# Tasks: Multi-Rate Overtime Calculation for Attendance (serichai_hr_attendance)

**Input**: Design documents from `/specs/004-attendance-ot-multiplier/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/compute-engine.md, quickstart.md

**Tests**: Included — the plan's Project Structure and the spec's Success Criteria (SC-003) call for a unit/integration test suite covering the compute engine, so test tasks are part of each relevant story.

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3) so each can be implemented and independently tested/demoed on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: US1 / US2 / US3, per spec.md's prioritized user stories
- All paths are relative to the repo root (`/home/odoo/serichai-odoo`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new addon's skeleton so later phases have somewhere to add code.

- [X] T001 Create the addon skeleton at `serichai-odoo/serichai_hr_attendance/`: empty `__init__.py`, `models/__init__.py`, `tests/__init__.py`, and empty `views/`, `security/`, `data/`, `static/description/` directories
- [X] T002 Write `serichai-odoo/serichai_hr_attendance/__manifest__.py` — `name`, `summary`, `depends: ['hr_attendance']`, `author: 'Serichai Group'`, `license: 'AGPL-3'`, `installable: True`, empty `data` list (populated by later tasks), `post_init_hook: 'post_init_hook'`
- [X] T003 [P] ~~Add a placeholder module icon~~ — **skipped**: none of this repo's other custom addons (`serichai_project_mo`, `serichai_project_security`, `serichai_inventory_barcode`) ship a `static/description/icon.png` either, and it is not required for install; fabricating a placeholder binary would deviate from the actual repo convention

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `hr.attendance.ot.rule` model, its default data, and its access rights — needed by all three user stories (US1 reads rules to compute hours, US2 lets staff edit them, US3 reports rely on the pay categories they define).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create the `hr.attendance.ot.rule` model in `serichai-odoo/serichai_hr_attendance/models/hr_attendance_ot_rule.py` per data-model.md: fields `name` (Char, required), `wage_type` (Selection: daily/monthly, required), `day_type` (Selection: weekday/sunday_holiday, required), `sequence` (Integer, default 10), `time_from`/`time_to` (Float, widget `float_time`, 0–24), `pay_type` (Selection: normal/ot150/ot200, required), `catch_outside` (Boolean, default False), `company_id` (Many2one `res.company`, default `env.company`), `active` (Boolean, default True); add an `@api.constrains('time_from', 'time_to')` raising `ValidationError` when `time_from >= time_to`
- [X] T005 Wire `serichai-odoo/serichai_hr_attendance/models/__init__.py` to import `hr_attendance_ot_rule`, and `serichai-odoo/serichai_hr_attendance/__init__.py` to import `models` (depends on T004)
- [X] T006 [P] Create `serichai-odoo/serichai_hr_attendance/security/ir.model.access.csv` granting `group_hr_attendance_manager` and `group_hr_attendance_officer` full CRUD (`perm_read,perm_write,perm_create,perm_unlink` all `1`) on `model_hr_attendance_ot_rule`, per the user's explicit decision to open create/edit to Officers too
- [X] T007 [P] Create `serichai-odoo/serichai_hr_attendance/security/hr_attendance_ot_rule_security.xml` with a multi-company `ir.rule` restricting `hr.attendance.ot.rule` to `[('company_id', 'in', company_ids)]`, mirroring `hr_attendance`'s own `hr_attendance_rule_employee_company` pattern
- [X] T008 Create `serichai-odoo/serichai_hr_attendance/data/hr_attendance_ot_rule_data.xml` seeding the 8 default rules from data-model.md's default rule table (Daily/Monthly × Weekday/Sunday-Holiday, exact `time_from`/`time_to`/`pay_type`/`catch_outside` values) (depends on T004)
- [X] T009 Register `security/ir.model.access.csv`, `security/hr_attendance_ot_rule_security.xml`, and `data/hr_attendance_ot_rule_data.xml` in `__manifest__.py`'s `data` list, in that order (depends on T002, T006, T007, T008)

**Checkpoint**: `python3 odoo-bin ... -i serichai_hr_attendance --stop-after-init` installs cleanly; the 8 default `hr.attendance.ot.rule` records exist; Managers and Officers can read/write them via ORM. No `hr.attendance`/`hr.employee` changes yet — user story work can now begin.

---

## Phase 3: User Story 1 - Automatic pay-category split on every attendance record (Priority: P1) 🎯 MVP

**Goal**: Every `hr.attendance` record automatically shows Normal / OT 1.5x / OT 2x hours, computed from the employee's wage type and the record's day type, with no manual entry.

**Independent Test**: Set wage types on two test employees (one Daily Paid, one Monthly Paid); create attendance records for a plain weekday shift, a weekday shift into evening overtime, and a Sunday shift for each; confirm each record's computed split matches contracts/compute-engine.md's Verification contract without any manual calculation.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; they MUST fail (or error, since the fields/methods don't exist yet) before the implementation tasks below land.

- [X] T010 [P] [US1] Write unit/integration tests for `_get_day_type()`, `_interval_overlap()`, `_hours_outside()`, and `_compute_ot_hours()` in `serichai-odoo/serichai_hr_attendance/tests/test_ot_rule_engine.py`, covering all 12 verification scenarios in `contracts/compute-engine.md` (both wage types, both day types, overnight midnight-split, the Daily-Sunday unpaid gap, the weekday inter-window gap, sub-30-minute rounding, missing `wage_type`, and open/no-check-out attendance)
- [X] T011 [P] [US1] Write a test for the historical backfill in `serichai-odoo/serichai_hr_attendance/tests/test_ot_backfill.py`: create `hr.attendance` records, invoke the `post_init_hook` backfill logic directly, and assert all four new fields are correctly populated (non-blank) afterward per SC-005

### Implementation for User Story 1

- [X] T012 [US1] Add `wage_type` Selection field (`daily`/`monthly`, no default) to `hr.employee` by inheriting it in `serichai-odoo/serichai_hr_attendance/models/hr_employee.py`
- [X] T013 [US1] Expose `wage_type` on the employee form: inherit `hr.view_employee_form` in `serichai-odoo/serichai_hr_attendance/views/hr_employee_views.xml`, adding the field via `xpath="//field[@name='employee_type']"` `position="after"` (depends on T012)
- [X] T014 [US1] Add stored fields `day_type` (Selection: weekday/sunday_holiday), `normal_hours`, `overtime_150_hours`, `overtime_200_hours` (Float, `aggregator="sum"`) to `hr.attendance` by inheriting it in `serichai-odoo/serichai_hr_attendance/models/hr_attendance.py`
- [X] T015 [US1] Implement `_get_day_type(date, employee)` in `serichai-odoo/serichai_hr_attendance/models/hr_attendance.py` per contracts/compute-engine.md: Sunday → `sunday_holiday`; otherwise `sunday_holiday` if `date` falls within any `resource.calendar.leaves` record with empty `resource_id` on `employee.resource_calendar_id` (research.md Decision 2); else `weekday` (depends on T014)
- [X] T016 [US1] Implement `_interval_overlap(seg_start_hour, seg_end_hour, rule_from, rule_to)` and `_hours_outside(seg_start_hour, seg_end_hour, claimed_windows)` in `serichai-odoo/serichai_hr_attendance/models/hr_attendance.py` per contracts/compute-engine.md (depends on T014)
- [X] T017 [US1] Implement `_compute_ot_hours()` in `serichai-odoo/serichai_hr_attendance/models/hr_attendance.py` with `@api.depends('check_in', 'check_out', 'employee_id.wage_type')`: handle open attendance (all fields zero) and missing `wage_type` (all worked time → `normal_hours`, log a warning) first; otherwise split `[check_in, check_out]` into per-calendar-date segments in the employee's timezone, set `day_type` from the check-in-date segment, look up active `hr.attendance.ot.rule` records per segment's `(wage_type, day_type, company_id)` ordered by `sequence`, apply the Precedence algorithm from data-model.md (non-catch-outside rules first, remaining time to the lowest-sequence `catch_outside` rule, unclaimed remainder dropped), sum per `pay_type` across segments, then round each of the three totals down to the nearest 0.5 (depends on T015, T016)
- [X] T018 [US1] Wire `serichai-odoo/serichai_hr_attendance/models/__init__.py` to import `hr_employee` and `hr_attendance` (depends on T012, T017)
- [X] T019 [US1] Register `views/hr_employee_views.xml` in `__manifest__.py`'s `data` list (depends on T013)
- [X] T020 [US1] Implement the batched backfill `post_init_hook(env)` (search `hr.attendance` in chunks of 1000, trigger recompute of the four new fields for each batch) in `serichai-odoo/serichai_hr_attendance/__init__.py`, matching what `tests/test_ot_backfill.py` (T011) asserts (depends on T017)

**Checkpoint**: User Story 1 is fully functional and independently testable — `tests/test_ot_rule_engine.py` and `tests/test_ot_backfill.py` pass; attendance records show correct computed hours with no UI changes required beyond the employee form's `wage_type` field.

---

## Phase 4: User Story 2 - Configure pay-rate windows without code changes (Priority: P2)

**Goal**: HR Officers/Managers can view, edit, and add `hr.attendance.ot.rule` records through the UI, with changes taking effect on newly computed attendance immediately.

**Independent Test**: As an HR Officer or Manager, open Attendances → Overtime Rules, edit an existing rule's time boundary (or add a new rule), save, then create an attendance record that overlaps the change and confirm the computed hours reflect it; confirm a regular employee cannot open the screen to edit.

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] Write access-control tests in `serichai-odoo/serichai_hr_attendance/tests/test_ot_rule_security.py`: a user in `group_hr_attendance_officer` or `group_hr_attendance_manager` can create/write/unlink `hr.attendance.ot.rule` records; a plain `base.group_user` employee cannot

### Implementation for User Story 2

- [X] T022 [US2] Create list + form views for `hr.attendance.ot.rule` in `serichai-odoo/serichai_hr_attendance/views/hr_attendance_ot_rule_views.xml` — list shows `name`, `wage_type`, `day_type`, `time_from`, `time_to`, `pay_type`, `catch_outside`, `sequence` (widget `float_time` on the two time fields), grouped/sortable by `wage_type`/`day_type`; form exposes all editable fields
- [X] T023 [US2] Add the `ir.actions.act_window` and `menuitem` for "Overtime Rules" directly under the Attendances root menu (a sibling of Configuration, so Officers can reach it too) in `serichai-odoo/serichai_hr_attendance/views/hr_attendance_ot_rule_views.xml` (same file as T022)
- [X] T024 [US2] Register `views/hr_attendance_ot_rule_views.xml` in `__manifest__.py`'s `data` list (depends on T022, T023)

**Checkpoint**: User Stories 1 AND 2 both work independently — HR Officers/Managers can manage the ruleset through the UI, and rule changes are picked up by US1's compute engine with no code change.

---

## Phase 5: User Story 3 - Review and export pay-category totals for payroll (Priority: P3)

**Goal**: Payroll/HR staff can see and export Normal/OT 1.5x/OT 2x totals via the attendance list (with correct group subtotals), a payroll-summary pivot view, and the standard export wizard.

**Independent Test**: With attendance records already showing computed splits, group the attendance list by month then employee and confirm correct subtotals; open "OT Analysis" and confirm the pivot's employee/day-type breakdown; export a selection and confirm the four new fields are present with correct values.

### Tests for User Story 3 ⚠️

- [X] T025 [P] [US3] Write a test in `serichai-odoo/serichai_hr_attendance/tests/test_ot_export.py` that opens the export wizard's field list for `hr.attendance` and asserts `normal_hours`, `overtime_150_hours`, `overtime_200_hours`, and `day_type` are present and selectable

### Implementation for User Story 3

- [X] T026 [US3] Inherit `hr_attendance.view_attendance_tree` in `serichai-odoo/serichai_hr_attendance/views/hr_attendance_views.xml`, inserting `normal_hours` (`widget="float_time"`, `optional="show"`, `sum="Total"`), `overtime_150_hours` and `overtime_200_hours` (`widget="float_time"`, `optional="show"`, `sum="Total"`), and `day_type` (`optional="hide"`) immediately after the `overtime_hours` field (research.md Decision 4)
- [X] T027 [US3] Add an `hr.attendance` pivot view (rows: `employee_id`, `day_type`; measures: `normal_hours`, `overtime_150_hours`, `overtime_200_hours`) plus its `ir.actions.act_window` and an "OT Analysis" `menuitem` under the Attendances app, in `serichai-odoo/serichai_hr_attendance/views/hr_attendance_views.xml` (same file as T026)
- [X] T028 [US3] Register `views/hr_attendance_views.xml` in `__manifest__.py`'s `data` list (depends on T026, T027)

**Checkpoint**: All three user stories are independently functional — the full feature is usable end-to-end via the UI, matching spec Success Criteria SC-001–SC-006.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Deliverables and validation that span the whole feature.

- [X] T029 [P] Write `serichai-odoo/serichai_hr_attendance/README.md` documenting what the module does, the 8 default rules, and how to add/edit/deactivate a rule from the UI without code changes (deliverable #2)
- [X] T030 Run `python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db --test-enable --stop-after-init -u serichai_hr_attendance` and confirm all tests (T010, T011, T021, T025) pass — **done**: clean install, clean upgrade (`-u`), 29/29 tests pass (0 failed, 0 errors); also confirmed no regression by running core `hr_attendance`'s own suite — its 6 pre-existing errors are an unrelated `res_partner.group_rfq` NOT NULL data issue from the `purchase_stock` module in this test database, not touched by this addon
- [X] T031 [PARTIAL] Execute the manual walkthrough in `quickstart.md` — **steps 1 (install) and 2 (automated tests) done** as part of T030; **steps 3–10 (browser walkthrough: setting Wage Type via the employee form, the Overtime Rules screen, list columns, OT Analysis pivot, export dialog, live rule-edit effect) were NOT performed** — no browser/UI-driving tool is available in this environment. Server-side view loading was validated indirectly: Odoo's own module loader parses and validates every inherited view's `xpath`/field references at install/upgrade time (it would hard-error on a bad xpath or unknown field), and this passed cleanly on both install and upgrade with "verifying fields for every extended model" succeeding. This is not a substitute for actually clicking through the UI — flagging so a human can do the browser walkthrough before considering this fully done.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational only — independent of US1 (edits the same rule records US1 reads, but needs no US1 code to be present to be tested via T021's ORM-level access tests; the "changes reflect in newly computed attendance" half of its independent test does rely on US1's compute engine already existing at *demo* time, not at *build* time)
- **User Story 3 (Phase 5)**: Depends on Foundational **and** the four `hr.attendance` fields from US1 (T014) existing to display/export/pivot — build after US1
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each User Story

- Tests before implementation (write-first, must fail)
- Model/field tasks before the compute/view tasks that use them
- Manifest `data`-list registration tasks come last in each phase (they touch the shared `__manifest__.py` file)

### Parallel Opportunities

- T003 can run alongside T001/T002 (different files)
- T006 and T007 can run in parallel with each other and with T005 (different files)
- T010 and T011 can run in parallel (different test files)
- T021 can run in parallel with US1 implementation tasks once Foundational is done (different file, no shared dependency other than Foundational)
- T025 can start as soon as Foundational + T014 (the four new fields) exist, in parallel with US2's tasks

---

## Parallel Example: User Story 1

```bash
# Tests (after Foundational, before implementation):
Task: "Write unit/integration tests for the compute engine in tests/test_ot_rule_engine.py"
Task: "Write backfill test in tests/test_ot_backfill.py"

