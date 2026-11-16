# Implementation Plan: Create Manufacturing Orders from a Project Task

**Branch**: `011-task-create-mo` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/011-task-create-mo/spec.md` (FR-009 and FR-018 intentionally unused; Buy Goods and `serichai_project_security` out of scope). Findings in [research.md](./research.md); code review aid in [design.md](./design.md).

## Summary

Extend `serichai_project_mo` with a **Finish Goods** field on `project.task`, a **Create MO** wizard
(`project.task.create.mo`) and a "all MOs done" email on `project.project`.

- Creation is one choke point, `project.task._create_mos_from_finish_goods(user)`. It checks
  `check_access('write')` on the task as the real user, locks the task row, skips products already
  covered by a non-cancelled linked MO, then creates the MOs under `sudo()` (no custom group has
  `mrp.production` create rights). `sudo()` keeps the real uid, so `create_uid` is the clicking user;
  `user_id` is the chosen assignee.
- `mrp.production` overrides (`_write_multi`, `create`, `unlink`) do not send anything themselves. `_write_multi`
  is the single sink of `write()` and of the flush of the computed stored `state`/`project_id`; with `create` it
  calls one helper, `_on_tracked_fields_changed`, which decides "became done/cancel" and "project changed" and calls
  `project.project._schedule_all_mos_done_check()`, which queues one `_check_all_mos_done()` per project per
  transaction through `cr.precommit` (an MO created already done is covered; a new open MO resets
  `mo_done_mail_sent`). A project row locked by another transaction never raises: its check is skipped (no recheck cron). The check
  (`_all_mos_done` + `_send_mo_done_mail`) queues the project's template to the project manager under `sudo`
  and sets the flag; no manager or no template means no send and no flag (missing template logs a warning).
- Access: the wizard ACL covers `project.group_project_user`; `check_access('write')` on the task gates every creation. The Create MO button is further limited to that group in the view (UI only).
  `serichai_project_security` is not modified and not depended upon.
- Core `project_mrp` already provides stored `mrp.production.project_id`; it is reused, not redefined.

## Technical Context

**Language/Version**: Python 3.12, Odoo 19.0. No JavaScript (XML view + button only).

**Primary Dependencies**: `project`, `mrp`, **`project_mrp`** (new, for `project_id`), **`mail`** (new, template). Translations: `i18n/th.po` + `.pot`.

**Storage**: PostgreSQL. New: M2M table `project_task_finish_goods_rel`; `project_project` columns
`mo_done_mail_template_id`, `mo_done_mail_sent`. See [data-model.md](./data-model.md).

**Testing**: Odoo `TransactionCase` (`@tagged('post_install', '-at_install')`), `consu` products as in
`tests/test_contract_mo_report.py`. Run with `--test-tags /serichai_project_mo`.

**Target Platform**: Odoo 19 backend web client (form view button, dialog).

**Project Type**: Odoo addon extension (single area `odoo`, fullstack).

**Performance Goals**: N is small (a task has a handful of products); one `create([...])` call, one
grouped state count per affected project.

**Constraints**: no edits to `odoo/`; relation tables identical from both M2M sides; email must not depend
on the triggering user's rights; no duplicate MOs under double-click or concurrent confirm.

**Scale/Scope**: 1 new model (wizard), 1 new model file (`project.project`), 3 inherited models, 1 mail
template (+ install-time default assignment), 1 ACL file, ~3 views, Thai translation files.

## Constitution Check

| Principle / standard | Result |
|----------------------|--------|
| I Extend, never fork | Pass: only `_inherit` and view `inherit_id`; core and MuK untouched. |
| II Odoo conventions | Pass: file names `wizard/project_task_create_mo.py`, `*_views.xml`, `ir.model.access.csv`, `data/project_project_data.xml`; method prefixes `action_`, `_check_`, `_compute_`. |
| III Security by default | Pass: wizard ACL for project users; server-side `check_access('write')` before any `sudo()`. Each `sudo()` carries a why-comment (MO create: no group has create; mail: sender rights irrelevant; flag write: project users cannot write it; BoM lookup: project users may lack `mrp.bom` read). No raw SQL: row locks use `lock_for_update()`. |
| IV Tests | Pass: positive and negative access tests planned (see design.md 4.7). |
| V Spec first | Pass: every key file maps to FRs in design.md section 4. |
| M2M both-sides rule | Pass: `finish_goods_ids` has one side only (no inverse field); `project_task_mrp_production_rel` untouched. |
| Gate | `... -u serichai_project_mo`. |

No violations; Complexity Tracking empty.

## Project Structure

### Documentation

```text
specs/011-task-create-mo/
├── spec.md  plan.md  research.md  data-model.md  quickstart.md  design.md
└── (no contracts/: single area, no inter-area interface; requireContracts=false)
```

### Source Code

```text
serichai-odoo/serichai_project_mo/
├── __manifest__.py                 # + depends project_mrp, mail; + data files (v1.1.1)
├── models/{__init__,project_task,mrp_production}.py   # edited
├── models/project_project.py       # new
├── wizard/{__init__,project_task_create_mo}.py, project_task_create_mo_views.xml   # new
├── views/{mrp_production_views,project_task_views,project_project_views}.xml   # edited / new
├── security/ir.model.access.csv    # new (project users)
├── data/project_project_data.xml   # new, noupdate=1: mail template + install-time default assignment
├── migrations/19.0.1.1.1/post-migration.py   # new: same two calls on `-u` (Odoo skips noupdate <function>)
├── i18n/{serichai_project_mo.pot,th.po}   # new: Thai labels (some strings still English)
└── tests/{__init__,test_create_mo_from_task}.py   # new; test_contract_mo_report.py already existed
```

Manifest `data` order: `security/ir.model.access.csv`, `data/project_project_data.xml`,
`views/mrp_production_views.xml`, `views/project_task_views.xml`, `views/project_project_views.xml`,
`wizard/project_task_create_mo_views.xml`, `report/project_task_report_views.xml`,
`report/project_task_report_templates.xml`.

**Structure Decision**: single addon extension; the addon is self-contained.

## API Contracts

Not applicable: one area, no cross-area interface. The only public surface is the button action
`project.task.action_open_create_mo_wizard` and wizard `action_confirm`, documented in design.md.

## Task notes for `/speckit-tasks`

- Last task: update CLAUDE.md `serichai_project_mo` section (Finish Goods, wizard, email, new depends) and the stale `action_view_mrp_productions` mention.
- Risks: see design.md section 5 (open questions were resolved at Gate 2, section 7).

## Complexity Tracking

None.
