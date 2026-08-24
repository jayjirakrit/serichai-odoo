from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    mrp_production_ids = fields.Many2many('mrp.production', 'project_task_mrp_production_rel', 'project_task_id', 'mrp_production_id', string='Manufacturing Orders')
    mrp_production_count = fields.Integer(string='MO Count', compute='_compute_mrp_production_count',)

    @api.depends('mrp_production_ids')
    def _compute_mrp_production_count(self):
        for task in self:
            task.mrp_production_count = len(task.mrp_production_ids)
