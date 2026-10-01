from odoo import api, fields, models
from odoo.fields import Domain


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_expanded_access_task = fields.Boolean(
        compute='_compute_is_expanded_access_task',
        search='_search_is_expanded_access_task',
        help=(
            "True for tasks in the project an administrator has pinned as the "
            "expanded-access exception for the 'Task List Viewer (Production Planning Only)' "
            "role (see Settings > Project). Used to scope that role's write access and its "
            "dedicated menu - it does not affect any other role."
        ),
    )

    @api.model
    def _get_expanded_access_project_id(self):
        """Id of the project pinned as the write/form access exception for the restricted
        role, or False if none is configured. Referenced by record id (not name) so a rename
        doesn't drop the grant and a same-named project doesn't inherit it - see
        specs/006-product-dev-task-access/research.md Decision 1."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'serichai_project_security.expanded_access_project_id', 0
        )) or False

    def _compute_is_expanded_access_task(self):
        pinned_id = self._get_expanded_access_project_id()
        for task in self:
            task.is_expanded_access_task = bool(pinned_id) and task.project_id.id == pinned_id

    def _search_is_expanded_access_task(self, operator, value):
        # Odoo 19 normalizes boolean conditions (e.g. ('is_expanded_access_task', '=', True))
        # to 'in' / 'not in' a set of booleans before calling search methods.
        if operator not in ('in', 'not in'):
            return NotImplemented
        pinned_id = self._get_expanded_access_project_id()
        pinned = Domain('project_id', '=', pinned_id) if pinned_id else Domain.FALSE
        want_true, want_false = True in value, False in value
        if operator == 'not in':
            want_true, want_false = not want_true, not want_false
        if want_true and want_false:
            return Domain.TRUE
        if want_true:
            return pinned
        if want_false:
            return ~pinned
        return Domain.FALSE

    @api.model
    def action_open_expanded_access_tasks(self):
        """Entry point of the restricted role's "Product Development" menu (via a server
        action, since the pinned project id only exists at runtime). default_project_id lets
        the project Kanban show every stage of the pinned project as a column, empty ones
        included - see project.task._read_group_stage_ids and spec 006 FR-008."""
        action = self.env['ir.actions.act_window']._for_xml_id(
            'serichai_project_security.action_task_product_development_restricted'
        )
        pinned_id = self._get_expanded_access_project_id()
        if pinned_id:
            action['context'] = {'default_project_id': pinned_id}
            # sudo: only the name is exposed, and the role may lack read access to the project
            # record itself (e.g. a followers-only project).
            action['display_name'] = self.env['project.project'].sudo().browse(pinned_id).display_name
        return action

    def read(self, fields=None, load='_classic_read'):
        result = super().read(fields=fields, load=load)
        if self.env.su or not result or 'task_properties' not in result[0]:
            return result

        restricted_strings = self.env['project.task.property.access']._get_restricted_strings_for_user()
        if not restricted_strings:
            return result

        for vals in result:
            properties = vals.get('task_properties')
            if not properties:
                continue
            vals['task_properties'] = [
                prop for prop in properties
                if prop.get('string') not in restricted_strings
            ]
        return result
