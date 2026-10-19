# Implementation Plan: Project Configuration - High-Value-First Task Sorting

**Branch**: `010-project-configuration` | **Date**: 2026-10-19 (Gate 2, round 5) | **Spec**: [spec.md](./spec.md)

**Input**: `specs/010-project-configuration/spec.md`; findings in [research.md](./research.md).

## Summary

New addon `serichai_project_configuration`, which depends on `project` only.
`serichai_project_access` (spec 009) is not modified.

- **`is_high_value`** is a stored flag, computed as superuser. It comes from the task property
  labelled "มูลค่าโครงการ" in the task's project (label match, fail-safe parsing) and a threshold in
  `ir.config_parameter` (0 is allowed). It is recomputed when the task's properties or project
  change. After a threshold or definition change, an admin clicks Recalculate; a Settings hint says so.
- **`project_value`** is a non-stored "Project Value" column, computed with the current user's
  rights from the user's own `read(['task_properties'])`. A user from whom a module (e.g. 009) hides
  the property, or who cannot read the task, gets 0 and no error.
- **Views**: the internal task list base and kanban get
  `default_order="priority desc, is_high_value desc, state, date_deadline asc, id desc"`, the column and a
  "High Value" filter, shown to everyone. The model `_order` is unchanged.
- **Install**: the column is created first, then filled in batches.

See [design.md](./design.md).

## Technical Context

**Language/Version**: Python 3.12, Odoo 19.0 (research V1). No JavaScript.

**Primary Dependencies**: Odoo `project` only (research D2).

**Storage**: PostgreSQL. One new column `project_task.is_high_value bool` and one
`ir.config_parameter` key. `project_value` is not stored. No new model or table.

**Testing**: `TransactionCase` in `serichai_project_configuration/tests/test_budget_sort.py`. The
"cannot see the property" case is simulated by patching `project.task.read`, so no 009 is needed.
Use a dedicated test DB (quickstart.md).

**Target Platform**: Odoo 19 on Linux, standard backend web client.

**Project Type**: Odoo addon, area `odoo` (fullstack, backend-only change here).

**Performance Goals**: The sort is a plain SQL `ORDER BY` on stored columns. One task is recomputed
when it is written. All tasks are recomputed in batches of 1000, only on Recalculate. The column
costs one `read()` per batch of displayed rows.

**Constraints**:
- No edits to `odoo/` or `muk_web_theme/`.
- Portal, reports, exports, To-do and other task screens keep their order (FR-010).
- No evaluation error ever reaches the user (FR-007).
- No dependency on, or reference to, any other Serichai module (FR-001).

**Scale/Scope**: `serichai-db` today has 5 projects and 11 tasks; hundreds to low thousands expected.

## Constitution Check

| Principle | Status | Note |
|---|---|---|
| I. Extend, Never Fork | Pass | `_inherit` on `project.task` / `res.config.settings`; extension views only; 009 untouched. |
| II. Odoo conventions | Pass | Names follow Technology Standards; inherited views keep the original XML id with `.inherit.<details>` names. |
| III. Security by default | Pass | No new model, so no new ACL file. Threshold and recalculation are limited to `base.group_system` (ACL plus an explicit check). `project_value` is computed with the user's own rights through `read()`, so it shows no more than the user can read; `AccessError` gives 0. `is_high_value` (sudo) is readable by all (accepted). `sudo()` is used only for the `ir.config_parameter` read/write, the stored flag and the batch recalculation, each commented. The DDL in `pre_init_hook` uses `tools.sql.create_column` (fixed identifiers, no user input). |
| IV. Test what you change | Pass (planned) | design.md "Specs must assert", including the user who cannot read the property. |
| V. Spec first | Pass | Requirements map to key files in design.md. |

Technology Standards notes:
- No `security/` directory: the module adds no model, group or rule.
- The user runs the quality gate (`-u serichai_project_configuration` on `serichai-db`) after
  deployment (quickstart.md). Development tests use a throwaway DB.

## Contracts

None. Single area `odoo`, `requireContracts: false`. The module has no interface with any other
Serichai module: 009 is neither a dependency nor a dependent, and none of its code changes.

## Project Structure

### Documentation (this feature)

```text
specs/010-project-configuration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── design.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
serichai-odoo/serichai_project_configuration/      # NEW, depends: project
├── __init__.py                       # models; pre_init_hook, post_init_hook from hooks
├── __manifest__.py
├── hooks.py                          # create column; batched recalculation
├── models/
│   ├── __init__.py
│   ├── project_task.py               # constants, parsing, flag, per-user amount, recalculation
│   └── res_config_settings.py        # threshold (own get/set_values), recalc action
├── views/
│   ├── project_task_views.xml        # list/kanban default_order, column, filter
│   └── res_config_settings_views.xml
└── tests/
    ├── __init__.py
    └── test_budget_sort.py
```

**Structure Decision**: one new addon under `serichai-odoo/`, already on the `run_odoo.sh` addons
path. No other module changes.

## Complexity Tracking

No Constitution Check violations. Justified complexity (research):
- Column creation in `pre_init_hook`, for a batched install (V7).
- Custom `get_values`/`set_values` for the threshold, so that 0 can be stored (V7).
- `project_value` read through `read()` rather than field access, so modules that filter properties
  are honoured (V5).

## Post-merge follow-up

- Amend the constitution "Addons" list (`/speckit-constitution`, PATCH) and `CLAUDE.md` to name
  `serichai_project_configuration`.
