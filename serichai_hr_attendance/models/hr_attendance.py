import logging
from datetime import timedelta

from pytz import timezone as pytz_timezone
from pytz import utc

from odoo import api, fields, models
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    day_type = fields.Selection(
        [('weekday', 'Weekday'), ('sunday_holiday', 'Sunday/Holiday')],
        string='Day Type', compute='_compute_ot_hours', store=True,
    )
    normal_hours = fields.Float(
        string='Normal Hours', compute='_compute_ot_hours', store=True, aggregator='sum',
    )
    overtime_150_hours = fields.Float(
        string='OT 1.5x Hours', compute='_compute_ot_hours', store=True, aggregator='sum',
    )
    overtime_200_hours = fields.Float(
        string='OT 2x Hours', compute='_compute_ot_hours', store=True, aggregator='sum',
    )

    @api.model
    def _get_day_type(self, date, employee):
        """Return 'weekday' or 'sunday_holiday' for the given calendar `date`
        and `employee`. Sunday is always sunday_holiday; any other date that
        matches a company/calendar-wide (resource_id-less) resource.calendar.leaves
        record on the employee's calendar is treated the same way.
        """
        if date.weekday() == 6:  # Monday=0 ... Sunday=6
            return 'sunday_holiday'

        calendar = employee.resource_calendar_id
        if not calendar:
            return 'weekday'

        tz = pytz_timezone(employee.tz or calendar.tz or 'UTC')
        day_start_local = tz.localize(fields.Datetime.to_datetime(date))
        day_end_local = day_start_local + timedelta(days=1) - timedelta(microseconds=1)
        day_start_utc = day_start_local.astimezone(utc).replace(tzinfo=None)
        day_end_utc = day_end_local.astimezone(utc).replace(tzinfo=None)

        holiday = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', calendar.id),
            ('resource_id', '=', False),
            ('date_from', '<=', day_end_utc),
            ('date_to', '>=', day_start_utc),
        ], limit=1)
        return 'sunday_holiday' if holiday else 'weekday'

    @api.model
    def _interval_overlap(self, seg_start_hour, seg_end_hour, rule_from, rule_to):
        """Hours of overlap between [seg_start_hour, seg_end_hour) and
        [rule_from, rule_to), all expressed as local clock-time floats in [0, 24]."""
        start = max(seg_start_hour, rule_from)
        end = min(seg_end_hour, rule_to)
        return max(0.0, end - start)

    @api.model
    def _hours_outside(self, seg_start_hour, seg_end_hour, claimed_windows):
        """Hours of [seg_start_hour, seg_end_hour) not covered by any
        (from, to) window in `claimed_windows`."""
        if seg_end_hour <= seg_start_hour:
            return 0.0

        clipped = []
        for window_from, window_to in claimed_windows:
            start = max(seg_start_hour, window_from)
            end = min(seg_end_hour, window_to)
            if end > start:
                clipped.append((start, end))
        clipped.sort()

        merged = []
        for start, end in clipped:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        covered = sum(end - start for start, end in merged)
        return max(0.0, (seg_end_hour - seg_start_hour) - covered)

    @api.model
    def _round_down_half_hour(self, hours):
        return float_round(hours, precision_rounding=0.5, rounding_method='DOWN')

    @api.model
    def _split_into_day_segments(self, start_local, end_local):
        """Split a local-tz [start_local, end_local) datetime range into one
        segment per calendar date it crosses, splitting exactly at local midnight."""
        if end_local <= start_local:
            return [(start_local, start_local)]

        segments = []
        cursor = start_local
        while cursor < end_local:
            next_midnight = (cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            seg_end = min(end_local, next_midnight)
            segments.append((cursor, seg_end))
            cursor = seg_end
        return segments

    @api.depends('check_in', 'check_out', 'employee_id.wage_type')
    def _compute_ot_hours(self):
        for attendance in self:
            if not attendance.check_out:
                attendance.day_type = False
                attendance.normal_hours = 0.0
                attendance.overtime_150_hours = 0.0
                attendance.overtime_200_hours = 0.0
                continue

            employee = attendance.employee_id
            tz = pytz_timezone(
                employee.tz or (employee.resource_calendar_id.tz if employee.resource_calendar_id else None) or 'UTC'
            )
            check_in_local = utc.localize(attendance.check_in).astimezone(tz)
            check_out_local = utc.localize(attendance.check_out).astimezone(tz)
            segments = attendance._split_into_day_segments(check_in_local, check_out_local)

            attendance.day_type = attendance._get_day_type(segments[0][0].date(), employee)

            totals = {'normal': 0.0, 'ot150': 0.0, 'ot200': 0.0}
            wage_type = employee.wage_type

            if not wage_type:
                worked_hours = sum(
                    (seg_end - seg_start).total_seconds() for seg_start, seg_end in segments
                ) / 3600.0
                totals['normal'] = worked_hours
                _logger.warning(
                    "hr.attendance %s: employee %s has no wage_type set; recording all "
                    "worked hours as Normal pay.", attendance.id, employee.display_name,
                )
            else:
                for seg_start, seg_end in segments:
                    seg_day_type = attendance._get_day_type(seg_start.date(), employee)
                    seg_from_hour = seg_start.hour + seg_start.minute / 60.0 + seg_start.second / 3600.0
                    seg_to_hour = seg_from_hour + (seg_end - seg_start).total_seconds() / 3600.0

                    rules = self.env['hr.attendance.ot.rule'].search([
                        ('wage_type', '=', wage_type),
                        ('day_type', '=', seg_day_type),
                        ('company_id', '=', employee.company_id.id),
                    ], order='sequence, id')

                    # Every rule's own explicitly-bounded window claims its overlap,
                    # regardless of whether that same rule is also flagged catch_outside.
                    for rule in rules:
                        overlap = attendance._interval_overlap(
                            seg_from_hour, seg_to_hour, rule.time_from, rule.time_to
                        )
                        if overlap:
                            totals[rule.pay_type] += overlap

                    # catch_outside additionally sweeps time outside the OUTER boundary
                    # of the whole wage_type/day_type group (min(time_from)..max(time_to)
                    # across every rule in the group) — not the individual gaps between
                    # rules' windows, which stay intentionally unpaid (spec Edge Cases).
                    catch_rules = rules.filtered('catch_outside')
                    if catch_rules and rules:
                        boundary_from = min(rules.mapped('time_from'))
                        boundary_to = max(rules.mapped('time_to'))
                        remaining = attendance._hours_outside(
                            seg_from_hour, seg_to_hour, [(boundary_from, boundary_to)]
                        )
                        if remaining:
                            totals[catch_rules[0].pay_type] += remaining

            attendance.normal_hours = attendance._round_down_half_hour(totals['normal'])
            attendance.overtime_150_hours = attendance._round_down_half_hour(totals['ot150'])
            attendance.overtime_200_hours = attendance._round_down_half_hour(totals['ot200'])
