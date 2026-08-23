from odoo import models
from odoo.exceptions import AccessError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def get_view(self, view_id=None, view_type='form', **options):
        if view_type == 'form' and self.env.user.has_group(
            'serichai_project_security.group_project_task_list_only'
        ):
            raise AccessError(self.env._('You are not allowed to open task details.'))
        return super().get_view(view_id=view_id, view_type=view_type, **options)

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
