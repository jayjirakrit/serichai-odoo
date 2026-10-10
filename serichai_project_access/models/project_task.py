import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request

from ._utils import norm_label, search_bool


class ProjectTask(models.Model):
    _inherit = 'project.task'

    access_task_visible = fields.Boolean(
        compute='_compute_access_flags', search='_search_access_task_visible',
        help="Task is in a granted project and an allowed stage for the current user.")
    access_task_writable = fields.Boolean(
        compute='_compute_access_flags', search='_search_access_task_writable',
        help="Task is in a project the current user has Write access to.")
    access_task_detail = fields.Boolean(
        compute='_compute_access_flags', search='_search_access_task_detail',
        help="Task is visible and the current user may open its form.")

    # ------------------------------------------------------------
    # Access flags (used by the global rules, views and the guard)
    # ------------------------------------------------------------

    @api.depends_context('uid')
    @api.depends('project_id', 'stage_id')
    def _compute_access_flags(self):
        grants = self.env.user._get_project_access()
        for task in self:
            if grants is None or not task.project_id:
                # private tasks (no project): core's own-task rule decides, not the matrix
                task.access_task_visible = task.access_task_writable = True
                task.access_task_detail = True
                continue
            grant = grants.get(task.project_id.id)
            ok = bool(
                grant and (grant.stage_ids is None or task.stage_id.id in grant.stage_ids))
            task.access_task_visible = ok
            task.access_task_writable = bool(grant and grant.write)
            task.access_task_detail = ok and grant.detail

    @api.model
    def _access_domain(self, flag):
        """Domain of tasks the current user reaches; flag: visible | writable | detail."""
        grants = self.env.user._get_project_access()
        if grants is None:
            return Domain.TRUE
        by_stage = defaultdict(list)
        for pid, grant in grants.items():
            if (flag == 'writable' and not grant.write) or (flag == 'detail' and not grant.detail):
                continue
            # a Write grant is not limited by stage
            stages = None if (flag == 'writable' or grant.stage_ids is None) else grant.stage_ids
            by_stage[stages].append(pid)
        # tasks without a project stay with core's own private-task rule
        return Domain.OR([Domain('project_id', '=', False)] + [
            Domain('project_id', 'in', pids)
            & (Domain.TRUE if stages is None else Domain('stage_id', 'in', list(stages)))
            for stages, pids in by_stage.items()])

    def _search_access_task_visible(self, operator, value):
        return search_bool(operator, value, self._access_domain('visible'))

    def _search_access_task_writable(self, operator, value):
        return search_bool(operator, value, self._access_domain('writable'))

    def _search_access_task_detail(self, operator, value):
        return search_bool(operator, value, self._access_domain('detail'))

    # ------------------------------------------------------------
    # Open-detail guard (generalised spec 007)
    # ------------------------------------------------------------

    def _access_is_restricted_form_load(self):
        """True when a restricted user loads tasks through a direct ``project.task.web_read``
        RPC (a task form: deep link, pager, list click). web_read is also called internally by
        web_search_read, web_read_group and co-record reads, so the top-level RPC method is
        checked instead of guarding every web_read (spec 006 research Decision 3)."""
        if self.env.su or not request:
            return False
        if self.env.user._get_project_access() is None:
            return False
        params = request.params or {}
        return params.get('model') == self._name and params.get('method') == 'web_read'

    def web_read(self, specification):
        if self._access_is_restricted_form_load() and not all(self.mapped('access_task_detail')):
            raise AccessError(self.env._("You are not allowed to open this task."))
        return super().web_read(specification)

    # ------------------------------------------------------------
    # Hidden properties
    # ------------------------------------------------------------

    def read(self, fields=None, load='_classic_read'):
        result = super().read(fields=fields, load=load)
        if self.env.su or not result or 'task_properties' not in result[0]:
            return result
        grants = self.env.user._get_project_access()
        if grants is None:
            return result
        project_of = {t.id: t.project_id.id for t in self}
        for vals in result:
            grant = grants.get(project_of.get(vals['id']))
            if grant and grant.hidden and vals.get('task_properties'):
                vals['task_properties'] = [
                    p for p in vals['task_properties']
                    if norm_label(p.get('string')) not in grant.hidden]
        return result

    # ------------------------------------------------------------
    # Hidden properties: every other way to reach a hidden property (spec 009 bug A)
    # ------------------------------------------------------------

    @api.model
    def _access_hidden_property_names(self):
        """Internal names of the properties hidden for the current user in at least one of the
        projects they are granted (a name shared with a visible property elsewhere is blocked
        too: the safe side). Empty for unrestricted users and when nothing is hidden."""
        grants = self.env.user._get_project_access()
        hidden = {pid: g.hidden for pid, g in (grants or {}).items() if g.hidden}
        if not hidden:
            return frozenset()
        # sudo: definitions of granted projects are read to map hidden labels to internal names;
        # only names leave this method.
        projects = self.env['project.project'].sudo().browse(hidden)
        return frozenset(
            p['name'] for project in projects for p in project.task_properties_definition or []
            if p.get('name') and norm_label(p.get('string')) in hidden[project.id])

    @api.model
    def _access_check_property_refs(self, domain=None, groupby=(), order=None):
        """Refuse a domain, group-by or order that names a hidden property: filtering or
        grouping on it would reveal its values even though they are never returned."""
        if self.env.su or not self.env.user._get_project_access():
            return
        refs = set()
        if domain:
            refs.update(cond.field_expr for cond in Domain(domain).iter_conditions())
        refs.update(groupby or ())
        refs.update(re.findall(r'task_properties\.\w+', order or ''))
        names = {ref.split(':')[0].partition('.')[2] for ref in refs
                 if isinstance(ref, str) and ref.startswith('task_properties.')}
        if names and names & self._access_hidden_property_names():
            raise AccessError(self.env._("You are not allowed to use this property."))

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        self._access_check_property_refs(domain=domain, order=order)
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None,
                    order=None):
        self._access_check_property_refs(domain=domain, groupby=groupby, order=order)
        return super()._read_group(domain, groupby=groupby, aggregates=aggregates, having=having,
                                   offset=offset, limit=limit, order=order)

    @api.model
    def get_property_definition(self, full_name):
        result = super().get_property_definition(full_name)
        if result and not self.env.su and result.get('name') in self._access_hidden_property_names():
            return {}
        return result

    def export_data(self, fields_to_export):
        # the export format returns stored property values straight from the cache
        if not self.env.su and any(
                f.split('/')[0] == 'task_properties' for f in fields_to_export):
            grants = self.env.user._get_project_access()
            if grants is not None and any(
                    grants.get(t.project_id.id) and grants[t.project_id.id].hidden for t in self):
                raise AccessError(self.env._("You are not allowed to export task properties."))
        return super().export_data(fields_to_export)

    def _access_check_target_project(self, vals):
        """A restricted user may only put a task in a project they have Write access to."""
        project_id = vals.get('project_id')
        if self.env.su or not project_id:
            return
        grants = self.env.user._get_project_access()
        grant = None if grants is None else grants.get(project_id)
        if grants is not None and not (grant and grant.write):
            raise AccessError(self.env._("You are not allowed to put a task in this project."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._access_check_target_project(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._access_check_target_project(vals)
        grants = self.env.user._get_project_access() if not self.env.su else None
        if grants is None or not isinstance(vals.get('task_properties'), list):
            return super().write(vals)
        # Defensive (research D7): the client never received the hidden properties, so merge the
        # stored values back instead of letting a save erase them.
        for task in self:
            grant = grants.get(task.project_id.id)
            new_vals = vals
            if grant and grant.hidden:
                # sudo: read the stored values the current user is not shown.
                stored = task.sudo().read(['task_properties'])[0]['task_properties'] or []
                incoming = {p.get('name') for p in vals['task_properties']}
                kept = [p for p in stored
                        if norm_label(p.get('string')) in grant.hidden
                        and p.get('name') not in incoming]
                if kept:
                    new_vals = dict(vals, task_properties=vals['task_properties'] + kept)
            super(ProjectTask, task).write(new_vals)
        return True

    # ------------------------------------------------------------
    # Kanban columns
    # ------------------------------------------------------------

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        stages = super()._read_group_stage_ids(stages, domain)
        grants = self.env.user._get_project_access()
        if grants is None:
            return stages
        # projects asked for by the domain and/or the context; both given: their intersection
        asked = []
        domain_ids = {
            pid for cond in Domain(domain).iter_conditions()
            if cond.field_expr == 'project_id' and cond.operator in ('=', 'in')
            for pid in (cond.value if cond.operator == 'in' else [cond.value])
            if pid}
        if domain_ids:
            asked.append(domain_ids)
        if self.env.context.get('default_project_id'):
            asked.append({self.env.context['default_project_id']})
        project_ids = set.intersection(*asked) if asked else set(grants)

        def allowed(stage):
            for pid in project_ids:
                grant = grants.get(pid)
                if grant is None:
                    continue
                if grant.stage_ids is None:
                    if not stage.project_ids or pid in stage.project_ids.ids:
                        return True
                elif stage.id in grant.stage_ids:
                    return True
            return False

        return stages.filtered(allowed)
