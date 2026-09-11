# Implementation Plan: Contract MO Print Report for Project Task

**Branch**: `005-contract-mo-report` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-contract-mo-report/spec.md`

## Summary

Add a new "Contract MO" QWeb PDF report bound to `project.task` inside the existing `serichai_project_mo` addon, reachable from the task form's standard Print menu exactly like every other Odoo document report (`ir.actions.report` + `binding_model_id`/`binding_type: report` — no custom button, no view changes). The template reproduces the company's paper "ใบสั่งผลิตตัวอย่าง" order form using the same declarative pattern (`web.html_container` / `web.internal_layout`, Bootstrap table classes) that core's own MO "Production Order" report and `hr_timesheet`'s task-bound Timesheets report already use.

**Revised 2026-09-11** against the annotated mockup `project_mo_report-sample.png` (see spec.md's 2026-09-11 clarification session and research.md Decision 7 — this supersedes the original 2026-09-10 header design): the header is now `o.name` in a bordered box followed by the task's `task_properties` rendered as label/value pairs (one small presentation-only model method, `project.task._get_report_task_properties()`, added to read them through `read()` so the ORM's own existence/visibility filtering applies — no new persisted field), then a boxed "Manufacturing Order" heading above the item table, whose columns are now Manufacturing Order (`mo.name`) / Product / Quantity — folding the old separate announcement-number field into the table itself. The item table's blank-row padding, the remarks section (`o.description`), and the two signature blocks are unchanged from the original design. The module's existing `mrp_production_ids` many2many and `task_properties`/`task_properties_definition` (Odoo core `project`) are the only data sources; no new models or fields.

## Technical Context

**Language/Version**: Python 3.12 (repo `.venv`), Odoo 19.0 ORM + QWeb

**Primary Dependencies**: Odoo `project` (`project.task`), Odoo `mrp` (`mrp.production`) — both already depended on by `serichai_project_mo`; Odoo `web` module's `html_container`/`internal_layout` report templates (core, always present); no new third-party Python packages

**Storage**: None new — reads existing `project.task` fields (`name`, `task_properties` + its project's `task_properties_definition`, `description`, `user_ids`) and existing `mrp_production_ids` (via the module's own `project_task_mrp_production_rel` relation) plus each linked `mrp.production`'s `name`, `product_id`, `product_qty`, `product_uom_id`

**Testing**: `odoo.tests.common.TransactionCase` / `--test-enable --stop-after-init -u serichai_project_mo`, asserting the report renders (`env['ir.actions.report']._render_qweb_pdf` or `_render_qweb_html`) without error across the data-completeness edge cases in spec.md (no MOs, no project/no properties, no description, MO count exceeding the padded grid, a property whose definition was later removed)

**Target Platform**: Server-side Odoo addon (Linux) plus backend web client Print menu; PDF rendering via Odoo's existing wkhtmltopdf pipeline (no new rendering dependency)

**Project Type**: Odoo addon extension (existing addon `serichai-odoo/serichai_project_mo/`; adds a `report/` subpackage — no new addon)

**Performance Goals**: No dedicated throughput target; one report render per print action, item table sized to the task's own `mrp_production_ids` (expected to stay in the tens), negligible compute

**Constraints**: Must not modify vendored `odoo/` (report lives entirely in `serichai_project_mo`); must not change the existing `views/project_task_views.xml` MO smart button/embedded list tab or the `project_task_mrp_production_rel` relation (spec Assumptions); must not add a custom print button — discovery relies solely on `binding_model_id`/`binding_type: report` per spec FR-002

**Scale/Scope**: Single Odoo instance (`serichai-db`); scoped to `serichai_project_mo`'s new `report/` files and one manifest edit — no changes to `serichai_inventory`, `muk_web_theme`, or the other custom addons

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (`[PROJECT_NAME] Constitution` with bracketed placeholders) — no project-specific principles or gates have been ratified. This gate is **N/A / pass by default**. General repository conventions from `CLAUDE.md` (avoid modifying vendored `odoo/`, follow existing addon layout, avoid unrequested scope, keep both sides of the `project.task`/`mrp.production` relation in sync) are reflected in the Constraints above.

**Post-Phase-1 re-check**: No change — `research.md`, `data-model.md`, and `contracts/` introduce no new third-party dependencies, no core-file modifications, no new persisted models/fields, and stay entirely within `serichai_project_mo`. Gate remains N/A / pass.

## Project Structure

### Documentation (this feature)

```text
specs/005-contract-mo-report/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
serichai-odoo/serichai_project_mo/            # EXISTING addon — this feature only adds files here
├── __manifest__.py                                 # EDIT: add report/ files to `data`
├── models/
│   ├── project_task.py                             # EDIT (2026-09-11): add _get_report_task_properties()/_format_report_property_value() (mrp_production_ids relation unchanged)
│   └── mrp_production.py                           # unchanged
├── views/                                          # unchanged (smart button + embedded MO list tab)
│   ├── project_task_views.xml
│   └── mrp_production_views.xml
└── report/                                         # NEW subpackage
    ├── project_task_report_views.xml               # NEW: ir.actions.report record (action_report_contract_mo), bound to project.task
    └── project_task_report_templates.xml           # NEW: QWeb template (report_contract_mo) — header fields, item table, remarks, signatures
```

**Structure Decision**: Extend the existing `serichai_project_mo` addon in place with a new `report/` subdirectory — the standard location Odoo core addons (e.g. `mrp/report/`, `hr_timesheet/report/`) use for `ir.actions.report` + QWeb template pairs. No new addon, no new top-level directory, no `run_odoo.sh` change: `serichai_project_mo` is already on the addons path.

## Complexity Tracking

*No constitution violations — table not applicable.*
