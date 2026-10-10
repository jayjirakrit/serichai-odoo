from odoo.tests import new_test_user, tagged

from .common import AccessCase


@tagged('post_install', '-at_install')
class TestAccessMenus(AccessCase):

    def _menu_ids(self, user):
        return self.env['ir.ui.menu'].with_user(user)._load_menus_blacklist()

    def _visible_project_menus(self, user):
        menus = self.env['ir.ui.menu'].with_user(user).with_context(lang='en_US')
        data = menus.load_menus(False)
        root = self.env.ref('project.menu_main_pm')
        return {m['xmlid'] for m in data.values()
                if m.get('xmlid') and m.get('app_id') == root.id and m['id'] != root.id}

    def test_restricted_sees_only_own_menus(self):
        self.assertEqual(self._visible_project_menus(self.user), {
            'serichai_project_access.menu_task_all_access',
            'serichai_project_access.menu_project_access'})

    def test_project_user_sees_standard_menus_only(self):
        pm = new_test_user(self.env, login='pa_menu_pu', groups='project.group_project_user')
        pm.group_ids = [(4, self.group.id)]  # also in the department: still unrestricted
        self.assertIsNone(pm._get_project_access())
        visible = self._visible_project_menus(pm)
        self.assertNotIn('serichai_project_access.menu_task_all_access', visible)
        self.assertNotIn('serichai_project_access.menu_project_access', visible)
        self.assertIn('project.menu_project_management_all_tasks', visible)

    def test_action_view_tasks(self):
        action = self.p_read.with_user(self.user).action_view_tasks()
        self.assertEqual(
            action['id'], self.env.ref('serichai_project_access.project_task_action_access_project').id)
        self.assertEqual(action['domain'], [('project_id', '=', self.p_read.id)])
        # unrestricted users keep the stock action
        stock = self.p_read.with_user(self.env.ref('base.user_admin')).action_view_tasks()
        self.assertNotEqual(stock['id'], action['id'])

    def test_project_list_only_granted(self):
        projects = self.env['project.project'].with_user(self.user).search(
            [('id', 'in', (self.p_read | self.p_write | self.p_none).ids)])
        self.assertEqual(projects, self.p_read | self.p_write)
        action = self.env.ref('serichai_project_access.project_project_action_access')
        self.assertEqual(action.res_model, 'project.project')
