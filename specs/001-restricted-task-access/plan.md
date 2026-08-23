# Implementation Plan: Restricted "All Tasks" Access (serichai_project_security)

**Branch**: `001-restricted-task-access` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-restricted-task-access/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add a new custom Odoo addon, `serichai_project_security`, that introduces one restricted security
role granting a filtered, list-only, read-only view of `project.task` (scoped to the
"วางแผนการผลิต" stage), with server-side enforcement (not just UI hiding) against opening task
forms, plus menu-level hiding of the Project app's Projects/Reporting/Configuration entries and the
standard unrestricted "All Tasks" entry — all strictly additive so no existing group's access
changes. Technical approach follows standard Odoo security primitives (`res.groups`,
`ir.model.access.csv`, `ir.rule`, inherited views/actions, `ir.ui.menu` overrides, a `get_view()`
override) verified directly against this repository's vendored Odoo 19.0 source rather than the
Odoo-18-era source document the feature was originally scoped from. Hiding the Dashboards app icon
is explicitly out of scope for this module per user decision (see `research.md` §6) — Odoo 19's
Dashboards app has no group gating it, and the safe alternatives all still carry either
implementation cost or cross-department regression risk that the user chose to defer.

## Technical Context

**Language/Version**: Python 3.12 (this repo's `.venv`), Odoo 19.0 addon framework (XML data +
Python ORM models), no JS/OWL changes required.

**Primary Dependencies**: Odoo core `project` addon only (`depends: ["project"]`). No third-party
Python packages beyond what Odoo core already provides.

**Storage**: PostgreSQL via the Odoo ORM — no new tables; the module only adds `res.groups`,
`ir.model.access`, `ir.rule`, `ir.ui.view`, `ir.actions.act_window`, and `ir.ui.menu` records, and
extends `project.task`'s Python behavior via inheritance (no new fields/columns).

**Testing**: Odoo's built-in test framework (`odoo.tests.common.TransactionCase`), run via
`--test-enable --stop-after-init -u serichai_project_security` per this repo's documented workflow
(`CLAUDE.md`). No dedicated test suite exists yet in either sibling custom addon — this module
establishes the pattern.

**Target Platform**: Existing Odoo 19.0 backend web client, Linux server (this repo's dev
environment), single-company assumed unless the live database proves otherwise during
implementation verification.

**Project Type**: Single Odoo addon module (`serichai-odoo/serichai_project_security/`), following
the layout of the sibling addon `serichai_project_mo`.

**Performance Goals**: None beyond standard Odoo list-view rendering; no bulk-data or high-frequency
operations introduced by this feature.

**Constraints**: Must be purely additive — zero behavior change for any existing group or app
(FR-009, SC-005); form-access blocking must hold even via direct URL, not just UI hiding (FR-005,
FR-010); menu-hiding changes to shared records (`project.menu_projects`,
`project.menu_project_report`) must reproduce the live database's actual current `group_ids` value
before narrowing it — verify against the running `serichai-db`, not just static source, before
finalizing `views/project_menus.xml` (carried from research.md §2).

**Scale/Scope**: One new `res.groups` record, one `ir.rule`, two `ir.model.access.csv` rows, one
inherited view, one new action, one new menu item, five existing-menu `group_ids` edits, one Python
model extension (`get_view` override). No new persistent data model (see `data-model.md`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (all placeholder tokens, no
ratified principles) — this project has not adopted project-specific constitutional gates. In its
absence, this plan is governed by the constraints already documented in the repository's
`CLAUDE.md` (treat `odoo/` as vendored, don't modify third-party/theme addons, follow existing
custom-addon layout conventions) and by general Odoo addon best practices (additive security,
`ir.model.access.csv` + `ir.rule` for data access, standard manifest/module structure). No gate
violations to justify; **Complexity Tracking** section below is empty accordingly.

**Post-design re-check** (after Phase 1): Still no ratified constitution to violate. The one
deliberate scope reduction in this plan (Dashboards app hiding deferred, research.md §6) was an
explicit user decision, not a gate violation, and is documented in `spec.md` Assumptions and
`contracts/module-interface.md`'s "Explicitly out of scope" section rather than in Complexity
Tracking (it removes scope; it doesn't add unjustified complexity).

## Project Structure

### Documentation (this feature)

```text
specs/001-restricted-task-access/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── module-interface.md   # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
serichai-odoo/serichai_project_security/    # new addon, sibling to serichai_project_mo
├── __init__.py                             # from . import models
├── __manifest__.py                         # depends: ["project"]; data: security/*, views/*
├── security/
│   ├── security_groups.xml                 # group_project_task_list_only
│   ├── ir.model.access.csv                 # project.task + project.project, read-only
│   └── ir_rule.xml                         # rule_task_stage_restricted
├── models/
│   ├── __init__.py                         # from . import project_task
│   └── project_task.py                     # get_view() override -> AccessError on form
└── views/
    ├── project_task_views.xml              # view_task_list_restricted, action_task_all_restricted
    └── project_menus.xml                   # menu group_ids edits + menu_task_all_restricted
```

No `tests/` directory is scaffolded ahead of time — the first test module for this addon will be
created under a standard Odoo `tests/` package (`tests/__init__.py`,
`tests/test_task_access_restriction.py`) during `/speckit-tasks`/implementation, following
`odoo.tests.common.TransactionCase` conventions, matching this repo's stated (but not yet
exercised) `--test-enable` workflow.

**Structure Decision**: Single Odoo addon module, placed inside the existing `serichai-odoo` git
repository (not the untracked top-level `serichai_inventory/`, and not a new top-level directory) —
matching the sibling addon `serichai_project_mo`'s location and already covered by `run_odoo.sh`'s
addons path (`$BASE_PATH/serichai-odoo`), so no changes to the run script are needed. This is an
Odoo addon, not a web/mobile app — the standard Odoo module layout (`__manifest__.py`, `security/`,
`models/`, `views/`) is the correct structure, not any of the generic src/tests options.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations — no ratified constitution exists to violate, and no complexity beyond a standard
single Odoo addon is introduced by this plan.*
