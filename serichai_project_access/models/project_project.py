from odoo import api, fields, models
from odoo.fields import Domain

from ._utils import norm_label, search_bool


class ProjectProject(models.Model):
    _inherit = 'project.project'

    access_can_read = fields.Boolean(
        compute='_compute_access_can_read', search='_search_access_can_read',
        help="True when the current user may see this project (always true for unrestricted "
             "users). Used by the global read rule of the project access module.")

    @api.depends_context('uid')
    def _compute_access_can_read(self):
        grants = self.env.user._get_project_access()
        for project in self:
            project.access_can_read = grants is None or project.id in grants

    def _search_access_can_read(self, operator, value):
        grants = self.env.user._get_project_access()
        granted = Domain.TRUE if grants is None else Domain('id', 'in', list(grants))
        return search_bool(operator, value, granted)

    def read(self, fields=None, load='_classic_read'):
        """Drop the definition of the properties hidden for the current user: the list, kanban and
        form get the project co-record (and the search panel lists property names) through this
        read, which bypasses the task.read filter (spec 009 bug A)."""
        result = super().read(fields=fields, load=load)
        if self.env.su or not result or 'task_properties_definition' not in result[0]:
            return result
        grants = self.env.user._get_project_access()
        if grants is None:
            return result
        for vals in result:
            grant = grants.get(vals['id'])
            if grant and grant.hidden and vals.get('task_properties_definition'):
                vals['task_properties_definition'] = [
                    p for p in vals['task_properties_definition']
                    if norm_label(p.get('string')) not in grant.hidden]
        return result

    def write(self, vals):
        res = super().write(vals)
        if 'active' in vals:
            self.env.registry.clear_cache()
        return res

    def action_view_tasks(self):
        if self.env.user._get_project_access() is None:
            return super().action_view_tasks()
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'serichai_project_access.project_task_action_access_project')
        action.update(display_name=self.name, domain=[('project_id', '=', self.id)],
                      context={'default_project_id': self.id, 'active_id': self.id,
                               'project_kanban': True, 'create': False})
        return action
