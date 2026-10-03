from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrAttendanceOtRule(models.Model):
    _name = 'hr.attendance.ot.rule'
    _description = 'Attendance Overtime Pay-Rate Rule'
    _order = 'wage_type, day_type, sequence, id'

    name = fields.Char(required=True)
    wage_type = fields.Selection(
        [('daily', 'Daily Paid'), ('monthly', 'Monthly Paid')],
        required=True,
    )
    day_type = fields.Selection(
        [('weekday', 'Weekday'), ('sunday_holiday', 'Sunday/Holiday')],
        required=True,
    )
    sequence = fields.Integer(default=10)
    time_from = fields.Float(string='From', required=True, help="Local clock time, 0.0-24.0.")
    time_to = fields.Float(string='To', required=True, help="Local clock time, 0.0-24.0.")
    pay_type = fields.Selection(
        [('normal', 'Normal'), ('ot150', 'OT 1.5x'), ('ot200', 'OT 2x')],
        required=True,
    )
    catch_outside = fields.Boolean(
        string='Catch Outside',
        default=False,
        help="If checked, this rule also absorbs worked time in its wage type/day type "
             "group that falls outside every explicitly bounded (non-catch-outside) rule's "
             "window. Among multiple catch-outside rules for the same group, the lowest "
             "sequence one applies.",
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.constrains('time_from', 'time_to')
    def _check_time_range(self):
        for rule in self:
            if not (0.0 <= rule.time_from <= 24.0) or not (0.0 <= rule.time_to <= 24.0):
                raise ValidationError(self.env._("Rule times must be between 0:00 and 24:00."))
            if rule.time_from >= rule.time_to:
                raise ValidationError(
                    self.env._("Rule '%(name)s': the From time must be earlier than the To time.", name=rule.name)
                )
