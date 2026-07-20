from odoo import models, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    project_task_ids = fields.Many2many('project.task', 'project_task_mrp_production_rel', 'mrp_production_id', 'project_task_id', string='Project Tasks', help='Project tasks related to this manufacturing order.')
