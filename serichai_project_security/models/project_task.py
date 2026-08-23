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
