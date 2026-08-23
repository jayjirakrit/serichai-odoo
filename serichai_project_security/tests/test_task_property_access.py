import psycopg2

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestTaskPropertyAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project = cls.env['project.project'].create({
            'name': 'Test Project (property access)',
            'task_properties_definition': [
                {'name': 'client_budget', 'string': 'Client Budget', 'type': 'char'},
                {'name': 'priority_level', 'string': 'Priority Level', 'type': 'char'},
            ],
        })
        cls.task = cls.env['project.task'].create({
            'name': 'Task With Properties',
            'project_id': cls.project.id,
            'task_properties': {
                'client_budget': '50000',
                'priority_level': 'High',
            },
        })

        cls.finance_group = cls.env['res.groups'].create({'name': 'Test Finance Group'})

        cls.rule = cls.env['project.task.property.access'].create({
            'property_string': 'Client Budget',
            'group_ids': [(6, 0, cls.finance_group.ids)],
        })

        cls.finance_user = new_test_user(
            cls.env, login='finance_test_user',
            groups='project.group_project_user',
        )
        cls.finance_user.write({'group_ids': [(4, cls.finance_group.id)]})

        cls.other_user = new_test_user(
            cls.env, login='other_test_user',
            groups='project.group_project_user',
        )

        cls.manager_user = new_test_user(
            cls.env, login='manager_test_user',
            groups='project.group_project_manager',
        )

    def _property_strings(self, user):
        values = self.task.with_user(user).read(['task_properties'])[0]['task_properties']
        return {p['string'] for p in values}

    def test_restricted_property_visible_to_permitted_user(self):
        self.assertIn('Client Budget', self._property_strings(self.finance_user))

    def test_restricted_property_hidden_from_non_permitted_user(self):
        self.assertNotIn('Client Budget', self._property_strings(self.other_user))

    def test_unrelated_properties_unaffected_by_rule(self):
        self.assertIn('Priority Level', self._property_strings(self.finance_user))
        self.assertIn('Priority Level', self._property_strings(self.other_user))

    def test_no_rules_configured_no_behavior_change(self):
        self.rule.unlink()
        self.assertEqual(
            self._property_strings(self.finance_user),
            self._property_strings(self.other_user),
        )
        self.assertIn('Client Budget', self._property_strings(self.other_user))

    def test_manager_can_create_edit_delete_rule(self):
        Access = self.env['project.task.property.access'].with_user(self.manager_user)
        rule = Access.create({
            'property_string': 'Manager Managed Property',
            'group_ids': [(6, 0, self.finance_group.ids)],
        })
        rule.write({'property_string': 'Manager Managed Property Renamed'})
        rule.unlink()

    def test_non_manager_cannot_manage_rules(self):
        Access = self.env['project.task.property.access'].with_user(self.other_user)
        with self.assertRaises(AccessError):
            Access.create({
                'property_string': 'Should Not Be Creatable',
                'group_ids': [(6, 0, self.finance_group.ids)],
            })

    def test_rule_requires_at_least_one_group(self):
        with self.assertRaises(ValidationError):
            self.env['project.task.property.access'].create({
                'property_string': 'No Groups Property',
                'group_ids': [(6, 0, [])],
            })

    def test_duplicate_property_string_rejected(self):
        with self.assertRaises(psycopg2.errors.UniqueViolation), self.env.cr.savepoint():
            self.env['project.task.property.access'].create({
                'property_string': 'Client Budget',
                'group_ids': [(6, 0, self.finance_group.ids)],
            })
