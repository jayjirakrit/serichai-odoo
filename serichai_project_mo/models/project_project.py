import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

DEFAULT_MAIL_TEMPLATE_XMLID = 'serichai_project_mo.mail_template_all_mos_done'
PENDING_CHECKS_KEY = 'serichai_project_mo.projects_to_check'


class ProjectProject(models.Model):
    _inherit = 'project.project'

    mo_done_mail_template_id = fields.Many2one(
        'mail.template', string="All MOs Done Email", domain="[('model', '=', 'project.project')]",
        default=lambda self: self.env.ref(DEFAULT_MAIL_TEMPLATE_XMLID, raise_if_not_found=False),
        ondelete='set null',
        help="Email sent to the project manager once all Manufacturing Orders of the project are done. "
             "If left empty, the default 'Project MO Complete Email Template' is used.")
    mo_done_mail_sent = fields.Boolean(copy=False, help="Technical: the current MO batch was already notified.")

    @api.model
    def _set_default_mo_done_mail_template(self):
        """Give existing projects the default template (called once, at install)."""
        template = self.env.ref(DEFAULT_MAIL_TEMPLATE_XMLID, raise_if_not_found=False)
        if template:
            self.with_context(active_test=False).search(
                [('mo_done_mail_template_id', '=', False)]).write({'mo_done_mail_template_id': template.id})

    @api.model
    def _mark_completed_projects_as_notified(self):
        """Flag projects that are already complete (called once, at install), so a later MO change
        does not send them an email. Idempotent."""
        # sudo: technical flag, same reason as _reset_mo_done_mail_sent
        Production = self.env['mrp.production'].sudo().with_context(active_test=False)
        project_ids = {project.id for [project] in Production._read_group(
            [('project_id', '!=', False), ('state', '!=', 'cancel')], groupby=['project_id'])}
        open_ids = {project.id for [project] in Production._read_group(
            [('project_id', '!=', False), ('state', 'not in', ('cancel', 'done'))], groupby=['project_id'])}
        self.sudo().with_context(active_test=False).browse(sorted(project_ids - open_ids)).filtered(
            lambda project: not project.mo_done_mail_sent).write({'mo_done_mail_sent': True})

    def _reset_mo_done_mail_sent(self):
        # sudo: project users cannot write the technical notified flag
        self.sudo().filtered('mo_done_mail_sent').write({'mo_done_mail_sent': False})

    def _schedule_all_mos_done_check(self):
        """Run `_check_all_mos_done` once per project at the end of the transaction.

        Many MO changes can hit the same project in one transaction (and the final MO state may only
        be known after the recomputes), so the check is deferred to the precommit hook and
        deduplicated. Computed stored fields are flushed before the pending set is read, so a
        state changed only by a compute is scheduled too.
        """
        project_ids = [pid for pid in self.ids if isinstance(pid, int)]
        if not project_ids:
            return
        precommit = self.env.cr.precommit
        pending = precommit.data.get(PENDING_CHECKS_KEY)
        if pending is None:
            pending = precommit.data[PENDING_CHECKS_KEY] = set()
            Project = self.env['project.project']
            precommit.add(lambda: Project._run_scheduled_all_mos_done_check())
        pending.update(project_ids)

    @api.model
    def _run_scheduled_all_mos_done_check(self):
        self.env.flush_all()  # may schedule projects whose MO state/project_id was only recomputed
        project_ids = self.env.cr.precommit.data.pop(PENDING_CHECKS_KEY, ())
        self.browse(sorted(project_ids)).exists()._check_all_mos_done()

    def _check_all_mos_done(self):
        """Email the project manager once every non-cancelled MO of the project is done."""
        # sudo: the outcome must not depend on the acting user's rights (FR-020)
        projects = self.sudo().filtered(lambda p: p.id and not p.mo_done_mail_sent)
        if not projects:
            return
        locked = projects.try_lock_for_update(allow_referencing=True)
        if locked != projects:
            # Another transaction holds a project row (probably completing a sibling MO). Never raise
            # here: the email must not veto the user's MO change. The locked projects are skipped; the
            # other transaction's own check sees the final state once it commits.
            _logger.info("Projects %s are locked by another transaction; skipping their all-MOs-done check.",
                         (projects - locked).ids)
        for project in locked:
            project.invalidate_recordset(['mo_done_mail_sent'])
            if project.mo_done_mail_sent or not project.user_id.partner_id:
                continue  # no manager: do NOT set the flag (FR-016)
            if project._all_mos_done():
                project._send_mo_done_mail()

    def _all_mos_done(self):
        """True if the project has MOs and every non-cancelled one is done."""
        self.ensure_one()
        Production = self.env['mrp.production'].sudo()  # sudo: same reason as in _check_all_mos_done
        domain = [('project_id', '=', self.id), ('state', '!=', 'cancel')]
        return bool(Production.search_count(domain)) and not Production.search_count(domain + [('state', '!=', 'done')])

    def _send_mo_done_mail(self):
        """Queue the notification and flag the project; without any usable template, warn and skip."""
        self.ensure_one()
        template = self.mo_done_mail_template_id or self.env.ref(DEFAULT_MAIL_TEMPLATE_XMLID, raise_if_not_found=False)
        if not template:
            _logger.warning(
                "Project %s (id %s): all MOs are done but no email template is set and the default "
                "template %s is missing; no email sent.", self.name, self.id, DEFAULT_MAIL_TEMPLATE_XMLID)
            return
        # sudo (via the caller's projects): the acting user may lack mail rights; mail is only queued
        template.sudo().send_mail(self.id, force_send=False)
        self.mo_done_mail_sent = True
