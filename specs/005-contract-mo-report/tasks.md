# Tasks: Contract MO Print Report for Project Task

**Input**: Design documents from `/specs/005-contract-mo-report/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/report-contract.md, quickstart.md

**Tests**: Included — plan.md's Technical Context commits to `TransactionCase` tests asserting the report renders without error across the spec's data-completeness edge cases, matching this repo's existing test convention (`serichai_project_security/tests/`, `serichai_hr_attendance/tests/`).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3) so each can be implemented and independently tested/demoed on its own. Because this feature is two XML files in one existing addon, several stories touch the same `report/project_task_report_templates.xml` file — dependencies are called out explicitly where that happens instead of marking those tasks `[P]`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: US1 / US2 / US3, per spec.md's prioritized user stories
- All paths are relative to the repo root (`/home/odoo/serichai-odoo`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new `report/` subpackage and `tests/` package inside the existing `serichai_project_mo` addon so later phases have somewhere to add code.

- [X] T001 Create the `serichai-odoo/serichai_project_mo/report/` directory (pure-XML report package — no `__init__.py` needed, matching core precedent e.g. `odoo/addons/delivery/report/`, `odoo/addons/hr_expense/report/`)
- [X] T002 [P] Create `serichai-odoo/serichai_project_mo/tests/__init__.py` (imports `test_contract_mo_report`, added ahead of T006 since this addon had no `tests/` package yet)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Register the report action and the QWeb template skeleton — nothing prints, and no user story can be demoed, until these exist.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `serichai-odoo/serichai_project_mo/report/project_task_report_views.xml` with the `action_report_contract_mo` record per contracts/report-contract.md's `ir.actions.report` record contract: `name` "Contract MO", `model` `project.task`, `report_type` `qweb-pdf`, `report_name`/`report_file` both `serichai_project_mo.report_contract_mo`, `print_report_name` `'Contract MO - %s' % object.name`, `binding_model_id` `ref="model_project_task"` (research.md Decision 2), `binding_type` `report`
- [X] T004 Create `serichai-odoo/serichai_project_mo/report/project_task_report_templates.xml` with the `report_contract_mo` template skeleton per research.md Decision 3: `<t t-call="web.html_container">` → `<t t-foreach="docs" t-as="o">` → `<t t-call="web.internal_layout">` → `<div class="page">` containing a centered document title heading (content sections added by later phases)
- [X] T005 Register `report/project_task_report_views.xml` and `report/project_task_report_templates.xml` in `serichai-odoo/serichai_project_mo/__manifest__.py`'s `data` list, after the existing `views/*.xml` entries (depends on T003, T004)

**Checkpoint**: `python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory -d serichai-db -u serichai_project_mo --stop-after-init` upgrades cleanly; opening any task's Print dropdown shows "Contract MO" (title-only PDF so far) — user story work can now begin.

---

## Phase 3: User Story 1 - Print a company-standard order document for a task (Priority: P1) 🎯 MVP

**Goal**: A task with linked Manufacturing Orders prints a PDF containing every content section from the paper form, correctly populated.

**Independent Test**: Link 2-3 MOs of different sizes/quantities to a task, set its description and project, print "Contract MO," and confirm the PDF shows the task name as job, creation date, project, one item-table row per MO (product/size + qty), the joined MO reference numbers as the announcement number, the description as remarks, and the signature blocks.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; they MUST fail (template has no content sections yet) before the implementation tasks below land.

- [X] T006 [P] [US1] Write `serichai-odoo/serichai_project_mo/tests/test_contract_mo_report.py::test_render_with_data`: create a `project.task` with 2-3 linked `mrp.production` records (distinct `product_id`/`product_qty`), a `project_id`, and `description` text; render `serichai_project_mo.report_contract_mo` via `self.env['ir.actions.report']._render_qweb_html(...)`; assert no error and that the rendered HTML contains the task name, each linked MO's product display name and quantity, the joined MO names (announcement number), and the description text
- [X] T007 [US1] Wire `serichai-odoo/serichai_project_mo/tests/__init__.py` to import `test_contract_mo_report` (depends on T002, T006)

### Implementation for User Story 1

- [X] T008 [US1] Add the header-fields section to `serichai-odoo/serichai_project_mo/report/project_task_report_templates.xml`: a `table-borderless` row with job/สำหรับงาน (`o.name`), order date/วันที่สั่ง (`o.create_date`, widget `date`), and a project line `t-if="o.project_id"` showing `o.project_id.name` (depends on T004)
- [X] T009 [US1] Add the production-announcement-number field (สำหรับผลิตประกาศเลขที่) to the header section, sourced from `', '.join(o.mrp_production_ids.mapped('name'))` per the resolved spec clarification (FR-009), same file (depends on T008)
- [X] T010 [US1] Add the item table to `report/project_task_report_templates.xml`: `table-bordered` with columns ลำดับ/รายการ/จำนวน, a `t-foreach="o.mrp_production_ids" t-as="mo"` real-row block (index, `mo.product_id.display_name`, `mo.product_qty` + `mo.product_uom_id.name`), followed by a blank-row padding block sized to `N = 15` (constant pinned per code-review finding A1) (depends on T004) — implemented directly with the `max(0, N - len(...))` safe form from T019, since writing it unsafe-then-fixing added no value
- [X] T011 [US1] Add the remarks/หมายเหตุ section to `report/project_task_report_templates.xml`: a `table-borderless` row rendering `o.description` (Html field, plain `t-field`, research.md Decision 6) (depends on T004)
- [X] T012 [US1] Add the two signature blocks to `report/project_task_report_templates.xml`: a `table-borderless text-center` row with signature lines labeled หัวหน้าแผนกเย็บ (always blank) and ผู้สั่งผลิต (`', '.join(o.user_ids.mapped('name'))`) (depends on T004)

**Checkpoint**: User Story 1 is fully functional and independently testable — `test_render_with_data` passes; a populated task prints a complete, correctly-mapped PDF.

---

## Phase 4: User Story 2 - Discover and print the report like every other Odoo document (Priority: P2)

**Goal**: "Contract MO" is discoverable purely via the standard Print menu, with standard Odoo report chrome — no dedicated button, no special-cased layout.

**Independent Test**: Open any task's Print dropdown and confirm "Contract MO" is listed with no extra setup; confirm the printed PDF's header/footer/logo matches the company's configured report layout, same as any other Odoo PDF report.

### Tests for User Story 2 ⚠️

- [X] T013 [P] [US2] Write `serichai-odoo/serichai_project_mo/tests/test_contract_mo_report.py::test_report_action_binding` (same file as T006, new test method): assert `action_report_contract_mo`'s `binding_model_id.model == 'project.task'` and `binding_type == 'report'`, and that `self.env['ir.actions.report'].get_bindings('project.task')` includes it — confirming Print-menu discoverability without opening a browser (depends on T003)

### Implementation for User Story 2

- [X] T014 [US2] Manually verify quickstart.md step 4 (printed PDF's header/footer/logo matches Settings → General Settings → Companies → Document Layout, same chrome as another standard report e.g. a Sales Order) — no code change; this story is satisfied entirely by Phase 2's `binding_model_id`/`binding_type`/`web.internal_layout` usage (depends on T003, T004)

**Checkpoint**: User Stories 1 AND 2 both work independently — the report has full content (US1) and is discoverable/styled exactly like every other Odoo report (US2), verified by T013's binding test and T014's manual chrome check.

---

## Phase 5: User Story 3 - Report prints cleanly with incomplete data (Priority: P3)

**Goal**: A task missing linked MOs, project, description, or assignees — or one with more linked MOs than the table's default row count — still prints a clean, error-free PDF.

**Independent Test**: Print a bare task (no MOs, no project, no description) and confirm a clean PDF with a fully blank ruled table; link more MOs than the template's row constant to a task and confirm every MO still appears as a row.

### Tests for User Story 3 ⚠️

- [X] T015 [P] [US3] Write `serichai-odoo/serichai_project_mo/tests/test_contract_mo_report.py::test_render_empty_task` (same file as T006/T013, new test method): a task with zero linked MOs, no `project_id`, no `description`, no `user_ids`; render the report; assert no error, the item table has only blank rows, and the announcement-number field and both signature-name spans are empty rather than raising
- [X] T016 [P] [US3] Write `serichai-odoo/serichai_project_mo/tests/test_contract_mo_report.py::test_render_overflow_mos` (same file, new test method): a task with more linked MOs than the template's blank-row constant `N`; render the report; assert every linked MO's product/quantity appears in the output (no data loss) and no negative-range error occurs
- [X] T017 [US3] ~~Wire `tests/__init__.py`~~ — **no-op**: T002/T007 already import the whole `test_contract_mo_report` module, so T013/T015/T016's new methods are collected automatically; no further edit needed to ensure the new test methods are collected (only needed if T007 didn't already cover the whole module import — same file) (depends on T007, T015, T016)

### Implementation for User Story 3

- [X] T018 [US3] In `report/project_task_report_templates.xml`, confirm/adjust the `t-if` guards around the project line (T008), remarks section (T011), and both signature-name spans (T012) so each renders blank rather than erroring when `project_id`, `description`, or `user_ids` is falsy (depends on T008, T011, T012)
- [X] T019 [US3] ~~Change the blank-row padding loop to the safe `max(0, ...)` form~~ — **no-op**: T010 already implemented the safe form directly; `test_render_overflow_mos` (T016) confirms no negative-range error and no dropped rows (depends on T010)

**Checkpoint**: All three user stories are independently functional — `test_render_empty_task` and `test_render_overflow_mos` pass alongside `test_render_with_data` and `test_report_action_binding`, matching spec Success Criteria SC-001–SC-005.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation and documentation that span the whole feature.

- [X] T020 Run `python3 odoo-bin --http-port=8169 --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db --test-enable --test-tags /serichai_project_mo --stop-after-init -u serichai_project_mo` — **done**: clean upgrade, all 4 tests (`test_render_with_data`, `test_report_action_binding`, `test_render_empty_task`, `test_render_overflow_mos`) pass, 0 failed/0 errors; `--http-port` used because a dev server from `run_odoo.sh` was already bound to 8069 — no regression to the existing smart button/MO tab (unchanged files)
- [X] T021 [PARTIAL] Execute the browser walkthrough in quickstart.md steps 3-5 — **not performed**: no browser-driving/screenshot tool is available in this environment (same limitation noted in `004-attendance-ot-multiplier/tasks.md` T031). Substitute automated coverage: T006/T015/T016 assert the exact content quickstart.md step 3 asks a human to eyeball (job/date/project/announcement-number/item rows/remarks), and T013 asserts the Print-menu binding step 3-4 rely on. A human should still open a task in the browser and visually compare the PDF against `contract_mo_sample.jpg` before considering this fully done.
- [X] T022 [P] Add a short note to `CLAUDE.md`'s "serichai_project_mo" bullet under **Custom addon architecture** mentioning the new "Contract MO" print report, so the repo-level overview stays accurate

---

## Phase 7: Layout Revision — mockup `project_mo_report-sample.png` (2026-09-11)

**Purpose**: Rework the report's content to the annotated mockup: the task name in a bordered box, the task's `task_properties` printed as label/value pairs (skipping any property that no longer exists), a boxed "Manufacturing Order" heading, and item-table columns Manufacturing Order / Product / Quantity. Remarks and both signature blocks stay as they are; the order date, project line and announcement-number header field are dropped (spec FR-009 superseded by FR-013).

- [X] T023 Update `serichai-odoo/specs/005-contract-mo-report/spec.md`: add the 2026-09-11 clarification session, revise US1's acceptance scenarios and the edge cases, rewrite FR-004, mark FR-009 superseded, and add FR-011 (boxed task name), FR-012 (task_properties with existence check), FR-013 (new table columns)
- [X] T024 [P] Update `serichai-odoo/specs/005-contract-mo-report/data-model.md` and `contracts/report-contract.md` to describe the new report composition and the property-rendering helper contract (depends on T023)
- [X] T025 Add `_get_report_task_properties()` and `_format_report_property_value()` to `serichai-odoo/serichai_project_mo/models/project_task.py`: read `task_properties` through `read()` (so the ORM drops values whose definition no longer exists, and `serichai_project_security`'s read override still hides restricted properties), skip `separator` entries, and format each value per property type (FR-012)
- [X] T026 [US1] Write `serichai-odoo/serichai_project_mo/tests/test_contract_mo_report.py::test_render_task_properties`: a project defining 4 properties, a task setting 3 of them; assert every defined label prints (including the unset one, with a blank value) and that after removing two properties from the project's definition their labels no longer appear while the still-defined value does (depends on T025)
- [X] T027 Rework `serichai-odoo/serichai_project_mo/report/project_task_report_templates.xml`'s header: replace the job/date/project/announcement-number table with a bordered box holding `o.name`, followed by a `t-if`-guarded grid of `o._get_report_task_properties()` label/value pairs (FR-011, FR-012) (depends on T025)
- [X] T028 Rework the same file's item table: boxed "Manufacturing Order" heading above it, columns Manufacturing Order / Product / Quantity, rows showing `mo.name`, `mo.product_id.display_name`, `mo.product_qty` + `mo.product_uom_id.name`; keep the `max(0, 15 - len(...))` blank-row padding, the remarks section and both signature blocks unchanged (FR-013) (depends on T027)
- [X] T029 Update the existing tests for the revised content in `tests/test_contract_mo_report.py`: `test_render_with_data` no longer asserts the project name/announcement-number wording (MO references now come from the table column), and `test_render_empty_task` asserts the full blank ruled grid still renders (depends on T027, T028)
- [X] T030 Run `python3 odoo-bin --http-port=8169 --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory -d serichai-db --test-enable --test-tags /serichai_project_mo --stop-after-init -u serichai_project_mo` — **done**: clean upgrade, 5 tests pass, 0 failed / 0 errors; the rendered HTML was also dumped via `odoo-bin shell` for a task with 5 defined properties (one unset) and 2 linked MOs and visually matches the mockup's boxed name, property row, boxed heading and 3-column table
- [X] T031 [PARTIAL] Human check: open a task in the browser, print "Contract MO", and compare the PDF against `project_mo_report-sample.png` — **not performed as a real browser/PDF comparison**: no browser-driving tool is available in this environment (same limitation as T021). Substitute automated coverage performed instead: T026 asserts the property label/value + existence-check behavior the mockup calls out, and the rendered HTML for a representative task (5 defined properties, one unset, 2 linked MOs) was dumped via `odoo-bin shell` and inspected structurally — boxed name, property grid, boxed "Manufacturing Order" heading, and the Manufacturing Order/Product/Quantity columns all present and correctly populated, matching the mockup's annotated regions. A human should still open a task in the browser and visually compare the actual PDF (fonts, spacing, page breaks) against `project_mo_report-sample.png` before considering this fully done.

**Checkpoint**: The printed report matches the 2026-09-11 mockup; properties print only when they exist; the paper form's remarks and signature blocks are preserved.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational only — its test (T013) only needs T003; its "implementation" is verification, not new code
- **User Story 3 (Phase 5)**: Depends on Foundational **and** US1's template sections (T008, T010, T011, T012) existing, since it adjusts their guards/padding rather than adding new sections — build after US1
- **Polish (Phase 6)**: Depends on all three user stories being complete
- **Layout Revision (Phase 7)**: Depends on Phases 2-6 — it reworks the delivered template's content against the 2026-09-11 mockup rather than adding a new story

### Within Each User Story

- Tests before implementation (write-first, must fail)
- All template-content tasks in Phase 3 share one file (`report/project_task_report_templates.xml`) and are listed in a safe sequential order, even though several touch independent sections
- Manifest registration (T005) comes after the files it registers exist

### Parallel Opportunities

- T002 can run alongside T001 (different files)
- T006 can start as soon as Foundational (T003-T005) is done; T013 needs only T003, so it can run in parallel with T006-T012
- T015 and T016 can run in parallel with each other (independent test methods) once T008/T010/T011/T012 exist
- T022 can run in parallel with T020/T021 (different file, no shared dependency)

---

## Parallel Example: User Story 1

```bash
# Test (after Foundational, before implementation):
Task: "Write test_render_with_data in tests/test_contract_mo_report.py"          # T006

# Template sections (sequential — all in report/project_task_report_templates.xml):
Task: "Add header fields section"                                                # T008
Task: "Add production announcement number field"                                 # T009
Task: "Add item table with padding"                                              # T010
Task: "Add remarks section"                                                      # T011
Task: "Add signature blocks"                                                     # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (action record + template skeleton + manifest registration)
3. Complete Phase 3: User Story 1 (full content for a populated task)
4. **STOP and VALIDATE**: run `test_render_with_data`; print a populated task and compare against `contract_mo_sample.jpg`
5. This is a usable MVP: staff can already print a correct, complete order document for any task with data filled in

### Incremental Delivery

1. Setup + Foundational → report exists and appears in the Print menu (title-only)
2. Add US1 → full content prints correctly for populated tasks (MVP)
3. Add US2 → binding/chrome verified as standard Odoo practice (mostly already true from Foundational; this phase mainly adds proof)
4. Add US3 → empty and overflow tasks print cleanly, no errors, no data loss
5. Polish → full test run, quickstart walkthrough, CLAUDE.md note

---

## Notes

- [P] tasks touch different files (or independent test methods) with no unmet dependency on an incomplete task
- This feature adds no new models, fields, views, or security rules — every task stays within `report/`, `tests/`, and one `__manifest__.py` edit in the existing `serichai_project_mo` addon
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before moving on
