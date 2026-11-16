# Research: Create MOs from a Task

All "NEEDS CLARIFICATION" resolved against the code in `odoo/addons/{mrp,project_mrp,project}` and the two custom addons.

## D1 Where the "done"/"cancelled" hooks go (revised after code review)
- **Decision**: `mrp.production` overrides `_write_multi` (the ORM's low-level sink: `write()` and the flush of dirty
  stored computed fields both call it, verified in Odoo 19 `models.py` `_flush`), plus `create` and `unlink`. When
  `state` or `project_id` is written, the DB values are read by one SQL before `super()` and compared after, by one
  helper `_on_tracked_fields_changed(old)` (also used by `create` with an "empty" old value, so an MO created directly
  in done state is handled). It calls `project.project._schedule_all_mos_done_check()`; nothing sends mail directly (D5/D6).
- **Why**: `state` and `project_id` are stored *computed* fields, so a change can arrive without any `write`
  (moves cancelled or done by another flow, BoM-driven project). Overriding `_compute_state` would need a copy of
  core's `@api.depends` (silent breakage when core changes); `_write_multi` has no such coupling and handles write and
  recompute in one place. The hook fires at flush time, not at assignment; every path flushes before commit.
  `unlink` schedules for the projects it captured before the records vanish.
- **Rejected**: hooking only `write`/`_action_cancel` (misses pure recomputes); overriding the computes (copied depends,
  double handling with `write`).
- **Residual**: none known; the check is idempotent.

## D2 Why `sudo()` keeps the clicking user
`sudo()` in Odoo 19 keeps `env.uid`, so `create_uid` and chatter author stay the real user; only access checks are skipped.
Ownership = creator is the user, responsible (`user_id`) = chosen assignee. No `with_user(SUPERUSER)`.

## D3 Access check before `sudo()`
`recordset.check_access('write')` (ACL + record rules). Project users: write follows their normal task rules.

## D4 ACL placement
Odoo 19 TransientModels still need `ir.model.access` rows (constitution III).
- **Chosen**: one ACL row in `serichai_project_mo/security/ir.model.access.csv` for `project.group_project_user`.
  `serichai_project_security` is not touched and gets no dependency on `serichai_project_mo` (decision at review).
- The Task List Viewer role gets no wizard ACL, so it cannot use the feature; out of scope.

## D5 Concurrency (FR-008)
Odoo runs REPEATABLE READ. Plain "search then create" duplicates under double-click. Plan:
1. `task.lock_for_update(allow_referencing=True)` (SKIP LOCKED then `LockError`, a `UserError`): a truly simultaneous second
   confirm gets "being processed, try again" instead of waiting.
2. A competitor whose snapshot predates the first commit would lock successfully yet not see the new MOs. So the creator
   **writes the task row** (`mrp_production_ids` link, which bumps `write_date`): the stale competitor's `FOR UPDATE` then
   raises a serialization failure and Odoo's RPC retry re-runs it on a fresh snapshot, where coverage is visible.
3. UI: Confirm button also guarded by the standard one-click `disable` behaviour of buttons.
**Email (revised)**: triggers do not check synchronously. `_schedule_all_mos_done_check` adds the project id to a set kept in
`cr.precommit.data` and registers one precommit callback per transaction, so many MO changes yield one check per project
and the check sees the final, flushed states. `_check_all_mos_done` then `try_lock_for_update`s the projects; if it cannot
lock one (another transaction is completing a sibling MO), it does not raise (an email must not roll back the user's
MO change, and cron/shell callers have no retry). It skips the locked projects (logged) and relies on the other transaction's own check; no recheck cron (decision: not needed for now), so a simultaneous finish of sibling MOs can rarely leave one project without its email until its next MO change. Rejected: waiting on the lock (the snapshot stays stale); a pending-ids field
(writing the locked row would block). After locking it re-reads
`mo_done_mail_sent`, checks `_all_mos_done()`, and `_send_mo_done_mail()` queues the mail and sets the flag.

## D6 Email timing and linking
Email timing: the mail is queued (`force_send=False`) inside the precommit callback, so it is written to `mail.mail` at flush/commit
of the user's action, never synchronously in the MO write. `create` runs no check (a new open MO cannot complete a project).

Linking:
Create with `project_id`, `user_id`, `origin`; link to the task by writing the task side (`Command.link`) after create
(needed by D5). `project_id` passed in create vals overrides the `bom_id.project_id` compute (readonly=False, stored).

## D7 Email
- Template model `project.project`, recipient via `partner_to = {{ object.user_id.partner_id.id }}`, `use_default_to` False.
- The shipped template is now "Project MO Complete Email Template" (hand-edited): rich HTML with project, manager, count and
  table of non-cancelled MOs (name, product, quantity) and a "View Project in Odoo" link. Existing projects receive it at
  install via the `_set_default_mo_done_mail_template` function in the noupdate data file.
- Send with `template.sudo().send_mail(project.id, force_send=False)` (queued): no SMTP inside the transaction, and the
  sender's rights are irrelevant (FR-020). Default template ref'd on the field as a default; if the field is empty, fall back
  to `env.ref('serichai_project_mo.mail_template_all_mos_done')`. If that is missing too, `_send_mo_done_mail` logs a warning and
  leaves the flag unset (re-evaluated on the next trigger).
- `noupdate="1"` so admins' edits survive upgrades.

## D8 Products
`finish_goods_ids` is `product.product` (variants), domain `[('type', '=', 'consu')]`; coverage compares `product.product`.
BoM lookup for the warning: `mrp.bom.sudo()._bom_find(products)` (a project user may lack read access to `mrp.bom`); only names leave.

## D9 Assignee
Wizard `user_id` domain mirrors `mrp.production.user_id` (members of `mrp.group_mrp_user`); default = current user only if
they are such a member. Not enforced server-side (same as core MO).

## D10 Smart button
`project_task.py` has no `action_view_mrp_productions` (CLAUDE.md mentions it; code does not) and the stat button has no
`type`/`name`. Added here (small, same area) so the task's MOs are reachable.

## D11 Translations and button group
`i18n/th.po` and `serichai_project_mo.pot` carry Thai labels for the new screens; about 29 of 51 entries (mostly error texts, the
template-related labels and report strings) are still untranslated and fall back to English. The Create MO button has
`groups="project.group_project_user"`: UI only, the server check of D3 is unchanged. The wizard returns a toast instead of the
MO list when the user cannot read `mrp.production`.
