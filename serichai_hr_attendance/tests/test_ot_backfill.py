from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..import post_init_hook

MON = datetime(2026, 9, 7)


@tagged('post_install', '-at_install')
class TestOtBackfill(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'UTC'
        calendar = cls.env.company.resource_calendar_id.copy({'tz': 'UTC'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Backfill Test Employee',
            'tz': 'UTC',
            'resource_calendar_id': calendar.id,
            'wage_type': 'daily',
        })

    def test_backfill_recomputes_blanked_records(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': MON.replace(hour=8),
            'check_out': MON.replace(hour=17),
        })
        # Already correctly computed at creation time (this is what "pre-existing,
        # never-computed" data looks like right after the columns are added, before
        # any write has happened) - simulate that by blanking the stored columns
        # directly in SQL, bypassing the ORM compute, then invalidating the cache.
        # Flush first so create()'s in-memory computed values land in the DB before
        # the raw UPDATE - otherwise a later auto-flush would overwrite our NULLs.
        attendance.flush_recordset()
        self.env.cr.execute(
            "UPDATE hr_attendance SET day_type = NULL, normal_hours = 0, "
            "overtime_150_hours = 0, overtime_200_hours = 0 WHERE id = %s",
            (attendance.id,),
        )
        attendance.invalidate_recordset(['day_type', 'normal_hours', 'overtime_150_hours', 'overtime_200_hours'])
        self.assertFalse(attendance.day_type)
        self.assertEqual(attendance.normal_hours, 0.0)

        post_init_hook(self.env)

        attendance.invalidate_recordset(['day_type', 'normal_hours', 'overtime_150_hours', 'overtime_200_hours'])
        self.assertEqual(attendance.day_type, 'weekday')
        self.assertAlmostEqual(attendance.normal_hours, 9.0)
        self.assertAlmostEqual(attendance.overtime_150_hours, 0.0)
        self.assertAlmostEqual(attendance.overtime_200_hours, 0.0)

    def test_backfill_batches_without_error(self):
        # Not a real 1000+ record test (too slow for the suite); just confirms the
        # batching loop runs cleanly end-to-end against the current dataset.
        post_init_hook(self.env)
