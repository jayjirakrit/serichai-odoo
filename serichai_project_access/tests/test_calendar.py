from odoo.tests import tagged

from .common import AccessCase


@tagged('post_install', '-at_install')
class TestCalendar(AccessCase):

    def _view_types(self, xmlid):
        action = self.env.ref(f'serichai_project_access.{xmlid}')
        return [vt for _vid, vt in action.with_user(self.user)._get_action_dict()['views']]

    def test_actions_offer_calendar(self):
        self.assertIn('calendar', self._view_types('project_task_action_access_all'))
        self.assertIn('calendar', self._view_types('project_task_action_access_project'))

    def test_calendar_view_for_restricted_users(self):
        view = self.env.ref('serichai_project_access.project_task_view_calendar_access')
        arch = self.env['project.task'].with_user(self.user).get_view(view.id, 'calendar')['arch']
        self.assertIn('serichai_access_task_calendar', arch)
        self.assertIn('access_task_detail', arch)
        self.assertNotIn('tag_ids', arch)

    def test_calendar_search_respects_rules(self):
        deadline = '2026-10-20 08:00:00'
        self.tasks.write({'date_deadline': deadline})
        found = self.as_user().search([('date_deadline', '=', deadline)])
        self.assertEqual(found, self.tasks - self.t_none)
