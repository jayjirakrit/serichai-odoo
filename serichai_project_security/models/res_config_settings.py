from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    serichai_expanded_access_project_id = fields.Many2one(
        'project.project',
        string='Expanded-Access Project (Task List Viewer role)',
        config_parameter='serichai_project_security.expanded_access_project_id',
        help=(
            "Members of the 'Task List Viewer (Production Planning Only)' role can open the "
            "task form and edit existing tasks in this project only. Every other project keeps "
            "their normal read-only, list-only access."
        ),
    )
