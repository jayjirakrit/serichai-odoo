from odoo.exceptions import AccessError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestConfidentialDescription(TransactionCase):
    """Spec 013: confidential_description is limited to project.group_project_user."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({'name': 'Confidential Test'})
        cls.task = cls.env['project.task'].create({
            'name': 'Task', 'project_id': cls.project.id,
            'confidential_description': '<p>secret</p>',
        })
        cls.user = new_test_user(cls.env, login='conf_user', groups='project.group_project_user')
        cls.manager = new_test_user(cls.env, login='conf_manager', groups='project.group_project_manager')
        # Plain internal user, as a department user granted access by a Project Access Group.
        cls.viewer = new_test_user(cls.env, login='conf_viewer', groups='base.group_user')

    def test_user_and_manager_can_read_write(self):
        for user in (self.user, self.manager):
            task = self.task.with_user(user)
            task.confidential_description = '<p>secret</p>'
            task.invalidate_recordset()
            self.assertIn('secret', task.confidential_description)
            task.confidential_description = '<p>updated</p>'
            task.invalidate_recordset()
            self.assertIn('updated', task.confidential_description)

    def test_internal_user_without_project_group_denied(self):
        task = self.task.with_user(self.viewer)
        with self.assertRaises(AccessError):
            task.confidential_description
        with self.assertRaises(AccessError):
            task.write({'confidential_description': 'x'})

    def test_form_arch_hides_field_for_viewer(self):
        view = self.env['project.task'].with_user(self.viewer).get_view(
            self.env.ref('project.view_task_form2').id, 'form')
        self.assertNotIn('confidential_description', view['arch'])
        view = self.env['project.task'].with_user(self.user).get_view(
            self.env.ref('project.view_task_form2').id, 'form')
        self.assertIn('confidential_description', view['arch'])

    def test_not_copied(self):
        self.assertFalse(self.task.copy().confidential_description)
