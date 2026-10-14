
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase

from .. import hooks

OLD = hooks.OLD


def snapshot(env, user, projects):
    """What `user` can do on the tasks of `projects`: visible ids, editable ids and the
    visible property labels per task. Used for the before/after comparison (SC-005)."""
    Task = env['project.task'].with_user(user)
    tasks = Task.search([('project_id', 'in', projects.ids)], order='id')
    editable, props = [], {}
    for task in tasks:
        try:
            with env.cr.savepoint():
                task.write({'priority': task.priority})
                editable.append(task.id)
        except AccessError:
            pass
        data = task.read(['task_properties'])[0]['task_properties'] or []
        props[task.id] = sorted(p['string'] for p in data)
    menus = env['ir.ui.menu'].with_user(user).with_context(lang='en_US').load_menus(False)
    root = env.ref('project.menu_main_pm')
    names = sorted(m['name'] for m in menus.values()
                   if m.get('app_id') == root.id and m['id'] != root.id and not m.get('children'))
    return {'visible': tasks.ids, 'editable': editable, 'properties': props, 'menus': names}


def old_module_installed(env):
    return bool(env['ir.module.module'].sudo().search_count(
        [('name', '=', OLD), ('state', '=', 'installed')]))


@tagged('post_install', '-at_install')
class TestMigration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.old_present = old_module_installed(cls.env)

    def setUp(self):
        super().setUp()
        if not self.old_present:
            self.skipTest("%s is not installed: migration cannot be exercised" % OLD)
        env = self.env
        # discard what the install-time hook may already have created in this DB
        self.env['project.access.profile'].with_context(active_test=False).search(
            [('name', '=', hooks.MIGRATED_NAME)]).unlink()
        self.old_group = env.ref(f'{OLD}.group_project_task_list_only')
        Stage = env['project.task.type']
        self.stages = Stage.create([{'name': n} for n in hooks.STAGES if not Stage.search([('name', '=', n)])])
        self.other_stage = Stage.create({'name': 'MIG Other stage'})
        definition = [{'name': 'mig_cost', 'string': 'MIG Cost', 'type': 'char'},
                      {'name': 'mig_note', 'string': 'MIG Note', 'type': 'char'}]
        self.pinned, self.normal = env['project.project'].create([
            {'name': 'MIG Pinned', 'privacy_visibility': 'employees',
             'task_properties_definition': definition},
            {'name': 'MIG Normal', 'privacy_visibility': 'employees',
             'task_properties_definition': definition}])
        prod = Stage.search([('name', '=', hooks.STAGES[0])], limit=1)
        values = {'mig_cost': '10', 'mig_note': 'n'}
        Task = env['project.task']
        self.tasks = Task.create([
            {'name': 'MIG N prod', 'project_id': self.normal.id, 'stage_id': prod.id,
             'task_properties': values},
            {'name': 'MIG N other', 'project_id': self.normal.id, 'stage_id': self.other_stage.id,
             'task_properties': values},
            {'name': 'MIG P prod', 'project_id': self.pinned.id, 'stage_id': prod.id,
             'task_properties': values},
            {'name': 'MIG P other', 'project_id': self.pinned.id, 'stage_id': self.other_stage.id,
             'task_properties': values}])
        env['ir.config_parameter'].sudo().set_param(
            f'{OLD}.expanded_access_project_id', str(self.pinned.id))
        self.finance = env['res.groups'].create({'name': 'MIG Finance'})
        # "MIG Cost" is reserved to finance (hidden from the old role), "MIG Note" to the old role
        Rule = env['project.task.property.access']
        Rule.create([{'property_string': 'MIG Cost', 'group_ids': [(6, 0, self.finance.ids)]},
                     {'property_string': 'MIG Note', 'group_ids': [(6, 0, self.old_group.ids)]}])
        self.user = new_test_user(env, login='mig_user', groups=f'{OLD}.group_project_task_list_only')
        self.user_fin = new_test_user(env, login='mig_user_fin', groups=f'{OLD}.group_project_task_list_only')
        self.user_fin.group_ids = [(4, self.finance.id)]
        self.outsider = new_test_user(env, login='mig_outsider', groups='base.group_user')
        self.projects = self.pinned | self.normal

    def _profile(self):
        return self.env['project.access.profile'].with_context(active_test=False).search(
            [('name', '=', hooks.MIGRATED_NAME)])

    def test_migration_content(self):
        hooks.post_init_hook(self.env)
        profile = self._profile()
        self.assertEqual(len(profile), 1)
        read_line = profile.line_ids.filtered(lambda l: l.access_level == 'read')
        write_line = profile.line_ids.filtered(lambda l: l.access_level == 'write')
        self.assertEqual(write_line.project_ids, self.pinned)
        self.assertIn(self.normal, read_line.project_ids)
        self.assertNotIn(self.pinned, read_line.project_ids)
        self.assertEqual(read_line.task_access, 'list')
        self.assertEqual(set(read_line.stage_ids.mapped('name')), set(hooks.STAGES))
        self.assertIn('MIG Cost', read_line.hidden_property_names.splitlines())
        self.assertNotIn('MIG Note', read_line.hidden_property_names.splitlines())
        new_group = self.env.ref('serichai_project_access.' + hooks.GROUP_XMLID)
        self.assertEqual(profile.group_ids, new_group)
        # users moved; the outsider is untouched
        self.assertIn(new_group, self.user.group_ids)
        self.assertIn(new_group, self.user_fin.group_ids)
        self.assertNotIn(new_group, self.outsider.group_ids)
        self.assertIsNotNone(self.user._get_project_access())
        self.assertIsNone(self.outsider._get_project_access())
        # a hidden property for one old user, the finance user's extra group is not copied (R3)
        grants = self.user._get_project_access()
        self.assertTrue(grants[self.pinned.id].write)
        self.assertFalse(grants[self.normal.id].write)

    def test_idempotent(self):
        hooks.post_init_hook(self.env)
        lines = self._profile().line_ids
        hooks.post_init_hook(self.env)
        self.assertEqual(len(self._profile()), 1)
        self.assertEqual(self._profile().line_ids, lines)

    def test_core_menus_restored(self):
        hooks.post_init_hook(self.env)
        ref = self.env.ref
        for xmlid, expected in {
            'project.menu_main_pm': {
                'project.group_project_manager', 'project.group_project_user',
                'serichai_project_access.serichai_project_access_group_restricted'},
            'project.menu_projects_group_stage': {'project.group_project_stages'},
            'project.menu_projects': set(),
            'project.menu_project_report': set(),
            'project.menu_project_management': set(),
            'project.menu_project_management_all_tasks': set(),
        }.items():
            self.assertEqual(ref(xmlid).group_ids, self.env['res.groups'].concat(*[ref(x) for x in expected]),
                             xmlid)

    def test_before_after(self):
        """SC-005: with the old rules alone (before the hook) and with the migrated profile
        (the old rules still AND-ed in), each user can do the same things."""
        before = {u.login: snapshot(self.env, u, self.projects) for u in (self.user, self.user_fin)}
        # sanity: the old role sees production stages only, and edits only the pinned project
        self.assertNotIn(self.tasks[1].id, before['mig_user']['visible'])
        # pinned project: every stage is editable, nothing else
        self.assertEqual(before['mig_user']['editable'], [self.tasks[2].id, self.tasks[3].id])
        hooks.post_init_hook(self.env)
        after = {u.login: snapshot(self.env, u, self.projects) for u in (self.user, self.user_fin)}
        for login in before:
            for key in ('visible', 'editable'):
                self.assertEqual(before[login][key], after[login][key], (login, key))

    def test_fresh_install_does_nothing(self):
        # without the old group record the hook must not create anything
        data = self.env['ir.model.data'].sudo().search(
            [('module', '=', OLD), ('name', '=', 'group_project_task_list_only')])
        data.name = 'renamed_for_test'
        self.env.flush_all()
        self.env.registry.clear_cache()
        hooks.post_init_hook(self.env)
        self.assertFalse(self._profile())
