# Implementation Plan: Multi-Rate Overtime Calculation for Attendance (serichai_hr_attendance)

**Branch**: `004-attendance-ot-multiplier` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-attendance-ot-multiplier/spec.md`

## Summary

Every `hr.attendance` record gets three new stored hour buckets — Normal, OT 1.5x, OT 2x — computed automatically from the employee's wage type (Daily/Monthly Paid, new `hr.employee.wage_type` field) and the record's day type (weekday vs. Sunday/Holiday), against a configurable, UI-editable ruleset (new `hr.attendance.ot.rule` model, seeded with the 8 default rules). This ships as a new addon, `serichai_hr_attendance`, that only extends `hr_attendance`/`hr.employee` via inheritance — it does not touch vendored `odoo/` core files and does not replace or disable core's own overtime-approval system (`overtime_hours`/`validated_overtime_hours`/`hr.attendance.overtime.rule`), which keeps operating unchanged in parallel. Research below found that this Odoo 19 vendor tree already ships a materially different, more general overtime-ruleset engine than the feature brief assumed, and represents "public holiday" via calendar-wide `resource.calendar.leaves` rather than an `hr.holidays.public.line` model that doesn't exist in this codebase — both are accounted for in the design.

## Technical Context

**Language/Version**: Python 3.12 (repo `.venv`), Odoo 19.0 ORM

**Primary Dependencies**: Odoo `hr_attendance` (extends `hr.attendance`, `hr.employee`), Odoo `resource` (via `hr` → `resource`) for `resource.calendar` / `resource.calendar.leaves` (public-holiday detection); no new third-party Python packages

**Storage**: PostgreSQL via Odoo ORM; one new model (`hr.attendance.ot.rule`, configuration data) plus 4 new stored fields (`hr.employee.wage_type`; `hr.attendance.day_type`, `normal_hours`, `overtime_150_hours`, `overtime_200_hours`)

**Testing**: `odoo.tests.common.TransactionCase`, run via `--test-enable --stop-after-init -u serichai_hr_attendance`, following the pattern already established in `serichai_project_security/tests/test_access_restriction.py`

**Target Platform**: Server-side Odoo addon (Linux) plus backend web client (Attendance list/pivot views); kiosk-created attendance records flow through the same `hr.attendance` compute with no separate handling needed

**Project Type**: Odoo addon (single addon, own top-level directory alongside the repo's other custom addons; extends `hr_attendance` and `hr.employee` via `_inherit`)

**Performance Goals**: No dedicated throughput targets; the rule set is small (8 default rows, expected to stay in the tens even with customization) so per-record rule matching is O(rules) and negligible; the one-time historical backfill batches records (chunks of 1000) rather than recomputing the whole table in a single transaction

**Constraints**: Must not modify vendored `odoo/` (all changes via `_inherit`, no edits to `hr_attendance` core files); must not disable, hide, or reinterpret core's existing `overtime_hours` / `validated_overtime_hours` fields or the `hr.attendance.overtime.rule`/`hr.attendance.overtime.ruleset` engine — this feature's three buckets are additive and independently computed, not a replacement

**Scale/Scope**: Single Odoo instance (`serichai-db`); scoped to `hr.attendance` + `hr.employee` + one new configuration model, no changes to other custom addons in the repo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (`[PROJECT_NAME] Constitution` with bracketed placeholders) — no project-specific principles or gates have been ratified. This gate is **N/A / pass by default**. General repository conventions from `CLAUDE.md` (avoid modifying vendored `odoo/`, follow existing addon layout, avoid unrequested scope) are reflected in the Constraints above and the design below.

**Post-Phase-1 re-check**: No change — `research.md`, `data-model.md`, and `contracts/` introduce no new third-party dependencies, no core-file modifications, and stay within the scoped addon. Gate remains N/A / pass.

## Project Structure

### Documentation (this feature)

```text
specs/004-attendance-ot-multiplier/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
serichai-odoo/serichai_hr_attendance/        # NEW addon, own top-level directory (sibling of serichai_project_mo, serichai_project_security, serichai_inventory_barcode)
├── __init__.py                                    # imports models, defines post_init_hook re-export
├── __manifest__.py                                # depends: ['hr_attendance']; post_init_hook: backfill historical hr.attendance rows
├── models/
│   ├── __init__.py
│   ├── hr_attendance_ot_rule.py                   # NEW model: hr.attendance.ot.rule (name, wage_type, day_type, sequence, time_from, time_to, pay_type, catch_outside, company_id, active)
│   ├── hr_employee.py                             # _inherit hr.employee: + wage_type Selection field
│   └── hr_attendance.py                           # _inherit hr.attendance: + day_type, normal_hours, overtime_150_hours, overtime_200_hours (stored, compute) and helpers _get_day_type(), _interval_overlap(), _hours_outside(), _compute_ot_hours()
├── views/
│   ├── hr_attendance_ot_rule_views.xml            # list + form views, Attendances (top-level, not nested in Configuration, since that submenu is Manager-only) > Overtime Rules menu item
│   ├── hr_attendance_views.xml                    # inherits hr_attendance.view_attendance_tree (new columns after `overtime_hours`), adds hr.attendance pivot view + action + "OT Analysis" menu item
│   └── hr_employee_views.xml                      # inherits employee form to expose wage_type (HR/Attendance-relevant tab)
├── security/
│   ├── ir.model.access.csv                        # hr.attendance.ot.rule: manager + officer both get full CRUD
│   └── hr_attendance_ot_rule_security.xml          # multi-company record rule on hr.attendance.ot.rule, mirroring hr_attendance's own company rule pattern
├── data/
│   └── hr_attendance_ot_rule_data.xml              # the 8 default rules from spec FR-004
├── tests/
│   ├── __init__.py
│   ├── test_ot_rule_engine.py                     # unit tests: _get_day_type, _interval_overlap, _hours_outside, rounding — the 10 scenarios from spec SC-003
│   ├── test_ot_backfill.py                         # post_init_hook backfills pre-existing hr.attendance rows
│   └── test_ot_export.py                           # new fields present/selectable in the export-wizard field list
└── static/description/
    └── icon.png                                    # standard Odoo addon icon (reuse repo convention/placeholder)
```

**Structure Decision**: A new, standalone addon at `serichai-odoo/serichai_hr_attendance/`, following the exact layout already used by `serichai_project_mo`/`serichai_project_security`/`serichai_inventory_barcode` (`models/`, `views/`, `security/`, `data/`, `tests/`). It depends only on `hr_attendance` (which already depends on `hr`/`resource`/`barcodes`/`base_geolocalize`) and adds nothing to the vendored `odoo/` tree. `run_odoo.sh` already passes the whole `serichai-odoo/` directory as one `--addons-path` entry (`ADDITIONAL_ADDONS="$BASE_PATH/muk_web_theme,$BASE_PATH/serichai-odoo"`), and Odoo auto-discovers every addon subdirectory under a path entry — so placing this addon directly under `serichai-odoo/`, the same way `serichai_project_mo`/`serichai_project_security`/`serichai_inventory_barcode` already are, makes it discoverable with **no `run_odoo.sh` change needed** (unlike `serichai_inventory`, which `CLAUDE.md` notes lives one level *above* `serichai-odoo/` and is therefore genuinely off the path).

## Complexity Tracking

*No constitution violations — table not applicable.*
