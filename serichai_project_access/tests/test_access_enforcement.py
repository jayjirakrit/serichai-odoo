from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools import OrderedSet
from odoo.tests import tagged

from .common import AccessCase


@tagged('post_install', '-at_install')
class TestAccessEnforcement(AccessCase):

    def _visible(self, user=None):
        return self.as_user(user).search([('id', 'in', self.tasks.ids)])

    def test_ungranted_invisible(self):
        self.assertEqual(self._visible(), self.t_read1 | self.t_read2 | self.t_write)
        self.assertEqual(
            self.as_user().search_count([('id', '=', self.t_none.id)]), 0)
        groups = self.as_user()._read_group(
            [('id', 'in', self.tasks.ids)], ['project_id'], ['__count'])
        self.assertNotIn(self.p_none, [g[0] for g in groups])
        with self.assertRaises(AccessError):
            self.t_none.with_user(self.user).read(['name'])
        projects = self.env['project.project'].with_user(self.user).search(
            [('id', 'in', (self.p_read | self.p_write | self.p_none).ids)])
        self.assertEqual(projects, self.p_read | self.p_write)

    def test_unrestricted_sees_all(self):
        admin_visible = self.tasks.with_user(self.env.ref('base.user_admin')).filtered_domain([])
        self.assertEqual(admin_visible, self.tasks)
        pm = self.env['res.users'].create({
            'name': 'PA PM', 'login': 'pa_pm',
            'group_ids': [(6, 0, [self.env.ref('project.group_project_user').id,
                                  self.group.id])]})
        self.assertEqual(self._visible(pm), self.tasks)

    def test_stage_filter(self):
        self.line_read.stage_ids = self.s1
        self.assertEqual(self._visible(), self.t_read1 | self.t_write)
        self.line_read.stage_ids = self.s1 | self.s2
        self.assertEqual(self._visible(), self.t_read1 | self.t_read2 | self.t_write)
        self.line_read.stage_ids = False
        self.assertEqual(self._visible(), self.t_read1 | self.t_read2 | self.t_write)

    def test_stages_exhausted(self):
        stage = self.env['project.task.type'].create({'name': 'PA Gone'})
        self.line_read.stage_ids = stage
        self.assertEqual(self._visible(), self.t_write)  # only the stage Gone is allowed
        stage.unlink()
        self.assertTrue(self.line_read.stages_exhausted)
        self.assertFalse(self.line_read.stage_ids)
        self.assertEqual(self._visible(), self.t_write)  # grants no stage, not all
        self.line_read.stage_ids = self.s1
        self.assertFalse(self.line_read.stages_exhausted)
        self.assertEqual(self._visible(), self.t_read1 | self.t_write)

    def test_kanban_columns(self):
        self.line_read.stage_ids = self.s1
        Task = self.as_user().with_context(default_project_id=self.p_read.id)
        stages = Task._read_group_stage_ids(self.s1 | self.s2 | self.s3, [])
        self.assertEqual(stages, self.s1)
        stages = Task.with_context(default_project_id=self.p_none.id)._read_group_stage_ids(
            self.s1 | self.s2, [])
        self.assertFalse(stages)

    def test_read_refuses_write_create_unlink(self):
        Task = self.as_user()
        with self.assertRaises(AccessError):
            self.t_read1.with_user(self.user).write({'name': 'x'})
        with self.assertRaises(AccessError):
            Task.create({'name': 'new', 'project_id': self.p_read.id})
        with self.assertRaises(AccessError):
            Task.create({'name': 'new', 'project_id': self.p_none.id})
        with self.assertRaises(AccessError):
            self.t_read1.with_user(self.user).unlink()
        with self.assertRaises(AccessError):
            self.p_read.with_user(self.user).write({'name': 'x'})

    def test_write_allows_write_create_not_unlink(self):
        Task = self.as_user()
        self.t_write.with_user(self.user).write({'name': 'edited'})
        self.assertEqual(self.t_write.name, 'edited')
        new = Task.create({'name': 'new', 'project_id': self.p_write.id})
        self.assertTrue(new.exists())
        with self.assertRaises(AccessError):
            new.unlink()
        with self.assertRaises(AccessError):
            self.p_write.with_user(self.user).unlink()
        with self.assertRaises(AccessError):
            self.p_write.with_user(self.user).write({'name': 'x'})

    def test_write_ignores_stage_and_properties_settings(self):
        # settings on a Write line are cleared/ignored by the resolver
        self.line_write.write({'stage_ids': [(6, 0, self.s1.ids)],
                               'hidden_property_names': 'Secret'})
        grant = self.user._get_project_access()[self.p_write.id]
        self.assertIsNone(grant.stage_ids)
        self.assertEqual(grant.hidden, frozenset())
        self.assertIn(self.t_write, self._visible())

    def test_changes_apply_without_reassignment(self):
        self.assertNotIn(self.t_none, self._visible())
        self.env['project.access.line'].create({
            'profile_id': self.profile.id, 'project_ids': [(6, 0, self.p_none.ids)]})
        self.assertIn(self.t_none, self._visible())
        self.profile.line_ids.filtered(lambda l: self.p_none in l.project_ids).unlink()
        self.assertNotIn(self.t_none, self._visible())

    def test_merge_two_departments(self):
        group2 = self.env['res.groups'].create({'name': 'PA Dept Group 2'})
        profile2 = self.env['project.access.profile'].create({
            'name': 'PA Dept 2', 'group_ids': [(6, 0, group2.ids)]})
        self.line_read.stage_ids = self.s1
        line2 = self.env['project.access.line'].create({
            'profile_id': profile2.id, 'project_ids': [(6, 0, self.p_read.ids)],
            'access_level': 'read', 'task_access': 'detail', 'stage_ids': [(6, 0, self.s2.ids)]})
        self.assertEqual(self._visible(), self.t_read1 | self.t_write)
        self.user.group_ids = [(4, group2.id)]
        self.assertEqual(self._visible(), self.t_read1 | self.t_read2 | self.t_write)
        self.assertTrue(self.t_read1.with_user(self.user).access_task_detail)
        self.user.group_ids = [(3, group2.id)]
        self.assertEqual(self._visible(), self.t_read1 | self.t_write)
        # upgrade the second department to Write on the Read project: becomes writable
        self.user.group_ids = [(4, group2.id)]
        line2.access_level = 'write'
        self.t_read1.with_user(self.user).write({'name': 'merged'})
        self.assertEqual(self.t_read1.name, 'merged')

    # ---- review fixes ----

    def test_private_tasks_own_only(self):
        """#2: a restricted user keeps CRUD on own private task, never sees others'."""
        Task = self.as_user()
        mine = Task.create({'name': 'mine', 'user_ids': [(6, 0, self.user.ids)]})
        self.assertFalse(mine.project_id)
        other = self.env['project.task'].create({'name': 'theirs'})  # no assignee
        self.assertIn(mine, Task.search([('id', 'in', (mine | other).ids)]))
        self.assertNotIn(other, Task.search([('id', 'in', (mine | other).ids)]))
        mine.name = 'mine2'
        self.assertEqual(mine.name, 'mine2')
        with self.assertRaises(AccessError):
            other.with_user(self.user).write({'name': 'x'})
        with self.assertRaises(AccessError):
            other.with_user(self.user).unlink()
        mine.unlink()
        self.assertFalse(mine.exists())
        # project tasks stay protected: read project still not deletable
        with self.assertRaises(AccessError):
            self.t_read1.with_user(self.user).unlink()

    def test_target_project_validated(self):
        """#7: write/create may only target a Write project."""
        self.t_write.with_user(self.user).write({'project_id': self.p_write.id})
        for target in (self.p_read, self.p_none):
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                self.t_write.with_user(self.user).write({'project_id': target.id})
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                self.as_user().create({'name': 'n', 'project_id': target.id})
        # unrestricted users are unaffected
        self.t_write.write({'project_id': self.p_none.id})
        self.assertEqual(self.t_write.project_id, self.p_none)

    def test_kanban_columns_without_context(self):
        """#5: columns limited to granted projects' stages, even without default_project_id."""
        self.line_read.stage_ids = self.s1
        Task = self.as_user()
        s_none = self.env['project.task.type'].create(
            {'name': 'PA S4', 'project_ids': [(6, 0, self.p_none.ids)]})
        s_read = self.env['project.task.type'].create(
            {'name': 'PA S5', 'project_ids': [(6, 0, self.p_read.ids)]})
        # s1 allowed on Read, s3 belongs to the Write project; s2 and s5 belong to the Read
        # project but are not allowed stages there, s4 to an ungranted project
        stages = self.s1 | self.s2 | self.s3 | s_none | s_read
        self.assertEqual(Task._read_group_stage_ids(stages, []), self.s1 | self.s3)
        # a domain naming an ungranted project gives nothing; context + domain intersect
        none_dom = [('project_id', '=', self.p_none.id)]
        self.assertFalse(Task._read_group_stage_ids(self.s1 | self.s2, none_dom))
        read_dom = [('project_id', '=', self.p_read.id)]
        self.assertEqual(Task._read_group_stage_ids(self.s1 | self.s2, read_dom), self.s1)
        crossed = Task.with_context(default_project_id=self.p_none.id)
        self.assertFalse(crossed._read_group_stage_ids(self.s1 | self.s2, read_dom))
        # 'in' domains (stored as an OrderedSet by Domain), as sent by the Project kanban
        in_dom = Domain('project_id', 'in', OrderedSet([self.p_read.id]))
        self.assertEqual(Task._read_group_stage_ids(self.s1 | self.s2, in_dom), self.s1)
        none_in = Domain('project_id', 'in', [self.p_none.id, self.p_read.id]) & Domain(
            'stage_id', '!=', False)
        self.assertEqual(Task._read_group_stage_ids(self.s1 | self.s2, none_in), self.s1)
        # the Project kanban path: web_read_group grouped by stage on an 'in' project domain
        result = Task.web_read_group(
            [('project_id', 'in', [self.p_read.id])], ['stage_id'], ['__count'])
        self.assertTrue(result['groups'])
        # unrestricted user: untouched
        self.assertEqual(
            self.env['project.task']._read_group_stage_ids(self.s1 | self.s2, []), self.s1 | self.s2)
