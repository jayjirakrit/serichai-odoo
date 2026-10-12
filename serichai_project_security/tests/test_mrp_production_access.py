from odoo.exceptions import AccessError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestMrpProductionAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login='restricted_mo_user',
            groups='serichai_project_security.group_project_task_list_only',
        )
        cls.product = cls.env['product.product'].create({'name': 'MO Test Product'})
        cls.production = cls.env['mrp.production'].create({'product_id': cls.product.id})
        cls.project = cls.env['project.project'].create({'name': 'MO Test Project'})
        stage = cls.env['project.task.type'].create({'name': 'วางแผนการผลิต'})
        cls.task = cls.env['project.task'].create({
            'name': 'MO Task',
            'project_id': cls.project.id,
            'stage_id': stage.id,
        })

    def test_open_form_and_assign_task(self):
        production = self.production.with_user(self.user)
        production.web_read({
            'product_id': {'fields': {'display_name': {}}},
            'project_task_ids': {'fields': {'display_name': {}}},
            'move_raw_ids': {'fields': {}},
            'workorder_ids': {'fields': {}},
        })
        production.write({'project_task_ids': [(4, self.task.id)]})
        self.assertEqual(self.production.project_task_ids, self.task)

    def test_other_fields_and_create_blocked(self):
        production = self.production.with_user(self.user)
        with self.assertRaises(AccessError):
            production.write({'origin': 'x'})
        with self.assertRaises(AccessError):
            self.env['mrp.production'].with_user(self.user).create({'product_id': self.product.id})
        with self.assertRaises(AccessError):
            production.unlink()

    def test_task_dropdown_lists_visible_tasks(self):
        res = self.env['project.task'].with_user(self.user).web_name_search(
            'MO Task', {'display_name': {}}, limit=8,
        )
        self.assertTrue(res)
        self.env['mrp.production'].with_user(self.user).web_search_read(
            [('id', '=', self.production.id)], {'project_task_ids': {'fields': {'display_name': {}}}},
        )
