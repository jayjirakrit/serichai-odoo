from odoo import api, fields, models
from odoo.exceptions import AccessError

from .project_task import THRESHOLD_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # No config_parameter=: it would store 0 as "unset".
    serichai_high_value_threshold = fields.Float(string='High-Value Threshold', help="Tasks whose project value is above this amount are listed first. 0 makes every positive value high-value. After changing it, click 'Recalculate high-value flag'.")

    @api.model
    def get_values(self):
        res = super().get_values()
        res['serichai_high_value_threshold'] = self.env['project.task']._get_high_value_threshold()
        return res

    def set_values(self):
        super().set_values()
        # sudo: settings are admin-only (ACL); repr keeps 0 as "0.0", not unset.
        self.env['ir.config_parameter'].sudo().set_param(THRESHOLD_PARAM, repr(self.serichai_high_value_threshold))

    def action_serichai_recompute_high_value(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(self.env._("Only administrators can recalculate the flag."))
        self.env['project.task']._recompute_high_value()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': { 'type': 'success', 'message': self.env._("High-value flag recalculated.")}}
