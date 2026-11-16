import importlib.util
from pathlib import Path
from unittest.mock import patch


from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCreateMoFromTask(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.manager = Users.create({
            'name': 'Project Manager',
            'login': 'create_mo_manager',
            'email': 'create_mo_manager@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.project_user = Users.create({
            'name': 'Project User',
            'login': 'create_mo_project_user',
            'email': 'create_mo_project_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('project.group_project_user').id,
            ])],
        })
        cls.mrp_user = Users.create({
            'name': 'MRP User',
            'login': 'create_mo_mrp_user',
            'email': 'create_mo_mrp_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('mrp.group_mrp_user').id,
            ])],
        })
        cls.project = cls.env['project.project'].create({
            'name': 'Create MO Project',
            'user_id': cls.manager.id,
        })
        cls.task = cls.env['project.task'].create({
            'name': 'Create MO Task',
            'project_id': cls.project.id,
        })
        uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.products = cls.env['product.product'].create([
            {'name': 'Finish Good %s' % i, 'type': 'consu', 'uom_id': uom_unit.id}
            for i in range(3)
        ])
        cls.task.finish_goods_ids = cls.products

    def _create_wizard(self, task=None, user=None, as_user=None):
        task = task or self.task
        wizard = self.env['project.task.create.mo']
        if as_user:
            wizard = wizard.with_user(as_user)
            task = task.with_user(as_user)
        return wizard.create({'task_id': task.id, 'user_id': (user or self.mrp_user).id})

    def _task_mos(self, task=None):
        return self.env['mrp.production'].search([('project_task_ids', 'in', (task or self.task).ids)])

    # ---- US1

    def test_create_one_mo_per_finish_good(self):
        action = self._create_wizard().action_confirm()
        mos = self._task_mos()
        self.assertEqual(len(mos), 3)
        self.assertEqual(mos.product_id, self.products)
        for mo in mos:
            self.assertEqual(mo.state, 'draft')
            self.assertEqual(mo.user_id, self.mrp_user)
            self.assertEqual(mo.project_id, self.project)
            self.assertEqual(mo.origin, self.task.name)
        self.assertEqual(self.task.mrp_production_ids, mos)
        self.assertEqual(self.task.mrp_production_count, 3)
        self.assertEqual(action['res_model'], 'mrp.production')
        self.assertIn('3', action['name'])
        self.assertEqual(self.env['mrp.production'].search(action['domain']), mos)

    def test_mo_quantity_follows_bom(self):
        """FR-006: the MO quantity is the one from the product's BoM."""
        product = self.products[0]
        self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 5.0,
            'type': 'normal',
        })
        self._create_wizard().action_confirm()
        mo = self._task_mos().filtered(lambda m: m.product_id == product)
        self.assertEqual(mo.product_qty, 5.0)
        self.assertEqual(mo.project_id, self.project, 'the BoM compute must not overwrite the project')

    def test_no_buy_goods_field(self):
        self.assertNotIn('buy_goods_ids', self.env['project.task']._fields)

    def test_view_mrp_productions_action(self):
        self._create_wizard().action_confirm()
        other_mo = self.env['mrp.production'].create({'product_id': self.products[0].id})
        action = self.task.action_view_mrp_productions()
        found = self.env[action['res_model']].search(action['domain'])
        self.assertEqual(found, self._task_mos())
        self.assertNotIn(other_mo, found)

    def test_wizard_assignee_required(self):
        with self.assertRaises(Exception), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.env['project.task.create.mo'].create({'task_id': self.task.id, 'user_id': False})

    # ---- US2

    def test_rerun_creates_nothing(self):
        self._create_wizard().action_confirm()
        action = self._create_wizard().action_confirm()
        self.assertEqual(len(self._task_mos()), 3)
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')

    def test_added_product_creates_one(self):
        self._create_wizard().action_confirm()
        extra = self.env['product.product'].create({'name': 'Extra FG', 'type': 'consu'})
        self.task.finish_goods_ids |= extra
        self._create_wizard().action_confirm()
        mos = self._task_mos()
        self.assertEqual(len(mos), 4)
        self.assertEqual(len(mos.filtered(lambda m: m.product_id == extra)), 1)

    def test_cancelled_mo_is_recreated(self):
        self._create_wizard().action_confirm()
        mo = self._task_mos().filtered(lambda m: m.product_id == self.products[0])
        mo.action_cancel()
        self._create_wizard().action_confirm()
        live = self._task_mos().filtered(lambda m: m.state != 'cancel' and m.product_id == self.products[0])
        self.assertEqual(len(live), 1)
        self.assertEqual(len(self._task_mos()), 4)

    def test_manual_link_counts_as_coverage(self):
        manual = self.env['mrp.production'].create({'product_id': self.products[0].id})
        self.task.mrp_production_ids = manual
        self._create_wizard().action_confirm()
        mos = self._task_mos()
        self.assertEqual(len(mos), 3)
        self.assertEqual(len(mos.filtered(lambda m: m.product_id == self.products[0])), 1)

    def test_sequential_confirms_no_duplicates(self):
        wizard = self._create_wizard()
        wizard.action_confirm()
        wizard.action_confirm()
        self.assertEqual(len(self._task_mos()), 3)

    def test_project_change_keeps_existing_mos_project(self):
        """Edge case: moving the task leaves existing MOs; a later run uses the new project."""
        self._create_wizard().action_confirm()
        old_mos = self._task_mos()
        other = self.env['project.project'].create({'name': 'Other Project', 'user_id': self.manager.id})
        self.task.project_id = other
        extra = self.env['product.product'].create({'name': 'Moved Extra FG', 'type': 'consu'})
        self.task.finish_goods_ids |= extra
        self._create_wizard().action_confirm()
        self.assertEqual(old_mos.project_id, self.project)
        new_mo = self._task_mos() - old_mos
        self.assertEqual(len(new_mo), 1)
        self.assertEqual(new_mo.product_id, extra)
        self.assertEqual(new_mo.project_id, other)

    def test_removed_finish_good_leaves_mo_unchanged(self):
        """Edge case: removing a product from Finish Goods does not touch its MO."""
        self._create_wizard().action_confirm()
        removed = self.products[0]
        mo = self._task_mos().filtered(lambda m: m.product_id == removed)
        self.task.finish_goods_ids -= removed
        self.assertTrue(mo.exists())
        self.assertEqual(mo.state, 'draft')
        self.assertIn(mo, self.task.mrp_production_ids)
        self._create_wizard().action_confirm()
        self.assertEqual(len(self._task_mos()), 3)
        self.assertEqual(mo.state, 'draft')

    # ---- US5

    def test_project_user_without_mrp_rights(self):
        self.assertFalse(self.project_user.has_group('mrp.group_mrp_user'))
        self.project.privacy_visibility = 'employees'
        self.task.message_subscribe(partner_ids=self.project_user.partner_id.ids)
        action = self.task.with_user(self.project_user).action_open_create_mo_wizard()
        self.assertEqual(action['res_model'], 'project.task.create.mo')
        wizard = self._create_wizard(as_user=self.project_user, user=self.mrp_user)
        wizard.action_confirm()
        mos = self._task_mos()
        self.assertEqual(len(mos), 3)
        self.assertEqual(mos.create_uid, self.project_user)
        self.assertEqual(mos.user_id, self.mrp_user)

    def test_user_without_mo_read_gets_notification(self):
        self.project.privacy_visibility = 'employees'
        self.task.message_subscribe(partner_ids=self.project_user.partner_id.ids)
        wizard = self._create_wizard(as_user=self.project_user, user=self.mrp_user)
        self.assertFalse(self.env['mrp.production'].with_user(self.project_user).has_access('read'))
        action = wizard.action_confirm()
        self.assertEqual(action['tag'], 'display_notification')
        self.assertEqual(action['params']['next'], {'type': 'ir.actions.act_window_close'})
        self.assertEqual(len(self._task_mos()), 3)

    def test_user_without_task_write_refused(self):
        # a portal-like internal user with no project group cannot write the task
        reader = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'No Project Rights',
            'login': 'create_mo_no_rights',
            'email': 'create_mo_no_rights@example.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        task = self.task.with_user(reader)
        with self.assertRaises(AccessError):
            task.action_open_create_mo_wizard()
        with self.assertRaises(AccessError):
            task._create_mos_from_finish_goods(self.mrp_user)
        self.assertFalse(self._task_mos())

    # ---- US3

    def test_wizard_open_without_finish_goods(self):
        self.task.finish_goods_ids = False
        with self.assertRaises(UserError):
            self.task.action_open_create_mo_wizard()
        with self.assertRaises(UserError):
            self.env['project.task.create.mo'].create(
                {'task_id': self.task.id, 'user_id': self.mrp_user.id}).action_confirm()
        with self.assertRaises(UserError):
            self.task._create_mos_from_finish_goods(self.mrp_user)
        self.assertFalse(self._task_mos())

    def test_wizard_open_without_project(self):
        self.task.project_id = False
        with self.assertRaises(UserError):
            self.task.action_open_create_mo_wizard()
        with self.assertRaises(UserError):
            self._create_wizard().action_confirm()
        with self.assertRaises(UserError):
            self.task._create_mos_from_finish_goods(self.mrp_user)
        self.assertFalse(self._task_mos())

    def test_warning_names_only_bomless_products(self):
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.products[0].product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })
        warning = self._create_wizard().warning
        self.assertTrue(warning)
        self.assertNotIn(self.products[0].display_name, warning)
        self.assertIn(self.products[1].display_name, warning)
        self.assertIn(self.products[2].display_name, warning)

    def test_no_warning_when_all_have_bom(self):
        for product in self.products:
            self.env['mrp.bom'].create({
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_qty': 1.0,
                'type': 'normal',
            })
        self.assertFalse(self._create_wizard().warning)

    def test_confirm_with_warning_still_creates(self):
        wizard = self._create_wizard()
        self.assertTrue(wizard.warning)
        wizard.action_confirm()
        self.assertEqual(len(self._task_mos()), 3)

    # ---- US4

    def _run_checks(self):
        """Run the deferred (precommit) "all MOs done" checks, as the commit would."""
        self.env.cr.flush()

    def _mails(self, project=None):
        self._run_checks()
        partner = (project or self.project).user_id.partner_id
        return self.env['mail.mail'].sudo().search_count([('recipient_ids', 'in', partner.ids)])

    def _make_mos(self, count=2, project=None):
        project = project or self.project
        return self.env['mrp.production'].create([
            {'product_id': self.products[i % 3].id, 'project_id': project.id} for i in range(count)])

    def _finish(self, mo):
        mo.action_confirm()
        mo.qty_producing = mo.product_qty
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self._run_checks()

    def test_default_template(self):
        template = self.env.ref('serichai_project_mo.mail_template_all_mos_done')
        self.assertEqual(template.model, 'project.project')
        self.assertEqual(self.project.mo_done_mail_template_id, template)
        self.assertFalse(self.project.mo_done_mail_sent)

    def test_template_domain_only_project_templates(self):
        domain = self.env['project.project']._fields['mo_done_mail_template_id'].domain
        self.assertEqual(domain, "[('model', '=', 'project.project')]")

    def test_mail_after_last_mo_done(self):
        mos = self._make_mos(2)
        before = self._mails()
        self._finish(mos[0])
        self.assertEqual(self._mails(), before)
        self._finish(mos[1])
        self.assertEqual(self._mails(), before + 1)
        self.assertTrue(self.project.mo_done_mail_sent)

    def test_mail_body_renders_under_sudo(self):
        """The rich template renders for the queued mail: project name and every done MO."""
        mos = self._make_mos(2)
        for mo in mos:
            self._finish(mo)
        self._run_checks()
        mail = self.env['mail.mail'].sudo().search(
            [('recipient_ids', 'in', self.manager.partner_id.ids)], order='id desc', limit=1)
        self.assertIn(self.project.name, mail.body_html)
        for mo in mos:
            self.assertIn(mo.name, mail.body_html)
        self.assertIn(self.project.name, mail.subject)

    def test_open_mo_no_mail(self):
        before = self._mails()
        self._make_mos(1)
        self.assertEqual(self._mails(), before)

    def test_all_cancelled_no_mail(self):
        before = self._mails()
        mos = self._make_mos(2)
        mos.action_cancel()
        self.assertEqual(self._mails(), before)
        self.assertFalse(self.project.mo_done_mail_sent)

    def test_repeated_check_sends_once(self):
        mos = self._make_mos(1)
        before = self._mails()
        self._finish(mos)
        self._run_checks()
        self.project._check_all_mos_done()
        self.project._check_all_mos_done()
        self.assertEqual(self._mails(), before + 1)

    def test_new_mo_starts_new_batch(self):
        before = self._mails()
        self._finish(self._make_mos(1))
        self.assertEqual(self._mails(), before + 1)
        manual = self._make_mos(1)  # manual MO resets the flag
        self.assertFalse(self.project.mo_done_mail_sent)
        self._finish(manual)
        self.assertEqual(self._mails(), before + 2)

    def test_project_write_resets_flag(self):
        self._finish(self._make_mos(1))
        self.assertTrue(self.project.mo_done_mail_sent)
        other = self.env['project.project'].create({'name': 'Other', 'user_id': self.manager.id})
        mo = self.env['mrp.production'].create({'product_id': self.products[0].id, 'project_id': other.id})
        self._finish(mo)
        self.assertTrue(other.mo_done_mail_sent)
        mo2 = self.env['mrp.production'].create({'product_id': self.products[0].id})
        mo2.project_id = self.project
        self._run_checks()  # state/project_id reach the database (and the hook) on flush
        self.assertFalse(self.project.mo_done_mail_sent)

    def test_no_manager_no_mail_and_flag_unset(self):
        project = self.env['project.project'].create({'name': 'No Manager', 'user_id': False})
        mo = self.env['mrp.production'].create({'product_id': self.products[0].id, 'project_id': project.id})
        mails_before = self.env['mail.mail'].sudo().search_count([])
        self._finish(mo)
        self._run_checks()
        self.assertEqual(self.env['mail.mail'].sudo().search_count([]), mails_before)
        self.assertFalse(project.mo_done_mail_sent)
        project.user_id = self.manager
        before = self._mails(project)  # runs pending checks
        project._check_all_mos_done()
        self.assertEqual(self._mails(project), before + 1)
        self.assertTrue(project.mo_done_mail_sent)

    def test_chosen_template_used(self):
        template = self.env.ref('serichai_project_mo.mail_template_all_mos_done').copy({
            'name': 'Custom', 'subject': 'CUSTOM SUBJECT'})
        self.project.mo_done_mail_template_id = template
        self._finish(self._make_mos(1))
        self._run_checks()
        mail = self.env['mail.mail'].sudo().search(
            [('recipient_ids', 'in', self.manager.partner_id.ids)], order='id desc', limit=1)
        self.assertEqual(mail.subject, 'CUSTOM SUBJECT')

    def test_empty_template_falls_back_to_default(self):
        self.project.mo_done_mail_template_id = False
        before = self._mails()
        self._finish(self._make_mos(1))
        self.assertEqual(self._mails(), before + 1)

    def test_cancel_last_open_mo_triggers_check(self):
        done, open_mo = self._make_mos(2)
        self._finish(done)
        before = self._mails()
        open_mo.action_cancel()
        self.assertEqual(self._mails(), before + 1)

    def test_unlink_last_open_mo_triggers_check(self):
        done, open_mo = self._make_mos(2)
        self._finish(done)
        before = self._mails()
        open_mo.unlink()
        self.assertEqual(self._mails(), before + 1)

    def test_trigger_user_without_mail_rights(self):
        mos = self._make_mos(1)
        mo = mos.with_user(self.mrp_user)
        self.assertFalse(self.mrp_user.has_group('base.group_system'))
        before = self._mails()
        mo.action_confirm()
        mo.qty_producing = mo.product_qty
        mo.button_mark_done()
        self.assertEqual(self._mails(), before + 1)

    def test_cancelled_mo_joining_project_does_not_reset_flag(self):
        before = self._mails()
        self._finish(self._make_mos(1))
        self.assertTrue(self.project.mo_done_mail_sent)
        cancelled = self.env['mrp.production'].create({'product_id': self.products[0].id})
        cancelled.action_cancel()
        cancelled.project_id = self.project
        self.assertEqual(cancelled.state, 'cancel')
        self.assertTrue(self.project.mo_done_mail_sent)
        self.assertEqual(self._mails(), before + 1)

    def test_same_project_write_does_not_reset_flag(self):
        mo = self._make_mos(1)
        before = self._mails()
        self._finish(mo)
        self.assertTrue(self.project.mo_done_mail_sent)
        mo.project_id = self.project
        self.assertTrue(self.project.mo_done_mail_sent)
        self.assertEqual(self._mails(), before + 1)

    def _locked_out(self):
        """Simulate another transaction holding the project row: nothing can be locked."""
        return patch.object(self.registry['project.project'], 'try_lock_for_update',
                            lambda self, **kw: self.browse())

    def test_locked_project_does_not_raise_and_is_skipped(self):
        mo = self._make_mos(1)
        mo.action_confirm()
        mo.qty_producing = mo.product_qty
        before = self._mails()
        with self._locked_out():
            mo.button_mark_done()  # the user's own change must go through
            self._run_checks()
        self.assertEqual(mo.state, 'done')
        self.assertFalse(self.project.mo_done_mail_sent)
        self.assertEqual(self._mails(), before)

    # ---- Review follow-ups: template visibility, warning, deferred triggers

    def test_missing_template_logs_warning_and_leaves_flag_unset(self):
        self.project.mo_done_mail_template_id = False
        self.env.ref('serichai_project_mo.mail_template_all_mos_done').unlink()
        mo = self._make_mos(1)
        before = self._mails()
        with self.assertLogs('odoo.addons.serichai_project_mo.models.project_project', 'WARNING') as logs:
            self._finish(mo)
            self._run_checks()
        self.assertEqual(len(logs.records), 1)
        self.assertIn(self.project.name, logs.output[0])
        self.assertEqual(self._mails(), before)
        self.assertFalse(self.project.mo_done_mail_sent)

    def test_set_default_template_on_existing_projects(self):
        template = self.env.ref('serichai_project_mo.mail_template_all_mos_done')
        custom = template.copy({'name': 'Custom'})
        empty = self.env['project.project'].create({'name': 'Empty', 'mo_done_mail_template_id': False})
        archived = self.env['project.project'].create(
            {'name': 'Archived', 'mo_done_mail_template_id': False, 'active': False})
        chosen = self.env['project.project'].create({'name': 'Chosen', 'mo_done_mail_template_id': custom.id})
        self.env['project.project']._set_default_mo_done_mail_template()
        self.assertEqual(empty.mo_done_mail_template_id, template)
        self.assertEqual(archived.mo_done_mail_template_id, template)
        self.assertEqual(chosen.mo_done_mail_template_id, custom)

    def test_template_field_help_mentions_default(self):
        field = self.env['project.project']._fields['mo_done_mail_template_id']
        self.assertIn('default', field.help)

    def test_create_schedules_no_check(self):
        self._run_checks()
        self._make_mos(2)
        self.assertNotIn('serichai_project_mo.projects_to_check', self.env.cr.precommit.data)

    def test_one_check_per_project_per_transaction(self):
        mos = self._make_mos(3)
        for mo in mos:
            mo.action_confirm()
            mo.qty_producing = mo.product_qty
        self._run_checks()
        with patch.object(self.registry['project.project'], '_check_all_mos_done', autospec=True) as check:
            mos.button_mark_done()
            mos[0].project_id = self.env['project.project']
            self._run_checks()
        self.assertEqual(check.call_count, 1)
        self.assertEqual(check.call_args.args[0], self.project)

    def test_state_change_by_compute_triggers_check(self):
        """R4: a state that becomes cancel only through its compute still runs the check."""
        done, open_mo = self._make_mos(2)
        self._finish(done)
        open_mo.action_confirm()
        before = self._mails()
        self.assertTrue(open_mo.move_finished_ids)
        open_mo.move_finished_ids.write({'state': 'cancel'})  # no write() on the MO itself
        self.assertEqual(self._mails(), before + 1)
        self.assertEqual(open_mo.state, 'cancel')

    def test_move_to_other_project_checks_old_project(self):
        done, open_mo = self._make_mos(2)
        self._finish(done)
        elsewhere = self.env['project.project'].create({'name': 'Elsewhere', 'user_id': self.project_user.id})
        before, elsewhere_before = self._mails(), self._mails(elsewhere)
        open_mo.project_id = elsewhere
        self.assertEqual(self._mails(), before + 1)
        self.assertEqual(self._mails(elsewhere), elsewhere_before)

    def test_project_changed_by_bom_compute_resets_flag_and_checks(self):
        """Review #3: project_id moved through the BoM compute is handled like a write."""
        other = self.env['project.project'].create({'name': 'BoM Project', 'user_id': self.project_user.id})
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.products[0].product_tmpl_id.id, 'product_qty': 1.0, 'type': 'normal',
            'project_id': other.id,
        })
        done, open_mo = self._make_mos(2)
        self._finish(done)
        other.mo_done_mail_sent = True
        before, other_before = self._mails(), self._mails(other)
        open_mo.bom_id = bom  # the BoM compute moves the MO to the BoM's project
        self._run_checks()
        self.assertEqual(open_mo.project_id, other)
        self.assertFalse(other.mo_done_mail_sent, 'an open MO joined: new batch')
        self.assertEqual(self._mails(), before + 1, 'the old project is now complete')
        self.assertEqual(self._mails(other), other_before)

    def test_mo_created_directly_done_triggers_check(self):
        """Review #3: an MO created already done can complete the project."""
        done = self._make_mos(1)
        self._finish(done)
        self.project.mo_done_mail_sent = False
        before = self._mails()
        self.env['mrp.production'].create({
            'product_id': self.products[1].id, 'product_uom_id': self.products[1].uom_id.id, 'product_qty': 1.0,
            'project_id': self.project.id, 'state': 'done'})
        self.assertEqual(self._mails(), before + 1)

    def test_mo_created_open_resets_flag_and_done_one_does_not(self):
        done = self._make_mos(1)
        self._finish(done)
        self.assertTrue(self.project.mo_done_mail_sent)
        self.env['mrp.production'].create({
            'product_id': self.products[1].id, 'product_uom_id': self.products[1].uom_id.id, 'product_qty': 1.0,
            'project_id': self.project.id, 'state': 'cancel'})
        self.assertTrue(self.project.mo_done_mail_sent)
        self._make_mos(1)
        self.assertFalse(self.project.mo_done_mail_sent)

    def test_state_changes_go_through_the_single_hook(self):
        """Review #5: write() and the recompute flush both end in the one hook."""
        mos = self._make_mos(2)
        before = self._mails()
        self._finish(mos[0])
        mos[1].action_confirm()
        mos[1].qty_producing = mos[1].product_qty
        with patch.object(self.registry['mrp.production'], '_on_tracked_fields_changed',
                          autospec=True, side_effect=self.registry['mrp.production']._on_tracked_fields_changed) as hook:
            mos[1].button_mark_done()
            self._run_checks()
        self.assertTrue(hook.called)
        self.assertEqual(self._mails(), before + 1)

    # ---- T047-T049

    def test_mark_completed_projects_as_notified(self):
        Project, Production = self.env['project.project'], self.env['mrp.production']
        new = lambda name: Project.create({'name': name, 'user_id': self.manager.id})  # noqa: E731
        done_only, done_cancelled, open_one, cancelled_only, no_mo, archived = (
            new(name) for name in ('Done', 'Done+cancel', 'Open', 'Cancelled', 'None', 'Archived'))
        archived.active = False

        def mo(project, state):
            return Production.create({
                'product_id': self.products[0].id, 'product_uom_id': self.products[0].uom_id.id,
                'product_qty': 1.0, 'project_id': project.id, 'state': state})
        mo(done_only, 'done')
        mo(done_cancelled, 'done')
        mo(done_cancelled, 'cancel')
        mo(open_one, 'done')
        mo(open_one, 'draft')
        mo(cancelled_only, 'cancel')
        mo(archived, 'done')
        projects = done_only | done_cancelled | open_one | cancelled_only | no_mo | archived
        projects.write({'mo_done_mail_sent': False})
        for _i in range(2):  # idempotent
            Project._mark_completed_projects_as_notified()
            self.assertEqual(
                {p.name: p.mo_done_mail_sent for p in projects.with_context(active_test=False)},
                {'Done': True, 'Done+cancel': True, 'Open': False, 'Cancelled': False,
                 'None': False, 'Archived': True})
        before = self._mails(done_only)
        Project._check_all_mos_done()
        self.assertEqual(self._mails(done_only), before)

    def test_upgrade_migration(self):
        path = Path(__file__).resolve().parents[1] / 'migrations' / '19.0.1.1.1' / 'post-migration.py'
        spec = importlib.util.spec_from_file_location('serichai_project_mo_post_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        template = self.env.ref('serichai_project_mo.mail_template_all_mos_done')
        Project, Production = self.env['project.project'], self.env['mrp.production']
        complete = Project.create({'name': 'Complete', 'user_id': self.manager.id})
        open_one = Project.create({'name': 'Open', 'user_id': self.manager.id})
        for project, state in ((complete, 'done'), (open_one, 'draft')):
            Production.create({
                'product_id': self.products[0].id, 'product_uom_id': self.products[0].uom_id.id,
                'product_qty': 1.0, 'project_id': project.id, 'state': state})
        projects = complete | open_one
        projects.write({'mo_done_mail_template_id': False, 'mo_done_mail_sent': False})
        for _i in range(2):  # idempotent
            module.migrate(self.env.cr, '19.0.1.0.0')
            self.assertEqual(projects.mapped('mo_done_mail_template_id'), template)
            self.assertTrue(complete.mo_done_mail_sent)
            self.assertFalse(open_one.mo_done_mail_sent)
        before = self._mails(complete)
        Project._check_all_mos_done()
        self.assertEqual(self._mails(complete), before)

    def test_project_less_mo_does_not_touch_projects(self):
        Project = self.registry['project.project']
        with patch.object(Project, '_reset_mo_done_mail_sent', autospec=True) as reset, \
                patch.object(Project, '_schedule_all_mos_done_check', autospec=True) as schedule:
            mo = self.env['mrp.production'].create({'product_id': self.products[0].id})
            mo.action_confirm()
            mo.qty_producing = mo.product_qty
            mo.button_mark_done()
            self.assertEqual(mo.state, 'done')
        for call in reset.call_args_list + schedule.call_args_list:
            self.assertFalse(call.args[0], "a project-less MO must not reset or schedule any project")

    def test_mail_quantity_is_formatted(self):
        template = self.env.ref('serichai_project_mo.mail_template_all_mos_done')
        for qty in (1.0, 1234.5):
            self.env['mrp.production'].create({
                'product_id': self.products[0].id, 'product_uom_id': self.products[0].uom_id.id,
                'product_qty': qty, 'project_id': self.project.id})
        body = str(template._render_field('body_html', self.project.ids)[self.project.id])
        unit = self.products[0].uom_id.name
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        self.assertEqual(digits, 2)
        self.assertIn('>1.00 %s<' % unit, body)
        self.assertIn('>1,234.50 %s<' % unit, body)
