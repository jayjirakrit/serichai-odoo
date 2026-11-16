# Data Model: Create MOs from a Task

## project.task (inherit, `serichai_project_mo`)

| Field | Type | Notes |
|-------|------|-------|
| `finish_goods_ids` | Many2many `product.product` | table `project_task_finish_goods_rel`, cols `project_task_id`, `product_id`; domain `[('type','=','consu')]`; copy=False; one-sided (no inverse). |
| `mrp_production_ids`, `mrp_production_count` | existing | M2M `project_task_mrp_production_rel`, unchanged. |

Methods: `action_open_create_mo_wizard`, `action_view_mrp_productions` (added), `_check_can_create_mos`, `_create_mos_from_finish_goods(user)`.

## project.project (new file `models/project_project.py`)

| Field | Type | Notes |
|-------|------|-------|
| `mo_done_mail_template_id` | Many2one `mail.template` | domain `[('model','=','project.project')]`; default = shipped template; ondelete `set null` (fallback to default at send; if that is missing too, a warning is logged and the flag stays unset). Existing projects get the template at install through `_set_default_mo_done_mail_template` (model-level `<function>` in the noupdate data file). |
| `mo_done_mail_sent` | Boolean | technical, default False, copy=False, not shown. "Current batch already notified". |

Methods: `_schedule_all_mos_done_check` (queues one check per project per transaction on `cr.precommit`), `_run_scheduled_all_mos_done_check`, `_check_all_mos_done` (lock + guards), `_all_mos_done`, `_send_mo_done_mail`, `_reset_mo_done_mail_sent`, `_set_default_mo_done_mail_template`.

Shipped template `mail_template_all_mos_done`: name "Project MO Complete Email Template", `use_default_to` False, `partner_to` = project manager partner, HTML body with project, manager, count and table of non-cancelled MOs (name, product, quantity) and a "View Project in Odoo" link; `noupdate=1`.

## mrp.production (inherit)

No new field. Reused: `project_id` (project_mrp, stored), `project_task_ids` (existing M2M), `user_id`, `origin`, `state`.
Overrides: `_compute_state`, `_compute_project_id` (compare before/after), `create` (flag reset only), `write`, `unlink`; helpers `_snapshot`, `_on_state_changed`, `_on_project_changed`.

## project.task.create.mo (TransientModel, `wizard/`)

| Field | Type | Notes |
|-------|------|-------|
| `task_id` | Many2one `project.task` | required, readonly, ondelete cascade |
| `user_id` | Many2one `res.users` "Assignee" | required; domain = MRP users; default per D9 |
| `warning` | Text, computed | names of finish goods without BoM; empty = hidden |

Methods: `action_confirm`, `_notification(type, message)` (toast + close; used for "nothing new" and when the user cannot read `mrp.production`).

## State / rules

- Coverage(task, product) = exists MO in `task.mrp_production_ids`, `product_id = product`, `state != 'cancel'`.
- Notify(project) = non-cancelled MOs exist AND none is non-done AND `mo_done_mail_sent` False AND `user_id.partner_id` set.
- `mo_done_mail_sent`: set True only after a send is queued; reset False when a new non-cancelled, non-done MO is created for the project or an open MO genuinely moves into it (via write or the BoM-driven project compute).
- Check triggers (deferred, once per project per transaction): MO `state` becomes done/cancel (write and `_compute_state`), MO unlink, MO project change (old project always; new project only if the moved MO is done). `create` runs no check.

## Security data

- `serichai_project_mo/security/ir.model.access.csv`: wizard, `project.group_project_user`, 1,1,1,1. The Create MO button also has `groups="project.group_project_user"` (UI only).
- `i18n/th.po` / `.pot`: translations of labels; no schema impact.
- No new `ir.rule`; no new group.
