from types import SimpleNamespace
from unittest.mock import patch

from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase

TARGET_STAGE_NAME = 'วางแผนการผลิต'
REQUEST_PATH = 'odoo.addons.serichai_project_security.models.project_task.request'


@tagged('post_install', '-at_install')
class TestTaskAccessRestriction(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.stage_target = cls.env['project.task.type'].create({
            'name': TARGET_STAGE_NAME,
        })
        cls.stage_decoy = cls.env['project.task.type'].create({
            'name': 'Decoy Stage',
        })

        cls.project = cls.env['project.project'].create({
            'name': 'Test Project (serichai_project_security)',
        })

        cls.task_target = cls.env['project.task'].create({
            'name': 'Target Task',
            'project_id': cls.project.id,
            'stage_id': cls.stage_target.id,
        })
        cls.task_decoy = cls.env['project.task'].create({
            'name': 'Decoy Task',
            'project_id': cls.project.id,
            'stage_id': cls.stage_decoy.id,
        })

        # Expanded-access project (spec 006): pinned via the same config parameter an
        # administrator would set through Settings > Project. cls.project is deliberately
        # NOT pinned, so it continues to exercise the "everywhere else" behavior.
        cls.project_pinned = cls.env['project.project'].create({
            'name': 'Product Development',
        })
        cls.task_pinned = cls.env['project.task'].create({
            'name': 'Pinned Project Task',
            'project_id': cls.project_pinned.id,
            'stage_id': cls.stage_target.id,
        })
        cls.env['ir.config_parameter'].sudo().set_param(
            'serichai_project_security.expanded_access_project_id',
            str(cls.project_pinned.id),
        )

        # group_project_task_list_only implies base.group_user (see
        # security/security_groups.xml), so assigning it alone is sufficient
        # for a valid internal-user login - no project permissions beyond
        # what this module explicitly grants.
        cls.restricted_user = new_test_user(
            cls.env,
            login='restricted_test_user',
            groups='serichai_project_security.group_project_task_list_only',
        )
        cls.control_user = new_test_user(
            cls.env,
            login='control_test_user',
            groups='project.group_project_user',
        )

    def test_restricted_user_stage_filter_outside_pinned_project(self):
        # FR-001: outside the pinned project, only Production Planning stage tasks are visible.
        tasks = self.env['project.task'].with_user(self.restricted_user).search([])
        self.assertIn(self.task_target, tasks)
        self.assertNotIn(self.task_decoy, tasks)

    def test_restricted_user_sees_pinned_project_tasks_in_any_stage(self):
        # FR-007: the stage filter does not apply to the pinned project.
        pinned_decoy_stage_task = self.env['project.task'].create({
            'name': 'Pinned Project Task Outside Planning Stages',
            'project_id': self.project_pinned.id,
            'stage_id': self.stage_decoy.id,
        })
        tasks = self.env['project.task'].with_user(self.restricted_user).search(
            [('is_expanded_access_task', '=', True)]
        )
        self.assertIn(self.task_pinned, tasks)
        self.assertIn(pinned_decoy_stage_task, tasks)

        # Moving the task out of the pinned project puts it back under the stage filter.
        pinned_decoy_stage_task.project_id = self.project
        tasks = self.env['project.task'].with_user(self.restricted_user).search([])
        self.assertNotIn(pinned_decoy_stage_task, tasks)

    def test_product_development_action_opens_kanban_on_pinned_project(self):
        # FR-008: the menu's server action injects the pinned project so the Kanban can show
        # its stages, Kanban first.
        menu = self.env.ref('serichai_project_security.menu_task_product_development_restricted')
        action = menu.action.with_user(self.restricted_user).run()
        self.assertEqual(action['res_model'], 'project.task')
        self.assertEqual(action['context'], {'default_project_id': self.project_pinned.id})
        self.assertEqual(action['display_name'], self.project_pinned.name)
        self.assertEqual([view_type for _view_id, view_type in action['views']], ['kanban', 'list', 'form'])

    def test_product_development_kanban_shows_every_stage_of_pinned_project(self):
        # FR-008: every stage of the pinned project is a column, empty ones included, read as
        # the restricted user with the same context the Kanban view sends.
        empty_stage = self.env['project.task.type'].create({'name': 'Empty Stage'})
        self.project_pinned.type_ids = self.stage_target | self.stage_decoy | empty_stage
        Task = self.env['project.task'].with_user(self.restricted_user).with_context(
            default_project_id=self.project_pinned.id,
            project_kanban=True,
            read_group_expand=True,
        )
        groups = Task.formatted_read_group(
            [('is_expanded_access_task', '=', True)], ['stage_id'], ['__count'],
        )
        self.assertEqual(
            {group['stage_id'][0] for group in groups},
            {self.stage_target.id, self.stage_decoy.id, empty_stage.id},
        )

    def test_product_development_kanban_stage_columns_not_editable(self):
        # US1 scenario 5: the role can't create/edit/delete stage columns or create tasks.
        view = self.env.ref('serichai_project_security.view_task_kanban_expanded_access')
        result = self.env['project.task'].with_user(self.restricted_user).get_view(
            view_id=view.id, view_type='kanban',
        )
        kanban = etree.fromstring(result['arch'])
        for attribute in ('create', 'delete', 'quick_create', 'group_create', 'group_edit', 'group_delete'):
            self.assertEqual(kanban.get(attribute), '0', attribute)

    def test_restricted_user_form_view_fetchable(self):
        # 2026-09-30 (spec 006): get_view no longer categorically blocks 'form' for this role -
        # it has no record context to know which project a form is being opened for (see
        # research.md Decision 3), so the real boundary moved to write access (see the
        # expanded-access tests below). Fetching the arch itself is harmless: this role's
        # unrestricted perm_read already exposes the same field data via the list.
        Task = self.env['project.task'].with_user(self.restricted_user)
        Task.get_view(view_type='form')  # must not raise

    def test_restricted_user_write_denied_outside_pinned_project(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self.assertRaises(AccessError):
            Task.browse(self.task_target.id).write({'name': 'Attempted Edit'})

    def test_restricted_user_write_allowed_in_pinned_project(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        Task.browse(self.task_pinned.id).write({'name': 'Edited By Restricted User'})
        self.assertEqual(self.task_pinned.name, 'Edited By Restricted User')

    def test_restricted_user_create_denied_everywhere(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self.assertRaises(AccessError):
            Task.create({'name': 'New Task', 'project_id': self.project_pinned.id})

    def test_restricted_user_unlink_denied_even_in_pinned_project(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self.assertRaises(AccessError):
            Task.browse(self.task_pinned.id).unlink()

    def test_expanded_access_follows_project_record_through_rename(self):
        # FR-004: renaming the pinned project must not drop the grant.
        self.project_pinned.name = 'Product Development (Renamed)'
        Task = self.env['project.task'].with_user(self.restricted_user)
        Task.browse(self.task_pinned.id).write({'name': 'Still Editable After Rename'})
        self.assertEqual(self.task_pinned.name, 'Still Editable After Rename')

    def test_expanded_access_does_not_follow_a_same_named_project(self):
        # FR-003/Edge Case: a later, unrelated project reusing the pinned project's original
        # name must NOT inherit the grant - only the pinned record id qualifies.
        decoy_project = self.env['project.project'].create({'name': 'Product Development'})
        decoy_task = self.env['project.task'].create({
            'name': 'Decoy Product Development Task',
            'project_id': decoy_project.id,
        })
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self.assertRaises(AccessError):
            Task.browse(decoy_task.id).write({'name': 'Attempted Edit'})

    def test_no_pinned_project_grants_no_write_access(self):
        # Edge Case: before any project is pinned (or after it's cleared), the expanded-access
        # rule must match no tasks, without error - not even the "pinned" project's own task.
        self.env['ir.config_parameter'].sudo().set_param(
            'serichai_project_security.expanded_access_project_id', '0',
        )
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self.assertRaises(AccessError):
            Task.browse(self.task_pinned.id).write({'name': 'Attempted Edit'})

    def _rpc_request(self, method):
        # Stand-in for the JSON-RPC request the web client sends (call_kw / json2 both expose
        # the top-level model and method in request.params).
        return patch(REQUEST_PATH, SimpleNamespace(params={'model': 'project.task', 'method': method}))

    def test_all_tasks_action_has_form_view(self):
        # 2026-10-03: "All Tasks" can now switch to the form (for pinned-project rows only).
        action = self.env.ref('serichai_project_security.action_task_all_restricted')
        self.assertEqual(action.view_mode, 'list,form')

    def test_restricted_list_uses_gating_controller(self):
        view = self.env.ref('serichai_project_security.view_task_list_restricted')
        result = self.env['project.task'].with_user(self.restricted_user).get_view(
            view_id=view.id, view_type='list',
        )
        arch = etree.fromstring(result['arch'])
        self.assertEqual(arch.get('js_class'), 'serichai_restricted_task_list')
        self.assertEqual(arch.get('create'), '0')
        self.assertEqual(arch.get('delete'), '0')
        node = arch.find(".//field[@name='is_expanded_access_task']")
        self.assertIsNotNone(node, 'the client needs is_expanded_access_task to gate row opening')
        self.assertEqual(node.get('column_invisible'), '1')

    def test_restricted_user_form_load_allowed_in_pinned_project(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self._rpc_request('web_read'):
            [vals] = Task.browse(self.task_pinned.id).web_read({'name': {}})
        self.assertEqual(vals['name'], self.task_pinned.name)

    def test_restricted_user_form_load_denied_outside_pinned_project(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self._rpc_request('web_read'), self.assertRaises(AccessError):
            Task.browse(self.task_target.id).web_read({'name': {}})

    def test_restricted_user_list_read_unaffected_by_form_guard(self):
        # web_search_read calls web_read internally; the guard must not break the list.
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self._rpc_request('web_search_read'):
            result = Task.web_search_read([], {'name': {}, 'is_expanded_access_task': {}})
        ids = {rec['id'] for rec in result['records']}
        self.assertIn(self.task_target.id, ids)
        self.assertIn(self.task_pinned.id, ids)

    def test_restricted_user_can_read_every_field_of_task_form(self):
        # 2026-10-03: opening a pinned task failed with "Failed to read field
        # project.task.role_ids" - the default task form reads relational fields whose comodel
        # (project.role, project.task.recurrence) the role had no ACL on. Read every field the
        # form view exposes to this user, as the web client does.
        Task = self.env['project.task'].with_user(self.restricted_user)
        form_fields = Task.get_view(view_type='form')['models']['project.task']
        spec = {
            name: {'fields': {'display_name': {}}} if Task._fields[name].relational else {}
            for name in form_fields
        }
        with self._rpc_request('web_read'):
            Task.browse(self.task_pinned.id).web_read(spec)  # must not raise

    def test_project_user_form_load_unaffected(self):
        Task = self.env['project.task'].with_user(self.control_user)
        with self._rpc_request('web_read'):
            Task.browse(self.task_target.id).web_read({'name': {}})  # must not raise

    def test_restricted_list_hides_tags_column(self):
        view = self.env.ref('serichai_project_security.view_task_list_restricted')
        result = self.env['project.task'].with_user(self.restricted_user).get_view(
            view_id=view.id, view_type='list',
        )
        arch = etree.fromstring(result['arch'])
        tag_ids_node = arch.find(".//field[@name='tag_ids']")
        self.assertIsNotNone(tag_ids_node, 'tag_ids field should still be present in the arch')
        self.assertEqual(tag_ids_node.get('column_invisible'), '1')

    def test_restricted_user_hidden_menus_not_visible(self):
        # _visible_menu_ids() only checks a menu's own group_ids, not whether its ancestor
        # chain is visible - it is not a reliable proxy for whether a menu will actually be
        # reachable/rendered in the top menu bar (load_menus() does that extra ancestor-chain
        # filtering; see test_restricted_user_menu_bar_shows_only_all_tasks below, which covers
        # 'My Tasks' - a menu with no group_ids of its own, only reachable through the now-hidden
        # 'Tasks' parent). This check is scoped to menus that ARE directly group-restricted.
        hidden_menu_xmlids = [
            'project.menu_projects',
            'project.menu_project_report',
            'project.menu_project_config',
            'project.menu_project_management_all_tasks',
            'project.menu_project_management',
        ]
        visible_ids = self.env['ir.ui.menu'].with_user(self.restricted_user)._visible_menu_ids()
        for xmlid in hidden_menu_xmlids:
            menu = self.env.ref(xmlid)
            self.assertNotIn(menu.id, visible_ids, f'{xmlid} should not be visible to the restricted user')

    def test_restricted_user_menu_bar_shows_only_all_tasks(self):
        # load_menus() is what the web client actually calls to build the top menu bar; unlike
        # _visible_menu_ids(), it drops any menu whose ancestor chain up to its app root is not
        # itself visible (see ir_ui_menu.py load_menus()'s "Filter out menus not related to an
        # app" step) - the correct check for "what tabs does the user actually see".
        menus = self.env['ir.ui.menu'].with_user(self.restricted_user).load_menus(False)
        root = self.env.ref('project.menu_main_pm')
        all_tasks_menu = self.env.ref('serichai_project_security.menu_task_all_restricted')
        product_dev_menu = self.env.ref(
            'serichai_project_security.menu_task_product_development_restricted'
        )
        tasks_menu = self.env.ref('project.menu_project_management')
        my_tasks_menu = self.env.ref('project.menu_project_management_my_tasks')

        self.assertIn(root.id, menus, 'Project app icon should be visible')
        self.assertNotIn(tasks_menu.id, menus, "'Tasks' should not be reachable")
        self.assertNotIn(my_tasks_menu.id, menus, "'My Tasks' should not be reachable via the hidden 'Tasks' parent")
        self.assertEqual(
            menus[root.id]['children'], [all_tasks_menu.id, product_dev_menu.id],
            "'All Tasks' and 'Product Development' should be the Project app's only visible "
            "top-level tabs, in that order (sequence 0 then 1)",
        )

    def test_restricted_user_all_tasks_is_default_landing_menu(self):
        # menu_task_all_restricted must be a top-level child of the Project app root and have
        # the lowest sequence among that root's children visible to the restricted user - that's
        # what makes Odoo treat it as the default landing page (see spec.md User Story 5).
        menu = self.env.ref('serichai_project_security.menu_task_all_restricted')
        root = self.env.ref('project.menu_main_pm')
        self.assertEqual(menu.parent_id, root)

        visible_ids = set(self.env['ir.ui.menu'].with_user(self.restricted_user)._visible_menu_ids())
        siblings = self.env['ir.ui.menu'].search([('parent_id', '=', root.id), ('id', 'in', list(visible_ids))])
        self.assertIn(menu, siblings)
        self.assertEqual(menu, siblings.sorted('sequence')[0])

    def test_existing_project_user_unaffected(self):
        Task = self.env['project.task'].with_user(self.control_user)

        # Form access still works (no AccessError from our get_view override).
        Task.get_view(view_type='form')

        # All stages are visible, not just the target one.
        tasks = Task.search([])
        self.assertIn(self.task_target, tasks)
        self.assertIn(self.task_decoy, tasks)

        # The menus this module restricts for the new role remain visible here, matching
        # pre-existing behavior: menu_project_config was already Administrator-only before
        # this module (confirmed in T005), so it is correctly absent for a plain "User" -
        # that's unchanged, not a regression this module introduced.
        still_visible_menu_xmlids = [
            'project.menu_projects',
            'project.menu_project_report',
            'project.menu_project_management_all_tasks',
            'project.menu_project_management',
        ]
        visible_ids = self.env['ir.ui.menu'].with_user(self.control_user)._visible_menu_ids()
        for xmlid in still_visible_menu_xmlids:
            menu = self.env.ref(xmlid)
            self.assertIn(menu.id, visible_ids, f'{xmlid} should still be visible to a normal project user')

        # 2026-08-06: load_menus() (what the web client actually renders) still shows a "Projects"
        # entry - whichever of the two twin menus this Odoo build's _load_menus_blacklist() picks
        # based on the group_project_stages feature toggle - plus "Tasks", for a normal user. The
        # whitelist added to menu_projects_group_stage for the restricted-role fix must not have
        # removed this.
        root = self.env.ref('project.menu_main_pm')
        tasks_menu = self.env.ref('project.menu_project_management')
        projects_variants = {
            self.env.ref('project.menu_projects').id,
            self.env.ref('project.menu_projects_group_stage').id,
        }
        control_menus = self.env['ir.ui.menu'].with_user(self.control_user).load_menus(False)
        self.assertIn(root.id, control_menus)
        top_children = set(control_menus[root.id]['children'])
        self.assertTrue(top_children & projects_variants, 'a Projects tab should still be visible')
        self.assertIn(tasks_menu.id, top_children, 'Tasks tab should still be visible')

        # Tags column is not hidden on the standard (unrestricted) All Tasks list view.
        standard_view = self.env.ref('project.view_task_tree2')
        result = Task.get_view(view_id=standard_view.id, view_type='list')
        arch = etree.fromstring(result['arch'])
        tag_ids_node = arch.find(".//field[@name='tag_ids']")
        self.assertIsNotNone(tag_ids_node)
        self.assertNotEqual(tag_ids_node.get('column_invisible'), '1')
