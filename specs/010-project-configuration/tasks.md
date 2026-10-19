# Tasks: Project Configuration - High-Value-First Task Sorting

**Input**: Design documents from `serichai-odoo/specs/010-project-configuration/`

**Prerequisites**: plan.md, spec.md, design.md (key snippets), research.md, data-model.md, quickstart.md. There is no `contracts/` (single area, no inter-module interface).

**Area**: `odoo` (root `serichai-odoo/`, fullstack). All paths below are relative to `serichai-odoo/` unless they start with `specs/`. The new addon is `serichai_project_config/`; it depends only on `project`. `serichai_project_access` (spec 009) and everything under `odoo/` and `muk_web_theme/` are NOT modified.

**Tests**: Requested in the feature description, so they are included. All tests live in one file, `serichai_project_config/tests/test_budget_sort.py`, so test tasks in different stories are sequential (same file), not `[P]`. Write each story's tests first and see them fail, then implement.

**Test DB**: do not use `serichai-db`. Ask the user for the throwaway test database name before the first test run (quickstart.md section 1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: user story from spec.md (US1..US6)

---

## Phase 1: Setup (shared structure)

**Purpose**: Create the addon skeleton. Match `serichai_project_mo` / `serichai_project_access` layout.

- [X] T001 Create the addon folder `serichai_project_config/` with empty-package files `serichai_project_config/__init__.py` (imports `models` only for now; T021 adds the hooks import), `serichai_project_config/models/__init__.py` and `serichai_project_config/tests/__init__.py`, plus directories `views/` and `tests/` (design.md "Project Structure" in plan.md)
- [X] T002 Write `serichai_project_config/__manifest__.py`: name "Project Configuration", version `1.0.0`, license `AGPL-3`, `depends: ['project']` only (FR-001), `data: []` for now. Each later task adds its own entry: T009 adds `views/project_task_views.xml`, T019 adds `views/res_config_settings_views.xml`, T021 adds `pre_init_hook`/`post_init_hook`. This keeps the module installable after every task. Copy the author/category/summary style from `serichai_project_access/__manifest__.py`. Do not add any other Serichai module to `depends`.

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: Shared parsing, threshold reading, the stored flag column and the test fixtures that every story uses.

**CRITICAL**: no story work starts until this phase is done.

- [X] T003 In `serichai_project_config/models/project_task.py` add the module constants and helpers from design.md: `PROJECT_VALUE_LABEL = 'มูลค่าโครงการ'`, `THRESHOLD_PARAM = 'serichai_project_config.high_budget_threshold'`, `DEFAULT_THRESHOLD = 50_000_000.0`, `_AMOUNT_RE = re.compile(r'[-+]?\d+(\.\d+)?')`, `parse_amount(prop_type, raw)` and `is_value_property(prop)`. Rules (data-model.md): counted only for `integer`/`float`/`monetary` (finite number, not a `bool`) and `char`/`text` (remove whitespace and `,`, then the text must fullmatch `[-+]?\d+(\.\d+)?`); anything else or any non-finite result gives `0.0`; the label is matched with `.strip()` only, first match wins. Add `_logger = logging.getLogger(__name__)`. Register the module in `serichai_project_config/models/__init__.py` (`from . import project_task`).
- [X] T004 In `serichai_project_config/models/project_task.py` add `class ProjectTask(models.Model)` with `_inherit = 'project.task'`, the stored field `is_high_value = fields.Boolean(string='High Value', compute='_compute_is_high_value', store=True, ...)` (readonly; data-model.md: depends on `task_properties` and `project_id` only, no `project_id.task_properties_definition`), and `_get_high_value_threshold()` (`@api.model`: read `THRESHOLD_PARAM` via `sudo()` with a comment; unset or empty gives 50,000,000; `"0.0"` is a real 0; letters, negative or non-finite fall back to 50,000,000, never raise). Do not override `_order` (FR-010). Depends on T003.
- [X] T017 In `serichai_project_config/models/project_task.py` add `_recompute_high_value(self, batch_size=1000)` (`@api.model`) per design.md: `sudo().with_context(active_test=False)`, ids ordered by `id`, per batch `env.add_to_compute(self._fields['is_high_value'], batch)`, `flush_recordset(['is_high_value'])`, `invalidate_recordset()`; commented `sudo()`. Needed by the US1/US2/US4/US5 tests and by T021; depends on T004 (it only schedules the compute, which T008 implements).
- [X] T005 In `serichai_project_config/tests/test_budget_sort.py` create the test class skeleton (`TransactionCase`, `@tagged('post_install', '-at_install')`, `serichai_project_config` tag) with fixtures: a helper that builds a project with a `task_properties_definition` containing a property of a given type labelled `มูลค่าโครงการ` (internal `name` differs per project), a helper that creates tasks with property values, and a helper that sets or clears the threshold parameter. Import it from `serichai_project_config/tests/__init__.py`. Depends on T001.

**Checkpoint**: the module installs (`-i serichai_project_config`) with no views or hooks yet, and fixtures exist.

---

## Phase 3: User Story 1 - Starred, then high-value tasks first, then by deadline (P1) MVP

**Goal**: The internal task list and kanban show priority first, then high-value, then deadline ascending (empty last), then newest first; the model `_order` is untouched.

**Independent Test**: spec US1 / quickstart section 3 steps 1-3: values 60M (next month), 40M (tomorrow), none (next week), 70M (no deadline) give A, D, B, C; starring C puts it first.

### Tests for User Story 1 (write first, expect failure)

- [X] T006 [US1] In `serichai_project_config/tests/test_budget_sort.py` add tests: float property 60M sets `is_high_value`; 40M does not; exactly 50M does not (strictly greater, FR-005); with threshold 30M param a 40M task is high-value after `_recompute_high_value()`
- [X] T007 [US1] In `serichai_project_config/tests/test_budget_sort.py` add order tests that read `default_order` from the arch of the task list (`project.view_task_tree2`) and kanban (`project.view_task_kanban`) views via `get_view` and search with it: starred first (priority `'3'` > `'2'` > `'1'` > `'0'`), then high-value, then deadline with empty deadlines last, then `id desc`; a starred non-high-value task sorts above an unstarred high-value one; the model `_order` equals its original core value; the portal sharing list view (`project_task_view_tree_main_base`) has no `is_high_value` in its order

### Implementation for User Story 1

- [X] T008 [US1] In `serichai_project_config/models/project_task.py` implement `_compute_is_high_value` per design.md: `@api.depends('task_properties', 'project_id')`, computed as superuser through field access, finds the first project definition for which `is_value_property` is true, parses `task.task_properties.get(prop['name'])` with `parse_amount`, sets `is_high_value = value > threshold`; no project, no property, empty or unparseable gives `False`. The per-task parse is wrapped in `try/except (ValueError, TypeError, KeyError, AttributeError)` with `_logger.debug(..., task.id, exc_info=True)` (FR-007). No bare `except`.
- [X] T009 [US1] Create `serichai_project_config/views/project_task_views.xml` with the two order extensions: `project_task_view_tree_base` (inherits `project.project_task_view_tree_base`, name `project.task.view.list.base.inherit.high.value`) and `view_task_kanban` (inherits `project.view_task_kanban`), each `<list|kanban position="attributes">` setting `default_order="priority desc, is_high_value desc, date_deadline asc, id desc"`. Do not use `nulls last` (the client drops it; PostgreSQL ASC already puts NULLs last, research V4). Never inherit `project_task_view_tree_main_base` (portal list, research V5). Add `views/project_task_views.xml` to the manifest `data`.

**Checkpoint**: US1 tests pass; All Tasks and the kanban show the new order.

---

## Phase 4: User Story 2 - Sorting never fails when the property is missing or odd (P1)

**Goal**: Missing, renamed, deleted or unreadable property counts as 0 with no error; labels match across projects with different keys; moving a task re-evaluates it.

**Independent Test**: spec US2 / quickstart section 3 steps 5-7: no project has the property gives pure priority-then-deadline order; "abc" saves and sorts by deadline.

### Tests for User Story 2 (write first, expect failure)

- [X] T010 [US2] In `serichai_project_config/tests/test_budget_sort.py` add tests: char `"60,000,000"` is high-value and `parse_amount('char', "60,000,000")` returns `60000000.0`; `"abc"`, `"nan"`, `""`, `None`, a list, many2one and selection values give `0.0` and `is_high_value False`, and a task holding `"abc"` saves without error; task without project and project without the property give `False`; two projects with different internal keys but the same label (one with leading/trailing spaces) both work; two properties with the same label, the first wins
- [X] T011 [US2] In `serichai_project_config/tests/test_budget_sort.py` add tests: moving a high-value task to a project that lacks the property clears the flag at once; moving it to a project that has the property re-evaluates it; deleting or renaming the definition leaves the flag unchanged until `_recompute_high_value()` and then resets it to `False`; editing a task's own value updates its flag at once; with no project defining the property, the search order equals `priority desc, date_deadline asc, id desc`; one bad task in a batch does not stop the others

### Implementation for User Story 2

- [X] T012 [US2] Review and, if needed, harden `serichai_project_config/models/project_task.py` so T010/T011 pass without errors: `parse_amount` rejects `bool` and non-finite numbers; `_compute_is_high_value` handles each task inside its own `try/except` so one bad record never aborts the batch; archived and project-less tasks are evaluated; nothing logs above `debug`. No new file.

**Checkpoint**: US1 and US2 tests pass; the fail-safe behaviour is proven.

---

## Phase 5: User Story 3 - Planners see and filter by project value (P2)

**Goal**: A "Project Value" column (shown by default, hideable) and a "High Value" filter, offered to everyone.

**Independent Test**: spec US3 / quickstart section 3 step 4: the column shows each task's value, the filter leaves only tasks above the threshold.

### Tests for User Story 3 (write first, expect failure)

- [X] T013 [US3] In `serichai_project_config/tests/test_budget_sort.py` add tests: `project_value` equals the amount for a project user (float, integer, monetary and `"60,000,000"` text); 0 for a task without the property, a task without a project and an unsaved record; the "High Value" filter domain `[('is_high_value', '=', True)]` returns only high-value tasks; the list view arch contains `project_value` with `optional="show"` and the search view arch contains the `high_value` filter

### Implementation for User Story 3

- [X] T014 [US3] In `serichai_project_config/models/project_task.py` add `project_value = fields.Float(string='Project Value', compute='_compute_project_value')` (not stored) and `_compute_project_value` per design.md: `@api.depends_context('uid')` plus `@api.depends('task_properties', 'project_id')`, initialise 0.0, read only saved records through the user's own `saved.read(['task_properties'])` (one call per batch, no `sudo`), catch `AccessError` around that call and leave 0, then for each row find the property with `is_value_property` and set `parse_amount(prop.get('type'), prop.get('value'))`; per-row `try/except (ValueError, TypeError, KeyError, AttributeError)` with a `_logger.debug` including the task id. Add the comment explaining why `read()` and not field access (design.md, research V5). Depends on T008.
- [X] T015 [US3] In `serichai_project_config/views/project_task_views.xml` add `<field name="project_value" optional="show"/>` after `date_deadline` in the list extension (T009), and a new extension record of `project.view_task_search_form` (name `project.task.search.form.inherit.high.value`) adding `<filter string="High Value" name="high_value" domain="[('is_high_value', '=', True)]"/>` plus a `<separator/>` before `open_tasks` (design.md). Depends on T009, T014.

**Checkpoint**: column and filter work for admins and project users.

---

## Phase 6: User Story 4 - Administrators adjust the threshold and refresh values (P2)

**Goal**: Admin-only threshold in Settings (default 50,000,000, 0 allowed, invalid falls back silently) and a "Recalculate high-value flag" action.

**Independent Test**: spec US4 / quickstart section 3 step 8: set 30M, save, recalculate, and a 40M task becomes high-value.

### Tests for User Story 4 (write first, expect failure)

- [X] T016 [US4] In `serichai_project_config/tests/test_budget_sort.py` add tests: unset parameter, `'abc'`, `'-5'`, `'inf'` and empty string give 50,000,000 (including through `get_values`); saving 0 in settings stores `"0.0"` and reads back 0, and with threshold 0 a task with any positive value is high-value after recalculation; saving 30M changes no flag until `action_serichai_recompute_high_value` runs, then a 40M task is high-value; saving an unrelated setting changes nothing; a non-admin user calling the action gets `AccessError`; `_recompute_high_value` with `batch_size=2` over 5 tasks (archived included) recomputes all and continues when one task is unreadable

### Implementation for User Story 4

- [X] T018 [P] [US4] Create `serichai_project_config/models/res_config_settings.py` per design.md: `ResConfigSettings(_inherit='res.config.settings')`, float field `serichai_high_value_threshold` WITHOUT `config_parameter=`, `get_values` returning `project.task._get_high_value_threshold()`, `set_values` writing `repr(value)` to `THRESHOLD_PARAM` via commented `sudo()` (no recompute here), and `action_serichai_recompute_high_value` that raises `AccessError` unless `base.group_system` (FR-016), calls `_recompute_high_value()` and returns a `display_notification` success action. Register it in `serichai_project_config/models/__init__.py`. Depends on T017 for the action.
- [X] T019 [P] [US4] Create `serichai_project_config/views/res_config_settings_views.xml`: record `res_config_settings_view_form` inheriting `project.res_config_settings_view_form`, adding `<block title="Task Sorting" groups="base.group_system">` after `//block[@id='tasks_management']`, with one `<setting>` holding the threshold field and a `btn-link` button `action_serichai_recompute_high_value`, plus a muted hint under the button: "Run after changing the threshold or a project's 'มูลค่าโครงการ' property; edited tasks update on their own." Add `views/res_config_settings_views.xml` to the manifest `data`. Depends on T018 (field and action names).

**Checkpoint**: threshold and recalculation work and are admin-only.

---

## Phase 7: User Story 5 - Existing tasks are ready on installation (P2)

**Goal**: Install fills the flag for every existing task in batches and succeeds even when no project has the property.

**Independent Test**: spec US5 / quickstart section 5: install on a copy of production data and high-value tasks are on top without editing any task.

### Tests for User Story 5 (write first, expect failure)

- [X] T020 [US5] In `serichai_project_config/tests/test_budget_sort.py` add tests: `post_init_hook(env)` marks existing high-value tasks and leaves others `False`; it runs without error when no project has the property and when tasks hold garbage values; `pre_init_hook(env)` is idempotent (does nothing when the column already exists)

### Implementation for User Story 5

- [X] T021 [US5] Create `serichai_project_config/hooks.py` per design.md: `pre_init_hook(env)` creates the `bool` column `project_task.is_high_value` with `tools.sql.create_column` only if `column_exists` is false (fixed identifiers, no user input); `post_init_hook(env)` calls `env['project.task']._recompute_high_value()`. Wire both in `serichai_project_config/__init__.py` (`from .hooks import pre_init_hook, post_init_hook`) and add `pre_init_hook`/`post_init_hook` to the manifest. Depends on T017.

**Checkpoint**: a fresh install on `<test_db>` and on a production copy leaves tasks correctly flagged.

---

## Phase 8: User Story 6 - Users who cannot see the project value still get a correct list (P1)

**Goal**: With any access module that hides properties in `read()` (spec 009 does), the user gets the same order with no errors, and the column shows 0 instead of an amount they may not read. No 009-specific code, no change to 009.

**Independent Test**: spec US6 / quickstart section 4.

### Tests for User Story 6 (write first, expect failure)

- [X] T022 [US6] In `serichai_project_config/tests/test_budget_sort.py` add tests that simulate the restricted user by patching `project.task.read`: once stripping the `มูลค่าโครงการ` property from the returned `task_properties`, once raising `AccessError`. In both cases `project_value` is 0 with no exception, a `project_value` export row (`export_data`) is 0, while `is_high_value` and the list order are identical to those seen by an unrestricted user; a task in a project where the property is not hidden still shows its amount

### Implementation for User Story 6

- [X] T023 [US6] Verify `_compute_project_value` in `serichai_project_config/models/project_task.py` (T014) satisfies T022: it must not use `sudo()`, must catch `AccessError` only around the `read()` call, and must not reference any `serichai_*` module. Run `grep -rn "serichai_project_access\|_get_project_access" serichai_project_config/` and confirm no output (FR-001, quickstart section 1). Fix any gap in the same file.

**Checkpoint**: restricted-user behaviour proven without touching 009.

---

## Phase 9: Polish and cross-cutting

- [X] T024 Run the full test suite on the throwaway DB (ask the user for the name first): `cd odoo && ../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d <test_db> --without-demo=all --no-http --test-enable --stop-after-init -i serichai_project_config --test-tags /serichai_project_config`. Expect 0 failed, 0 errors, and no warnings during install (SC-003).
- [X] T025 If `serichai_project_access` is installed on `<test_db>`, run its suite too (`--test-tags /serichai_project_access`) to confirm it still passes unchanged (spec 009 not modified, FR-020).
- [ ] T026 Walk through `specs/010-project-configuration/quickstart.md` sections 3-5 on a copy of the database and record the result in `specs/010-project-configuration/quickstart.md` only if a step needs correcting. Check that the portal task list and the Contract MO report keep their order (SC-008).
- [X] T027 Hand-over note for the user (no file change): run the constitution gate `-u serichai_project_config --test-enable` on `serichai-db` after deployment, and after merge amend the constitution "Addons" list and `CLAUDE.md` (see plan.md "Post-merge follow-up").

---

## Dependencies and execution order

- **Phase 1** (T001-T002) first. **Phase 2** (T003-T005 and T017) blocks every story. T004 depends on T003; T005 depends on T001 only.
- **US1** (T006-T009) is the MVP. T006/T007 first (same test file, sequential), then T008, then T009 (T009 needs the field from T004).
- **US2** (T010-T012) depends on US1's compute (T008). Tests T010/T011 are sequential (same file).
- **US3** (T013-T015) depends on T008 and T009. T015 edits the view file created in T009.
- **US4** (T016-T019): T017 is in Phase 2; T018 and T019 are different files, `[P]` once T017 exists, but T019 needs T018's names.
- **US5** (T020-T021) depends on T017.
- **US6** (T022-T023) depends on US3's `project_value` (T014).
- **Polish** (T024-T027) last.

Stories US2, US3, US4 and US5 can proceed in parallel after US1 if staffed, except that they all edit `models/project_task.py` and `tests/test_budget_sort.py`; keep those edits sequential or merge carefully.

## Parallel opportunities

- T018 and T019 (settings model and settings view, different files) after T017.
- Different developers can take US3 (`views/project_task_views.xml`, `project_value`), US4 (`models/res_config_settings.py`, `views/res_config_settings_views.xml`) and US5 (`hooks.py`) in parallel after US1, since the source files differ; only the shared test file needs coordination.

## Implementation strategy

1. **MVP**: Phases 1-3 (US1). Stop and check that All Tasks and the kanban show priority, then high-value, then deadline.
2. Add **US2** (fail-safe) before any rollout: it is also P1.
3. Add **US6** (P1) once `project_value` exists in US3; deliver US3 first.
4. Add **US4** and **US5** (P2) to finish administration and install.
5. Finish with Polish. Known limitations to keep in mind (spec Assumptions): dragging a task inside a kanban column does not keep its position; the Project Value column cannot be sorted by clicking its header; a threshold or definition change needs Recalculate; hidden users can infer high-value status from position or the filter.

## Notes

- Every task names the file(s) it touches; all are in area `odoo`.
- Do not edit `odoo/`, `muk_web_theme/` or `serichai_project_access/`.
- Do not commit as part of elaboration; commits happen in `/jy-sdd:execution`.

---

## Phase 10: Convergence

- [X] T028 Install `serichai_project_access` on `serichai-test` only (never `serichai-db`) with `-i serichai_project_access`, then confirm that its restricted list and kanban views (`serichai_access_task_list`, `serichai_access_task_kanban`) end up with `default_order="priority desc, is_high_value desc, date_deadline asc, id desc"` via `get_view`, that a user with a hidden `มูลค่าโครงการ` line gets `project_value` 0 and the same order as an admin, and that `--test-tags /serichai_project_access` still passes unchanged; add the confirmed view check to `serichai_project_config/tests/test_budget_sort.py` as a test skipped when 009 is not installed, without importing or naming 009 in module code per FR-008, FR-020 (partial)

---

## Phase 11: Review follow-ups

- [X] T029 [US1] In `serichai_project_config/views/project_task_views.xml` stop the new `default_order` and the Project Value column from reaching the task-template list, the templates kanban and the milestone task list (core views inheriting `project.project_task_view_tree_base` at `project_task_views.xml` lines ~1002 and ~1329, and the templates kanban): add child extensions that restore the core order `priority desc, sequence, date_deadline asc, id desc` and remove `project_value` on those views, per FR-010; add a test in `serichai_project_config/tests/test_budget_sort.py` asserting those views keep the core order and have no `project_value`
- [X] T030 In `serichai_project_config/hooks.py` create the column with `create_column(env.cr, "project_task", "is_high_value", "boolean")` so that it gets `DEFAULT false`, and extend `test_pre_init_hook_idempotent` in `serichai_project_config/tests/test_budget_sort.py` to assert existing rows are `false`, not NULL
- [X] T031 In `serichai_project_config/tests/test_budget_sort.py` strengthen `test_unhidden_project_still_shows_amount` (assert the real visible amount for a task whose label matches), remove the unused `marker` task in `test_order_priority_then_high_value_then_deadline`, and make `test_move_between_projects` assert against literal expected values instead of restating the production logic
- [X] T032 Remove the unnecessary `# pylint: disable=pointless-statement` first line of `serichai_project_config/__manifest__.py`

---

## Phase 12: Review follow-ups (round 2)

- [X] T033 In `serichai_project_config/views/project_task_views.xml` change the `default_order` of the main task list and kanban extensions (`project_task_view_tree_base`, `view_task_kanban`) to `priority desc, is_high_value desc, state, date_deadline asc, id desc` (keeps the core `state` term so open tasks stay apart from done and cancelled ones) per FR-008, FR-009 (contradicts); update the order assertions in `serichai_project_config/tests/test_budget_sort.py` (`test_order_views_use_flag`, `test_order_priority_then_high_value_then_deadline`, `test_no_property_anywhere_order`, `test_order_in_restricted_access_views`) and add a test that an open task sorts before a done task of the same priority and value
