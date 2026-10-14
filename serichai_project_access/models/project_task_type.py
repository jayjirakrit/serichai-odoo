from odoo import models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    def unlink(self):
        # sudo: managers of stages may not read access lines; only a flag is set.
        lines = self.env['project.access.line'].sudo().search([('stage_ids', 'in', self.ids)])
        exhausted = lines.filtered(lambda l: not (l.stage_ids - self))
        res = super().unlink()
        if exhausted:
            exhausted.write({'stages_exhausted': True})
        return res
