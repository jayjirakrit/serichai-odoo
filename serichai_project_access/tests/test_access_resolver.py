from odoo.exceptions import ValidationError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase

from ..models.res_users import Grant

RESTRICTED = 'serichai_project_access.serichai_project_access_group_restricted'


@tagged('post_install', '-at_install')
class TestAccessResolver(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Project = cls.env['project.project']
        cls.p1, cls.p2 = Project.create([{'name': 'PA P1'}, {'name': 'PA P2'}])
        Stage = cls.env['project.task.type']
        cls.s1, cls.s2 = Stage.create([{'name': 'PA S1'}, {'name': 'PA S2'}])
        cls.group = cls.env['res.groups'].create({'name': 'PA Dept Group'})
        cls.group2 = cls.env['res.groups'].create({'name': 'PA Dept Group 2'})
        cls.restricted = cls.env.ref(RESTRICTED)
        cls.profile = cls.env['project.access.profile'].create({
            'name': 'Dept', 'group_ids': [(6, 0, cls.group.ids)]})
        cls.user = new_test_user(cls.env, login='pa_user', groups='base.group_user')
        cls.user.group_ids = [(4, cls.group.id)]

    def _line(self, profile=None, **vals):
        vals.setdefault('project_ids', [(6, 0, self.p1.ids)])
        return self.env['project.access.line'].create(
            dict(vals, profile_id=(profile or self.profile).id))

    def _access(self, user=None):
        return (user or self.user)._get_project_access()

    def test_restricted_group_sync(self):
        self.assertIn(self.restricted, self.group.implied_ids)
        self.assertIn(self.restricted.id, self.user._get_group_ids())
        self.profile.active = False
        self.assertNotIn(self.restricted, self.group.implied_ids)
        self.profile.active = True
        self.assertIn(self.restricted, self.group.implied_ids)
        other = self.env['project.access.profile'].create(
            {'name': 'Other', 'group_ids': [(6, 0, self.group2.ids)]})
        self.assertIn(self.restricted, self.group2.implied_ids)
        other.group_ids = self.group
        self.assertNotIn(self.restricted, self.group2.implied_ids)
        other.unlink()
        self.assertIn(self.restricted, self.group.implied_ids)
        self.profile.unlink()
        self.assertNotIn(self.restricted, self.group.implied_ids)

    def test_forbidden_groups(self):
        for ref in ('base.group_user', 'base.group_portal', 'base.group_public',
                    'base.group_system', 'project.group_project_user',
                    'project.group_project_manager'):
            with self.assertRaises(ValidationError, msg=ref), self.cr.savepoint():
                self.env['project.access.profile'].create(
                    {'name': 'Bad', 'group_ids': [(6, 0, self.env.ref(ref).ids)]})

    def test_single_grant(self):
        self._line(stage_ids=[(6, 0, self.s1.ids)], hidden_property_names=' Foo \n\nBar')
        self.assertEqual(self._access(), {
            self.p1.id: Grant(False, False, frozenset(self.s1.ids), frozenset({'foo', 'bar'}))})

    def test_unrestricted_returns_none(self):
        self._line()
        plain = new_test_user(self.env, login='pa_plain', groups='base.group_user')
        self.assertIsNone(self._access(plain))
        pm = new_test_user(self.env, login='pa_pm', groups='project.group_project_manager')
        pm.group_ids = [(4, self.group.id)]
        self.assertIsNone(self._access(pm))
        pu = new_test_user(self.env, login='pa_pu', groups='project.group_project_user')
        pu.group_ids = [(4, self.group.id)]
        self.assertIsNone(self._access(pu))

    def test_merge_write_over_read_and_detail(self):
        self.profile.group_ids = self.group | self.group2
        profile2 = self.env['project.access.profile'].create(
            {'name': 'D2', 'group_ids': [(6, 0, self.group2.ids)]})
        self.user.group_ids = [(4, self.group2.id)]
        self._line(stage_ids=[(6, 0, self.s1.ids)], hidden_property_names='a\nb')
        self._line(profile2, access_level='write')
        grant = self._access()[self.p1.id]
        self.assertTrue(grant.write)
        self.assertTrue(grant.detail)
        self.assertIsNone(grant.stage_ids)
        self.assertEqual(grant.hidden, frozenset())

    def test_merge_detail_stage_union_hidden_intersection(self):
        profile2 = self.env['project.access.profile'].create(
            {'name': 'D2', 'group_ids': [(6, 0, self.group2.ids)]})
        self.user.group_ids = [(4, self.group2.id)]
        self._line(stage_ids=[(6, 0, self.s1.ids)], hidden_property_names='a\nb')
        self._line(profile2, task_access='detail', stage_ids=[(6, 0, self.s2.ids)],
                   hidden_property_names='B\nc')
        grant = self._access()[self.p1.id]
        self.assertFalse(grant.write)
        self.assertTrue(grant.detail)
        self.assertEqual(grant.stage_ids, frozenset((self.s1 | self.s2).ids))
        self.assertEqual(grant.hidden, frozenset({'b'}))
        # a line without stages means all stages
        self._line(profile2, project_ids=[(6, 0, self.p2.ids)])
        self.assertIsNone(self._access()[self.p2.id].stage_ids)

    def test_write_forces_detail(self):
        line = self._line(access_level='write')
        self.assertEqual(line.task_access, 'detail')

    def test_duplicate_project_in_profile(self):
        self._line()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._line()

    def test_cache_invalidation(self):
        self.assertEqual(self._access(), {})
        line = self._line()
        self.assertEqual(set(self._access()), {self.p1.id})
        line.access_level = 'write'
        self.assertTrue(self._access()[self.p1.id].write)
        self.p1.active = False
        self.assertEqual(self._access(), {})
        self.p1.active = True
        self.user.group_ids = [(3, self.group.id)]
        self.assertIsNone(self._access())
        self.user.group_ids = [(4, self.group.id)]
        self.assertEqual(set(self._access()), {self.p1.id})
        self.profile.active = False
        self.assertIsNone(self._access())

    def test_stages_exhausted(self):
        line = self._line(stage_ids=[(6, 0, self.s1.ids)])
        self.s1.unlink()
        self.assertTrue(line.stages_exhausted)
        self.assertEqual(self._access()[self.p1.id].stage_ids, frozenset())
        line.stage_ids = self.s2
        self.assertFalse(line.stages_exhausted)
        self.assertEqual(self._access()[self.p1.id].stage_ids, frozenset(self.s2.ids))

    def test_forbidden_transitive(self):
        """#8: a group implying a forbidden group is rejected; implying base.group_user is not."""
        Profile = self.env['project.access.profile']
        sneaky = self.env['res.groups'].create({
            'name': 'PA Sneaky', 'implied_ids': [(4, self.env.ref('project.group_project_user').id)]})
        deep = self.env['res.groups'].create({'name': 'PA Deep', 'implied_ids': [(4, sneaky.id)]})
        for group in (sneaky, deep):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                Profile.create({'name': 'Bad', 'group_ids': [(6, 0, group.ids)]})
        ok = self.env['res.groups'].create({
            'name': 'PA Ok', 'implied_ids': [(4, self.env.ref('base.group_user').id)]})
        Profile.create({'name': 'Fine', 'group_ids': [(6, 0, ok.ids)]})

    def test_sync_touches_only_affected_groups(self):
        """#9: groups linked by other means or by unrelated profiles are left alone."""
        Profile = self.env['project.access.profile']
        manual = self.env['res.groups'].create(
            {'name': 'PA Manual', 'implied_ids': [(4, self.restricted.id)]})
        shared = self.group2
        other = Profile.create({'name': 'Other', 'group_ids': [(6, 0, (self.group | shared).ids)]})
        self.assertIn(self.restricted, shared.implied_ids)
        # deleting/archiving a profile keeps groups still wanted by another active profile
        self.profile.unlink()
        self.assertIn(self.restricted, self.group.implied_ids)  # still in `other`
        other.write({'group_ids': [(6, 0, shared.ids)]})
        self.assertNotIn(self.restricted, self.group.implied_ids)
        self.assertIn(self.restricted, shared.implied_ids)
        # unrelated group linked by hand survives every sync
        self.assertIn(self.restricted, manual.implied_ids)
        other.active = False
        self.assertNotIn(self.restricted, shared.implied_ids)
        self.assertIn(self.restricted, manual.implied_ids)
        other.unlink()
        self.assertIn(self.restricted, manual.implied_ids)
