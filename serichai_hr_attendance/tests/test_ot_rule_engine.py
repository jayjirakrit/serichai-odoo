from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

# Reference week: 2026-09-05 is a Saturday, 2026-09-06 a Sunday, 2026-09-07 a Monday.
# 2026-09-02 is a Wednesday, used as a "public holiday on a weekday" date.
MON = datetime(2026, 9, 7)
SAT = datetime(2026, 9, 5)
SUN = datetime(2026, 9, 6)
WED_HOLIDAY = datetime(2026, 9, 2)


def at(day, hour, minute=0):
    return day.replace(hour=hour, minute=minute)


@tagged('post_install', '-at_install')
class TestOtRuleEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'UTC'

        cls.calendar = cls.env.company.resource_calendar_id.copy({'tz': 'UTC'})

        cls.daily_employee = cls.env['hr.employee'].create({
            'name': 'Daily Test Employee',
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar.id,
            'wage_type': 'daily',
        })
        cls.monthly_employee = cls.env['hr.employee'].create({
            'name': 'Monthly Test Employee',
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar.id,
            'wage_type': 'monthly',
        })
        cls.no_wage_type_employee = cls.env['hr.employee'].create({
            'name': 'No Wage Type Employee',
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar.id,
        })

        # A public holiday on a Wednesday (not a Sunday), scoped to our test calendar.
        cls.env['resource.calendar.leaves'].create({
            'name': 'Test Public Holiday',
            'calendar_id': cls.calendar.id,
            'date_from': at(WED_HOLIDAY, 0, 0),
            'date_to': at(WED_HOLIDAY, 23, 59),
        })

    def _attendance(self, employee, check_in, check_out=None):
        vals = {'employee_id': employee.id, 'check_in': check_in}
        if check_out:
            vals['check_out'] = check_out
        return self.env['hr.attendance'].create(vals)

    def _assertHours(self, attendance, normal, ot150, ot200, day_type=None):
        self.assertAlmostEqual(attendance.normal_hours, normal, places=4)
        self.assertAlmostEqual(attendance.overtime_150_hours, ot150, places=4)
        self.assertAlmostEqual(attendance.overtime_200_hours, ot200, places=4)
        if day_type:
            self.assertEqual(attendance.day_type, day_type)

    # -- _get_day_type -----------------------------------------------------

    def test_get_day_type_weekday(self):
        self.assertEqual(
            self.env['hr.attendance']._get_day_type(MON.date(), self.daily_employee), 'weekday'
        )

    def test_get_day_type_sunday(self):
        self.assertEqual(
            self.env['hr.attendance']._get_day_type(SUN.date(), self.daily_employee), 'sunday_holiday'
        )

    def test_get_day_type_public_holiday(self):
        self.assertEqual(
            self.env['hr.attendance']._get_day_type(WED_HOLIDAY.date(), self.daily_employee),
            'sunday_holiday',
        )

    # -- _interval_overlap / _hours_outside ---------------------------------

    def test_interval_overlap_basic(self):
        attendance_model = self.env['hr.attendance']
        self.assertAlmostEqual(attendance_model._interval_overlap(8.0, 20.0, 8.0, 17.0), 9.0)
        self.assertAlmostEqual(attendance_model._interval_overlap(8.0, 20.0, 18.0, 22.0), 2.0)
        self.assertAlmostEqual(attendance_model._interval_overlap(8.0, 17.0, 18.0, 22.0), 0.0)

    def test_hours_outside_basic(self):
        attendance_model = self.env['hr.attendance']
        # Whole segment inside the boundary -> nothing outside.
        self.assertAlmostEqual(attendance_model._hours_outside(8.0, 17.0, [(8.0, 22.0)]), 0.0)
        # Segment straddling the boundary on both sides.
        self.assertAlmostEqual(attendance_model._hours_outside(6.0, 23.0, [(8.0, 22.0)]), 3.0)
        # No claimed windows -> everything is outside.
        self.assertAlmostEqual(attendance_model._hours_outside(8.0, 12.0, []), 4.0)

    # -- _compute_ot_hours: scenario 1 - plain weekday shift, Daily Paid ----

    def test_weekday_normal_only_daily(self):
        att = self._attendance(self.daily_employee, at(MON, 8), at(MON, 17))
        self._assertHours(att, 9.0, 0.0, 0.0, day_type='weekday')

    # -- scenario 2 - weekday shift into OT150, Daily Paid ------------------

    def test_weekday_into_ot150_daily(self):
        att = self._attendance(self.daily_employee, at(MON, 8), at(MON, 20))
        self._assertHours(att, 9.0, 2.0, 0.0, day_type='weekday')

    # -- scenario 3 - weekday shift with catch-outside time, Daily Paid -----

    def test_weekday_catch_outside_daily(self):
        att = self._attendance(self.daily_employee, at(MON, 6), at(MON, 23))
        self._assertHours(att, 9.0, 7.0, 0.0, day_type='weekday')

    # -- scenario 4 - Sunday shift within Daily-paid normal window ----------

    def test_sunday_normal_daily(self):
        att = self._attendance(self.daily_employee, at(SUN, 8), at(SUN, 12))
        self._assertHours(att, 4.0, 0.0, 0.0, day_type='sunday_holiday')

    # -- scenario 5 - Sunday shift crossing the Daily-paid unpaid gap -------

    def test_sunday_unpaid_gap_daily(self):
        att = self._attendance(self.daily_employee, at(SUN, 8), at(SUN, 13))
        self._assertHours(att, 4.0, 0.0, 0.5, day_type='sunday_holiday')

    # -- scenario 6 - Sunday shift into OT200, Daily Paid --------------------

    def test_sunday_ot200_daily(self):
        att = self._attendance(self.daily_employee, at(SUN, 12, 30), at(SUN, 16, 30))
        self._assertHours(att, 0.0, 0.0, 4.0, day_type='sunday_holiday')

    # -- scenario 7 - Sunday shift for Monthly-paid crossing into OT200 -----

    def test_sunday_ot200_monthly(self):
        att = self._attendance(self.monthly_employee, at(SUN, 8), at(SUN, 18))
        self._assertHours(att, 8.5, 0.0, 1.5, day_type='sunday_holiday')

    # -- scenario 8 - public holiday (non-Sunday) behaves like Sunday -------

    def test_public_holiday_like_sunday_daily(self):
        att = self._attendance(self.daily_employee, at(WED_HOLIDAY, 8), at(WED_HOLIDAY, 13))
        self._assertHours(att, 4.0, 0.0, 0.5, day_type='sunday_holiday')

    def test_public_holiday_like_sunday_monthly(self):
        att = self._attendance(self.monthly_employee, at(WED_HOLIDAY, 8), at(WED_HOLIDAY, 18))
        self._assertHours(att, 8.5, 0.0, 1.5, day_type='sunday_holiday')

    # -- scenario 9 - overnight shift split at midnight, Daily Paid ---------

    def test_overnight_shift_split_at_midnight_daily(self):
        att = self._attendance(self.daily_employee, at(SAT, 22), at(SUN, 7))
        # Sat 22:00-24:00 (weekday, catch-outside OT150) + Sun 00:00-07:00 (before the
        # Daily-paid Sunday Normal window, no catch-outside rule for that group -> unpaid).
        self._assertHours(att, 0.0, 2.0, 0.0, day_type='weekday')

    # -- scenario 10 - employee with no wage_type set ------------------------

    def test_no_wage_type_fallback(self):
        att = self._attendance(self.no_wage_type_employee, at(MON, 8), at(MON, 20))
        self._assertHours(att, 12.0, 0.0, 0.0)

    # -- scenario 11 - sub-30-minute remainder rounds down to zero ----------

    def test_sub_30_minute_rounds_down(self):
        att = self._attendance(self.daily_employee, at(MON, 18), at(MON, 18, 20))
        self._assertHours(att, 0.0, 0.0, 0.0)

    def test_rounding_50_minutes_rounds_to_half_hour(self):
        att = self._attendance(self.daily_employee, at(MON, 18), at(MON, 18, 50))
        self._assertHours(att, 0.0, 0.5, 0.0)

    # -- scenario 12 - open attendance (no check-out yet) --------------------

    def test_open_attendance_no_check_out(self):
        att = self._attendance(self.daily_employee, at(MON, 8))
        self.assertFalse(att.check_out)
        self._assertHours(att, 0.0, 0.0, 0.0)
        self.assertFalse(att.day_type)

    def test_open_attendance_then_check_out_recomputes(self):
        att = self._attendance(self.daily_employee, at(MON, 8))
        self._assertHours(att, 0.0, 0.0, 0.0)
        att.check_out = at(MON, 17)
        self._assertHours(att, 9.0, 0.0, 0.0, day_type='weekday')

    # -- recompute triggers ---------------------------------------------------

    def test_recompute_on_wage_type_change(self):
        att = self._attendance(self.daily_employee, at(SUN, 8), at(SUN, 13))
        self._assertHours(att, 4.0, 0.0, 0.5)
        self.daily_employee.wage_type = 'monthly'
        self._assertHours(att, 5.0, 0.0, 0.0)
