from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests import tagged, new_test_user
from odoo.tests.common import TransactionCase

TARGET_STAGE_NAME = 'วางแผนการผลิต'


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

    def test_restricted_user_sees_all_stage_tasks_while_stage_filter_disabled(self):
        # 2026-08-06: rule_task_stage_restricted in security/ir_rule.xml is TEMPORARILY
        # commented out (explicit user request) because no project.task.type named exactly
        # "วางแผนการผลิต" currently exists in this deployment - filtering to it would show
        # every restricted user an empty list. Once that stage exists and the rule is
        # re-enabled, restore this test to its original assertions (only task_target visible,
        # task_decoy excluded - see git history for the prior version).
        tasks = self.env['project.task'].with_user(self.restricted_user).search([])
        self.assertIn(self.task_target, tasks)
        self.assertIn(self.task_decoy, tasks)

    def test_restricted_user_form_access_denied(self):
        Task = self.env['project.task'].with_user(self.restricted_user)
        with self.assertRaises(AccessError):
            Task.get_view(view_type='form')

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
        tasks_menu = self.env.ref('project.menu_project_management')
        my_tasks_menu = self.env.ref('project.menu_project_management_my_tasks')

        self.assertIn(root.id, menus, 'Project app icon should be visible')
        self.assertNotIn(tasks_menu.id, menus, "'Tasks' should not be reachable")
        self.assertNotIn(my_tasks_menu.id, menus, "'My Tasks' should not be reachable via the hidden 'Tasks' parent")
        self.assertEqual(
            menus[root.id]['children'], [all_tasks_menu.id],
            "'All Tasks' should be the Project app's only visible top-level tab",
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
