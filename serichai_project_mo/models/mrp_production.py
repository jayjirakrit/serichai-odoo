from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    project_task_ids = fields.Many2many(
        'project.task', 'project_task_mrp_production_rel', 'mrp_production_id', 'project_task_id',
        string='Project Tasks', help='Project tasks related to this manufacturing order.')

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        productions = super().create(vals_list)
        # a new MO is a change from "no state, no project"
        productions._on_tracked_fields_changed(dict.fromkeys(productions.ids, (False, None)))
        return productions

    def _write_multi(self, vals_list):
        """Single sink of every database write of state/project_id.

        write() ends here, and so does the flush of recomputed stored fields (state and project_id
        are computed), so this one hook covers both without copying core's compute dependencies.
        """
        if not any('state' in vals or 'project_id' in vals for vals in vals_list):
            return super()._write_multi(vals_list)
        old = self._snapshot()
        res = super()._write_multi(vals_list)
        self._on_tracked_fields_changed(old)
        return res

    def unlink(self):
        projects = self.project_id  # super() cancels the MOs first, which already schedules the check
        res = super().unlink()
        projects._schedule_all_mos_done_check()
        return res

    # ------------------------------------------------------------
    # EMAIL CHECK TRIGGERS
    # ------------------------------------------------------------
    # The "all MOs done" email check only matters when an MO becomes done or cancelled, leaves or
    # joins a project, or is created or deleted. Each trigger schedules one deferred check per project
    # (see project.project._schedule_all_mos_done_check).

    def _snapshot(self):
        """Return {id: (state, project id)} as stored in the database, before they are overwritten."""
        ids = [mo_id for mo_id in self.ids if isinstance(mo_id, int)]
        if not ids:
            return {}
        self.env.cr.execute("SELECT id, state, project_id FROM mrp_production WHERE id IN %s", [tuple(ids)])
        return {mo_id: (state, project_id) for mo_id, state, project_id in self.env.cr.fetchall()}

    def _on_tracked_fields_changed(self, old):
        """React to state/project_id changes, given the `_snapshot` taken before the change."""
        Project = self.env['project.project']
        to_reset = to_check = Project
        for mo in self.filtered(lambda mo: mo.id in old):
            old_state, old_project_id = old[mo.id]
            if (mo.project_id.id or None) != old_project_id:
                if mo.state != 'cancel':
                    to_reset |= mo.project_id  # an open MO joining a project starts a new batch there
                to_check |= Project.browse(old_project_id)  # the old project may now be complete
                if mo.state == 'done':
                    to_check |= mo.project_id
            if mo.state != old_state and mo.state in ('done', 'cancel'):
                to_check |= mo.project_id
        to_reset._reset_mo_done_mail_sent()
        to_check._schedule_all_mos_done_check()
