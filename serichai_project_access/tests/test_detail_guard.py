from unittest.mock import patch, MagicMock

from odoo.exceptions import AccessError
from odoo.tests import tagged, new_test_user

from .common import AccessCase

REQUEST = 'odoo.addons.serichai_project_access.models.project_task.request'


def _request(method):
    req = MagicMock()
    req.params = {'model': 'project.task', 'method': method}
    req.__bool__ = lambda s: True
    return req


@tagged('post_install', '-at_install')
class TestDetailGuard(AccessCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.line_read.stage_ids = False
        cls.p_detail = cls.env['project.project'].create({'name': 'PA Detail'})
        cls.env['project.access.line'].create({
            'profile_id': cls.profile.id, 'project_ids': [(6, 0, cls.p_detail.ids)],
            'access_level': 'read', 'task_access': 'detail'})
        cls.t_detail = cls.env['project.task'].create(
            {'name': 'D1', 'project_id': cls.p_detail.id, 'stage_id': cls.s1.id})

    def test_list_only_refused(self):
        with patch(REQUEST, _request('web_read')):
            with self.assertRaises(AccessError):
                self.t_read1.with_user(self.user).web_read({'name': {}})

    def test_open_detail_allowed(self):
        with patch(REQUEST, _request('web_read')):
            res = self.t_detail.with_user(self.user).web_read({'name': {}})
            self.assertEqual(res[0]['name'], 'D1')

    def test_write_implies_detail(self):
        with patch(REQUEST, _request('web_read')):
            res = self.t_write.with_user(self.user).web_read({'name': {}})
            self.assertEqual(res[0]['name'], 'W1')

    def test_search_and_group_still_work(self):
        with patch(REQUEST, _request('web_search_read')):
            res = self.env['project.task'].with_user(self.user).web_search_read(
                [('id', 'in', self.tasks.ids)], {'name': {}})
            self.assertEqual(res['length'], 4 - 1)
        with patch(REQUEST, _request('web_read_group')):
            self.env['project.task'].with_user(self.user).web_read_group(
                [('id', 'in', self.tasks.ids)], ['project_id'], ['__count'])

    def test_project_user_exempt(self):
        pu = new_test_user(self.env, login='pa_guard_pu',
                           groups='project.group_project_user')
        pu.group_ids = [(4, self.group.id)]
        with patch(REQUEST, _request('web_read')):
            res = self.t_read1.with_user(pu).web_read({'name': {}})
            self.assertEqual(res[0]['name'], 'R1')

    def test_flags(self):
        self.assertFalse(self.t_read1.with_user(self.user).access_task_detail)
        self.assertTrue(self.t_write.with_user(self.user).access_task_detail)
        self.assertTrue(self.t_detail.with_user(self.user).access_task_detail)
