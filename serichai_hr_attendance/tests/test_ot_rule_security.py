from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestOtRuleSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager_user = new_test_user(
            cls.env, login='ot_rule_manager', groups='hr_attendance.group_hr_attendance_manager'
        )
        cls.officer_user = new_test_user(
            cls.env, login='ot_rule_officer', groups='hr_attendance.group_hr_attendance_officer'
        )
        cls.plain_user = new_test_user(cls.env, login='ot_rule_plain_employee', groups='base.group_user')

    def _rule_vals(self):
        return {
            'name': 'Test Rule',
            'wage_type': 'daily',
            'day_type': 'weekday',
            'time_from': 8.0,
            'time_to': 9.0,
            'pay_type': 'normal',
        }

    def test_manager_can_create_write_unlink(self):
        rule = self.env['hr.attendance.ot.rule'].with_user(self.manager_user).create(self._rule_vals())
        rule.with_user(self.manager_user).write({'time_to': 10.0})
        rule.with_user(self.manager_user).unlink()

    def test_officer_can_create_write_unlink(self):
        rule = self.env['hr.attendance.ot.rule'].with_user(self.officer_user).create(self._rule_vals())
        rule.with_user(self.officer_user).write({'time_to': 10.0})
        rule.with_user(self.officer_user).unlink()

    def test_plain_employee_cannot_create(self):
        with self.assertRaises(AccessError):
            self.env['hr.attendance.ot.rule'].with_user(self.plain_user).create(self._rule_vals())

    def test_plain_employee_cannot_write(self):
        rule = self.env['hr.attendance.ot.rule'].create(self._rule_vals())
        with self.assertRaises(AccessError):
            rule.with_user(self.plain_user).write({'time_to': 10.0})
