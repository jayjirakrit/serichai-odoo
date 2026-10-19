from datetime import timedelta
from unittest.mock import patch

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase

from ..hooks import post_init_hook, pre_init_hook
from ..models.project_task import (
    DEFAULT_THRESHOLD, PROJECT_VALUE_LABEL, THRESHOLD_PARAM, parse_amount)

ORDER = 'priority desc, is_high_value desc, state, date_deadline asc, id desc'


@tagged('post_install', '-at_install', 'serichai_project_configuration')
class TestBudgetSort(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Task = cls.env['project.task']
        cls.Project = cls.env['project.project']
        cls.env['ir.config_parameter'].sudo().search([('key', '=', THRESHOLD_PARAM)]).unlink()
        cls.project = cls._make_project('P Float', 'float', 'val_a')
        cls.user = new_test_user(cls.env, login='bs_user', groups='project.group_project_user,base.group_allow_export')
        cls.admin = new_test_user(cls.env, login='bs_admin',
                                  groups='base.group_system,project.group_project_manager')

    def setUp(self):
        super().setUp()
        # get_param is ormcache'd and a test rollback does not clear it: start each test clean
        self.env.registry.clear_cache('stable')
        self.addCleanup(self.env.registry.clear_cache, 'stable')

    # --- fixtures -------------------------------------------------------------------------

    @classmethod
    def _definition(cls, prop_type, key, label=PROJECT_VALUE_LABEL, **extra):
        return dict({'name': key, 'string': label, 'type': prop_type}, **extra)

    @classmethod
    def _make_project(cls, name, prop_type='float', key='val_a', label=PROJECT_VALUE_LABEL,
                      **extra):
        return cls.Project.create({
            'name': name,
            'task_properties_definition': [cls._definition(prop_type, key, label, **extra)],
        })

    def _task(self, value=None, project=None, key='val_a', **vals):
        project = project or self.project
        vals.setdefault('name', 'T')
        vals['project_id'] = project.id
        if value is not None:
            vals['task_properties'] = {key: value}
        return self.Task.create(vals)

    def _set_threshold(self, value):
        param = self.env['ir.config_parameter'].sudo()
        if value is None:
            param.search([('key', '=', THRESHOLD_PARAM)]).unlink()
        else:
            param.set_param(THRESHOLD_PARAM, value)

    def _view_order(self, xmlid, view_type):
        view = self.env.ref(xmlid)
        arch = self.Task.get_view(view_id=view.id, view_type=view_type)['arch']
        return etree.fromstring(arch).get('default_order')

    def _no_property_projects(self):
        """Remove the property from every project so none defines it."""
        self.Project.with_context(active_test=False).search([]).write(
            {'task_properties_definition': []})
        self.env.flush_all()


    def test_float_flag_and_threshold(self):
        self.assertTrue(self._task(60_000_000.0).is_high_value)
        self.assertFalse(self._task(40_000_000.0).is_high_value)
        self.assertFalse(self._task(50_000_000.0).is_high_value)  # strictly greater than the threshold

    def test_custom_threshold_after_recompute(self):
        task = self._task(40_000_000.0)
        self.assertFalse(task.is_high_value)
        self._set_threshold('30000000.0')
        self.Task._recompute_high_value()
        self.assertTrue(task.is_high_value)

    def test_order_views_use_flag(self):
        for xmlid, view_type in (('project.view_task_tree2', 'list'),
                                 ('project.view_task_kanban', 'kanban')):
            self.assertEqual(self._view_order(xmlid, view_type), ORDER, xmlid)

    def test_order_in_restricted_access_views(self):
        """Views built on the project list/kanban inherit the order (only when that module is installed)."""
        views = (('serichai_project_access.project_task_view_list_access', 'list'),
                 ('serichai_project_access.project_task_view_kanban_access', 'kanban'))
        for xmlid, view_type in views:
            if not self.env.ref(xmlid, raise_if_not_found=False):
                self.skipTest('serichai_project_access is not installed')
            self.assertEqual(self._view_order(xmlid, view_type), ORDER, xmlid)

    def test_order_priority_then_high_value_then_deadline(self):
        today = fields.Date.today()
        a = self._task(60_000_000.0, name='A', date_deadline=today + timedelta(days=30))
        b = self._task(40_000_000.0, name='B', date_deadline=today + timedelta(days=1))
        c = self._task(None, name='C', date_deadline=today + timedelta(days=7))
        d = self._task(70_000_000.0, name='D')  # no deadline
        e = self._task(None, name='E', priority='1', date_deadline=today + timedelta(days=90))
        f = self._task(None, name='F', priority='3')
        domain = [('id', 'in', (a | b | c | d | e | f).ids)]
        for xmlid, view_type in (('project.view_task_tree2', 'list'),
                                 ('project.view_task_kanban', 'kanban')):
            order = self._view_order(xmlid, view_type)
            res = self.Task.search(domain, order=order)
            # starred first (3 before 1), then high-value (A before D: deadline set before none),
            # then deadline asc (B, C)
            self.assertEqual(res.mapped('name'), ['F', 'E', 'A', 'D', 'B', 'C'], xmlid)

    def test_open_before_done_then_high_value_beats_state(self):
        today = fields.Date.today()
        order = self._view_order('project.view_task_tree2', 'list')
        done_early = self._task(None, name='DoneEarly', state='1_done',
                                date_deadline=today + timedelta(days=1))
        open_late = self._task(None, name='OpenLate', state='01_in_progress',
                               date_deadline=today + timedelta(days=60))
        high_done = self._task(80_000_000.0, name='HighDone', state='1_done',
                               date_deadline=today + timedelta(days=90))
        domain = [('id', 'in', (done_early | open_late | high_done).ids)]
        # priority, then high-value, then state, then deadline
        self.assertEqual(self.Task.search(domain, order=order).mapped('name'),
                         ['HighDone', 'OpenLate', 'DoneEarly'])

    def test_starred_non_high_value_above_high_value(self):
        high = self._task(80_000_000.0, name='H')
        star = self._task(None, name='S', priority='1')
        res = self.Task.search([('id', 'in', (high | star).ids)], order=ORDER)
        self.assertEqual(res, star | high)
        self.assertEqual(res[0], star)

    def test_model_order_and_portal_list_untouched(self):
        self.assertNotIn('is_high_value', self.Task._order)
        self.assertEqual(self.Task._order, 'priority desc, sequence, date_deadline asc, id desc')
        order = self._view_order('project.project_task_view_tree_main_base', 'list')
        self.assertNotIn('is_high_value', order)

    def test_non_main_views_keep_core_order_and_no_value_column(self):
        core = 'priority desc, sequence, state, date_deadline asc, id desc'
        for xmlid, view_type in (
                ('project.project_task_templates_list', 'list'),
                ('project.project_task_tree_view_project_milestone', 'list'),
                ('project.project_task_templates_kanban', 'kanban'),
                ('project.project_task_kanban_view_project_milestone', 'kanban')):
            view = self.env.ref(xmlid)
            root = etree.fromstring(self.Task.get_view(view_id=view.id, view_type=view_type)['arch'])
            self.assertEqual(root.get('default_order'), core, xmlid)
            self.assertFalse(root.xpath('//field[@name="project_value"]'), xmlid)


    def test_parse_amount(self):
        self.assertEqual(parse_amount('char', '60,000,000'), 60000000.0)
        self.assertEqual(parse_amount('text', ' 1 200.5 '), 1200.5)
        self.assertEqual(parse_amount('integer', 7), 7.0)
        self.assertEqual(parse_amount('monetary', 7.5), 7.5)
        for ptype, raw in (('char', 'abc'), ('char', 'nan'), ('char', 'inf'), ('char', ''),
                           ('char', None), ('char', ['x']), ('float', float('nan')),
                           ('float', float('inf')), ('float', True), ('integer', True),
                           ('many2one', 5), ('selection', 'a'), ('tags', ['a']),
                           ('date', '2026-01-01'), ('boolean', True), ('float', None)):
            self.assertEqual(parse_amount(ptype, raw), 0.0, (ptype, raw))

    def test_char_property_flag(self):
        project = self._make_project('P Char', 'char', 'val_c')
        self.assertTrue(self._task('60,000,000', project, 'val_c').is_high_value)
        for raw in ('abc', 'nan', ''):
            task = self._task(raw, project, 'val_c')
            self.assertFalse(task.is_high_value, raw)
        # a task holding garbage saves without error
        task = self._task('abc', project, 'val_c')
        task.write({'task_properties': {'val_c': 'still abc'}})
        self.assertFalse(task.is_high_value)

    def test_non_amount_types_give_false(self):
        p_sel = self._make_project(
            'P Sel', 'selection', 'val_s',
            selection=[['a', 'A'], ['b', 'B']])
        self.assertFalse(self._task('a', p_sel, 'val_s').is_high_value)
        partner = self.env['res.partner'].create({'name': 'X'})
        p_m2o = self._make_project('P M2O', 'many2one', 'val_m', comodel='res.partner')
        self.assertFalse(self._task(partner.id, p_m2o, 'val_m').is_high_value)
        self.assertEqual(self._task(partner.id, p_m2o, 'val_m').project_value, 0.0)

    def test_missing_property_or_project(self):
        self.assertFalse(self._task(None).is_high_value)
        no_prop = self.Project.create({'name': 'No prop'})
        self.assertFalse(self.Task.create({'name': 'x', 'project_id': no_prop.id}).is_high_value)
        self.assertFalse(self.Task.create({'name': 'private'}).is_high_value)

    def test_label_match_across_projects(self):
        spaced = self._make_project('P Spaced', 'float', 'other_key', label='  %s  ' % PROJECT_VALUE_LABEL)
        self.assertTrue(self._task(60_000_000.0, spaced, 'other_key').is_high_value)
        self.assertTrue(self._task(60_000_000.0).is_high_value)

    def test_duplicate_label_first_wins(self):
        project = self.Project.create({
            'name': 'P Dup',
            'task_properties_definition': [
                self._definition('float', 'first'), self._definition('float', 'second')],
        })
        task = self.Task.create({'name': 'd', 'project_id': project.id,
                                 'task_properties': {'first': 1.0, 'second': 90_000_000.0}})
        self.assertFalse(task.is_high_value)
        task.task_properties = {'first': 90_000_000.0, 'second': 1.0}
        self.assertTrue(task.is_high_value)

    def test_move_between_projects(self):
        no_prop = self.Project.create({'name': 'No prop'})
        task = self._task(60_000_000.0)
        self.assertTrue(task.is_high_value)
        task.project_id = no_prop
        self.assertFalse(task.is_high_value)
        task.project_id = self.project
        # moving back re-evaluates the flag: the property was kept (60M > 50M threshold)
        self.assertEqual(task.task_properties['val_a'], 60_000_000.0)
        self.assertTrue(task.is_high_value)
        task.task_properties = {'val_a': 1_000.0}
        self.assertFalse(task.is_high_value)
        task.task_properties = {'val_a': 60_000_000.0}
        self.assertTrue(task.is_high_value)

    def test_move_keeps_value_when_both_define_property(self):
        other = self._make_project('P Other', 'float', 'val_a')
        task = self._task(60_000_000.0)
        task.project_id = other
        self.assertTrue(task.is_high_value)

    def test_definition_change_needs_recompute(self):
        task = self._task(60_000_000.0)
        self.assertTrue(task.is_high_value)
        self.project.task_properties_definition = [
            self._definition('float', 'val_a', label='renamed')]
        self.env.flush_all()
        self.assertTrue(task.is_high_value)
        self.Task._recompute_high_value()
        self.assertFalse(task.is_high_value)

    def test_edit_value_updates_flag(self):
        task = self._task(10.0)
        self.assertFalse(task.is_high_value)
        task.task_properties = {'val_a': 99_000_000.0}
        self.assertTrue(task.is_high_value)
        task.task_properties = {'val_a': 5.0}
        self.assertFalse(task.is_high_value)

    def test_no_property_anywhere_order(self):
        self._no_property_projects()
        today = fields.Date.today()
        a = self.Task.create({'name': 'A', 'date_deadline': today + timedelta(days=5)})
        b = self.Task.create({'name': 'B', 'date_deadline': today + timedelta(days=1)})
        c = self.Task.create({'name': 'C'})
        d = self.Task.create({'name': 'D', 'priority': '1'})
        order = self._view_order('project.view_task_tree2', 'list')
        ids = [('id', 'in', (a | b | c | d).ids)]
        self.assertEqual(self.Task.search(ids, order=order).mapped('name'), ['D', 'B', 'A', 'C'])
        self.assertEqual(order, ORDER)
        # with no property anywhere the flag is always False, so the order reduces to the rest
        self.assertEqual(self.Task.search(ids, order=order),
                         self.Task.search(ids, order=order.replace('is_high_value desc, ', '')))

    def test_bad_task_does_not_stop_batch(self):
        bad = self._task(11.0, name='bad')
        good = self._task(60_000_000.0, name='good')
        real = parse_amount

        def flaky(prop_type, raw):
            if raw == 11.0:
                raise ValueError("unreadable")
            return real(prop_type, raw)
        with patch('odoo.addons.serichai_project_configuration.models.project_task.parse_amount',
                   flaky):
            (bad | good)._compute_is_high_value()
        self.assertFalse(bad.is_high_value)
        self.assertTrue(good.is_high_value)

    def test_archived_and_projectless_evaluated(self):
        task = self._task(60_000_000.0)
        task.active = False
        self.env.flush_all()
        self.env.cr.execute("UPDATE project_task SET is_high_value = false WHERE id = %s", (task.id,))
        task.invalidate_recordset()
        self.Task._recompute_high_value()
        self.assertTrue(task.is_high_value)


    def test_project_value_for_each_type(self):
        user_task = self.Task.with_user(self.user)
        cases = (('float', 'v1', 60_000_000.5, 60_000_000.5),
                 ('integer', 'v2', 123, 123.0),
                 ('monetary', 'v3', 77.25, 77.25),
                 ('char', 'v4', '60,000,000', 60_000_000.0))
        for ptype, key, raw, expected in cases:
            extra = {'currency_field': 'cur'} if ptype == 'monetary' else {}
            if ptype == 'monetary':
                project = self.Project.create({
                    'name': 'P mon',
                    'task_properties_definition': [
                        self._definition('monetary', key, currency_field='cur'),
                        {'name': 'cur', 'string': 'Cur', 'type': 'many2one',
                         'comodel': 'res.currency'}],
                })
            else:
                project = self._make_project('P %s' % ptype, ptype, key, **extra)
            task = self._task(raw, project, key)
            self.assertEqual(user_task.browse(task.id).project_value, expected, ptype)

    def test_project_value_zero_cases(self):
        user_task = self.Task.with_user(self.user)
        no_prop = self.Project.create({'name': 'No prop'})
        t1 = self._task(None)
        t2 = self.Task.create({'name': 'x', 'project_id': no_prop.id})
        t3 = self.Task.create({'name': 'private'})
        for task in (t1, t2, t3):
            self.assertEqual(user_task.browse(task.id).project_value, 0.0)
        self.assertEqual(self.Task.new({'name': 'unsaved'}).project_value, 0.0)

    def test_high_value_filter_and_view_arch(self):
        high = self._task(60_000_000.0)
        low = self._task(1.0)
        res = self.Task.search([('is_high_value', '=', True), ('id', 'in', (high | low).ids)])
        self.assertEqual(res, high)
        arch = self.Task.get_view(self.env.ref('project.view_task_tree2').id, 'list')['arch']
        node = etree.fromstring(arch).xpath('//field[@name="project_value"]')
        self.assertEqual(len(node), 1)
        self.assertEqual(node[0].get('optional'), 'show')
        search = self.Task.get_view(self.env.ref('project.view_task_search_form').id, 'search')['arch']
        self.assertTrue(etree.fromstring(search).xpath('//filter[@name="high_value"]'))


    def test_threshold_fallbacks(self):
        Settings = self.env['res.config.settings']
        for raw in (None, '', 'abc', '-5', 'inf', 'nan'):
            self._set_threshold(raw)
            self.assertEqual(self.Task._get_high_value_threshold(), DEFAULT_THRESHOLD, raw)
            self.assertEqual(Settings.get_values()['serichai_high_value_threshold'],
                             DEFAULT_THRESHOLD, raw)

    def test_threshold_zero_is_real(self):
        settings = self.env['res.config.settings'].with_user(self.admin).create(
            {'serichai_high_value_threshold': 0.0})
        settings.set_values()
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param(THRESHOLD_PARAM), '0.0')
        self.assertEqual(self.Task._get_high_value_threshold(), 0.0)
        self.assertEqual(
            self.env['res.config.settings'].get_values()['serichai_high_value_threshold'], 0.0)
        positive = self._task(1.0)
        zero = self._task(0.0)
        self.Task._recompute_high_value()
        self.assertTrue(positive.is_high_value)
        self.assertFalse(zero.is_high_value)

    def test_settings_save_then_recalculate(self):
        task = self._task(40_000_000.0)
        settings = self.env['res.config.settings'].with_user(self.admin).create(
            {'serichai_high_value_threshold': 30_000_000.0})
        self.env.flush_all()  # stored computes are lazy inside one transaction: settle the flag first
        settings.set_values()
        self.assertFalse(task.is_high_value)
        result = settings.action_serichai_recompute_high_value()
        self.assertEqual(result['tag'], 'display_notification')
        self.assertTrue(task.is_high_value)

    def test_unrelated_setting_changes_nothing(self):
        task = self._task(60_000_000.0)
        self._set_threshold('30000000.0')
        settings = self.env['res.config.settings'].with_user(self.admin).create({})
        self.assertEqual(settings.serichai_high_value_threshold, 30_000_000.0)
        settings.set_values()
        self.assertEqual(self.Task._get_high_value_threshold(), 30_000_000.0)
        self.assertTrue(task.is_high_value)

    def test_non_admin_cannot_recalculate(self):
        settings = self.env['res.config.settings'].with_user(self.admin).create({})
        with self.assertRaises(AccessError):
            settings.with_user(self.user).action_serichai_recompute_high_value()

    def test_recompute_batches_and_archived(self):
        tasks = self.Task
        for i in range(5):
            tasks |= self._task(60_000_000.0, name='B%s' % i)
        tasks[0].active = False
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE project_task SET is_high_value = false WHERE id IN %s", (tuple(tasks.ids),))
        tasks.invalidate_recordset()
        self.assertFalse(any(tasks.mapped('is_high_value')))
        self.Task._recompute_high_value(batch_size=2)
        self.assertTrue(all(tasks.with_context(active_test=False).mapped('is_high_value')))

    def test_recompute_continues_after_unreadable_task(self):
        tasks = self._task(60_000_000.0) | self._task(60_000_000.0) | self._task(60_000_000.0)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE project_task SET is_high_value = false WHERE id IN %s", (tuple(tasks.ids),))
        tasks.invalidate_recordset()
        # the recompute runs as superuser, so a user with no access still gets every task done
        self.Task.with_user(self.user)._recompute_high_value(batch_size=1)
        self.assertTrue(all(tasks.mapped('is_high_value')))

    def test_settings_view_has_block(self):
        arch = self.env['res.config.settings'].get_view(
            self.env.ref('project.res_config_settings_view_form').id, 'form')['arch']
        root = etree.fromstring(arch)
        self.assertTrue(root.xpath('//field[@name="serichai_high_value_threshold"]'))
        self.assertTrue(root.xpath('//button[@name="action_serichai_recompute_high_value"]'))


    def test_post_init_hook(self):
        high = self._task(60_000_000.0)
        low = self._task(1.0)
        garbage = self._task('abc', self._make_project('P Char', 'char', 'val_c'), 'val_c')
        self.env.flush_all()
        self.env.cr.execute("UPDATE project_task SET is_high_value = false")
        self.env.invalidate_all()
        post_init_hook(self.env)
        self.assertTrue(high.is_high_value)
        self.assertFalse(low.is_high_value)
        self.assertFalse(garbage.is_high_value)

    def test_post_init_hook_without_property(self):
        self._no_property_projects()
        self.Task.create({'name': 'x'})
        post_init_hook(self.env)

    def test_pre_init_hook_idempotent(self):
        pre_init_hook(self.env)  # column exists already: must not raise
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'project_task' AND column_name = 'is_high_value'")
        self.assertTrue(self.env.cr.fetchone())

    def test_pre_init_hook_new_column_defaults_false(self):
        self._task(60_000_000.0)
        self.env.flush_all()
        self.env.cr.execute("ALTER TABLE project_task DROP COLUMN is_high_value")
        pre_init_hook(self.env)
        self.env.cr.execute("SELECT count(*) FROM project_task")
        total = self.env.cr.fetchone()[0]
        self.assertTrue(total)
        self.env.cr.execute("SELECT count(*) FROM project_task WHERE is_high_value IS NULL")
        self.assertEqual(self.env.cr.fetchone()[0], 0)
        self.env.cr.execute("SELECT count(*) FROM project_task WHERE is_high_value = false")
        self.assertEqual(self.env.cr.fetchone()[0], total)
        self.env.invalidate_all()


    def _patch_read(self, mode, only_ids=None):
        model_cls = self.registry['project.task']
        orig = model_cls.read

        def read(this, fields=None, load='_classic_read'):
            if mode == 'deny':
                raise AccessError("denied")
            rows = orig(this, fields, load)
            for row in rows:
                if row.get('task_properties') and (only_ids is None or row['id'] in only_ids):
                    row['task_properties'] = [
                        p for p in row['task_properties']
                        if (p.get('string') or '').strip() != PROJECT_VALUE_LABEL]
            return rows
        self.patch(model_cls, 'read', read)

    def test_hidden_property_gives_zero(self):
        task = self._task(60_000_000.0)
        before_order = self.Task.search([('id', '=', task.id)], order=ORDER)
        self.assertEqual(self.Task.with_user(self.user).browse(task.id).project_value,
                         60_000_000.0)
        self._patch_read('strip')
        as_user = self.Task.with_user(self.user).browse(task.id)
        as_user.invalidate_recordset()
        self.assertEqual(as_user.project_value, 0.0)
        self.assertTrue(task.is_high_value)
        self.assertEqual(self.Task.with_user(self.user).search([('id', '=', task.id)], order=ORDER),
                         before_order)
        exported = as_user.export_data(['project_value'])['datas']
        self.assertEqual(float(exported[0][0] or 0), 0.0)

    def test_denied_read_gives_zero_without_error(self):
        task = self._task(60_000_000.0)
        self._patch_read('deny')
        as_user = self.Task.with_user(self.user).browse(task.id)
        as_user.invalidate_recordset()
        self.assertEqual(as_user.project_value, 0.0)
        self.assertTrue(task.is_high_value)
        exported = as_user.export_data(['project_value'])['datas']
        self.assertEqual(float(exported[0][0] or 0), 0.0)

    def test_unhidden_project_still_shows_amount(self):
        other_project = self._make_project('P other', 'float', 'o_key')
        task_hidden = self._task(7_000.0)
        task_visible = self._task(5_000.0, other_project, 'o_key')
        # hide the property only on the first project's task: the other one keeps its amount
        self._patch_read('strip', only_ids=task_hidden.ids)
        as_user = self.Task.with_user(self.user)
        hidden, visible = as_user.browse(task_hidden.id), as_user.browse(task_visible.id)
        (hidden | visible).invalidate_recordset()
        self.assertEqual(hidden.project_value, 0.0)
        self.assertEqual(visible.project_value, 5_000.0)
