from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged, new_test_user

from .common import AccessCase


@tagged('post_install', '-at_install')
class TestAccessAdmin(AccessCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(cls.env, login='pa_manager', groups='project.group_project_manager')
        cls.project_user = new_test_user(cls.env, login='pa_puser', groups='project.group_project_user')

    def test_manager_crud(self):
        Profile = self.env['project.access.profile'].with_user(self.manager)
        group = self.env['res.groups'].create({'name': 'PA Admin Group'})
        profile = Profile.create({'name': 'Mfg', 'group_ids': [(6, 0, group.ids)]})
        line = self.env['project.access.line'].with_user(self.manager).create({
            'profile_id': profile.id, 'project_ids': [(6, 0, self.p_read.ids)]})
        line.access_level = 'write'
        self.assertEqual(line.task_access, 'detail')
        self.assertEqual(profile.project_ids, self.p_read)
        line.unlink()
        profile.write({'name': 'Mfg2'})
        profile.unlink()

    def test_non_manager_refused(self):
        for user in (self.project_user, self.user):
            with self.assertRaises(AccessError, msg=user.login):
                self.env['project.access.profile'].with_user(user).search([])
            with self.assertRaises(AccessError, msg=user.login):
                self.env['project.access.line'].with_user(user).create({
                    'profile_id': self.profile.id, 'project_ids': [(6, 0, self.p_none.ids)]})

    def test_duplicate_project_refused(self):
        with self.assertRaises(ValidationError):
            self.env['project.access.line'].create({
                'profile_id': self.profile.id, 'project_ids': [(6, 0, self.p_read.ids)]})
        with self.assertRaises(ValidationError):
            self.line_write.project_ids = self.p_read | self.p_write

    def test_write_forces_detail(self):
        self.assertEqual(self.line_write.task_access, 'detail')
        line = self.env['project.access.line'].create({
            'profile_id': self.profile.id, 'project_ids': [(6, 0, self.p_none.ids)],
            'access_level': 'write', 'task_access': 'list'})
        self.assertEqual(line.task_access, 'detail')

    def test_warnings(self):
        self.p_read.task_properties_definition = [
            {'name': 'prop_a', 'string': 'Color', 'type': 'char'}]
        self.line_read.hidden_property_names = 'color\n Missing '
        self.assertIn("'missing'", self.line_read.warning_message)
        self.assertNotIn("'color'", self.line_read.warning_message)
        self.p_read.privacy_visibility = 'followers'
        self.assertIn('Visibility may block members', self.line_read.warning_message)
        self.assertIn(self.p_read.name, self.line_read.warning_message)
        self.p_read.privacy_visibility = 'employees'
        self.line_read.hidden_property_names = 'Color'
        self.assertFalse(self.line_read.warning_message)

    def test_write_line_cleans_everything(self):
        """#4: write lines never keep stages/hidden/exhausted, on create or any write."""
        Line = self.env['project.access.line']
        line = Line.create({
            'profile_id': self.profile.id, 'project_ids': [(6, 0, self.p_none.ids)],
            'access_level': 'write', 'stage_ids': [(6, 0, self.s1.ids)],
            'hidden_property_names': 'x', 'stages_exhausted': True, 'task_access': 'list'})
        self.assertFalse(line.stage_ids or line.hidden_property_names or line.stages_exhausted)
        self.assertEqual(line.task_access, 'detail')
        # later write that does not mention access_level
        line.write({'stage_ids': [(6, 0, self.s1.ids)], 'hidden_property_names': 'y',
                    'task_access': 'list'})
        self.assertFalse(line.stage_ids or line.hidden_property_names)
        self.assertEqual(line.task_access, 'detail')
        # read -> read keeps the settings (negative)
        self.line_read.write({'stage_ids': [(6, 0, self.s1.ids)], 'hidden_property_names': 'z'})
        self.assertEqual(self.line_read.stage_ids, self.s1)
        # write -> read resets task_access to list unless explicit
        line.access_level = 'read'
        self.assertEqual(line.task_access, 'list')
        line.access_level = 'write'
        line.write({'access_level': 'read', 'task_access': 'detail'})
        self.assertEqual(line.task_access, 'detail')
        # mixed recordset in one write
        line.access_level = 'write'
        (line | self.line_read | self.line_write).write({'access_level': 'read'})
        self.assertEqual((line | self.line_read | self.line_write).mapped('task_access'),
                         ['list', 'list', 'list'])

    def test_exhausted_warning(self):
        """#3: the flag is visible through a warning and cleared by choosing stages."""
        stage = self.env['project.task.type'].create({'name': 'PA Gone2'})
        self.line_read.stage_ids = stage
        self.assertNotIn('stages were deleted', self.line_read.warning_message or '')
        stage.unlink()
        self.assertTrue(self.line_read.stages_exhausted)
        self.assertIn('All selected stages were deleted', self.line_read.warning_message)
        self.line_read.stage_ids = self.s1
        self.assertFalse(self.line_read.warning_message)