# These two are the only [P] pair in US1 implementation (different concerns, but both
# touch models/hr_attendance.py in sequence — T015/T016/T017 are NOT parallel with each
# other since they share one file):
Task: "Add wage_type field to hr.employee in models/hr_employee.py"          # T012
Task: "(sequential) Add day_type/hour fields to hr.attendance in models/hr_attendance.py"  # T014
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (rule model + 8 default rules + access rights)
3. Complete Phase 3: User Story 1 (wage_type field + compute engine + backfill)
4. **STOP and VALIDATE**: run `tests/test_ot_rule_engine.py` and `tests/test_ot_backfill.py`; manually confirm a few attendance records compute correctly
5. This is a usable MVP: correct hours exist and are stored, even before any new UI surface (US2's config screen, US3's list/pivot/export) is built — they can still be inspected via the record's technical form fields or the ORM/shell in the meantime

### Incremental Delivery

1. Setup + Foundational → ruleset ready
2. Add US1 → correct hours computed automatically (MVP)
3. Add US2 → rules become editable from the UI without code changes
4. Add US3 → list columns, pivot, and export make the numbers usable for payroll
5. Polish → README, full test run, quickstart walkthrough

---

## Notes

- [P] tasks touch different files with no unmet dependency on an incomplete task
- Every task lists an exact file path so it's actionable without re-reading the design docs
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
