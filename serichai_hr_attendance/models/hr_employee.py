from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    wage_type = fields.Selection(
        [('daily', 'Daily Paid'), ('monthly', 'Monthly Paid')],
        string='Wage Type',
        help="Drives which Attendance Overtime Rules apply to this employee's attendance.",
    )
