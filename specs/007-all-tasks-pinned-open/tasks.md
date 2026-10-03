---
description: "Task list for spec 007: open pinned-project tasks from the restricted All Tasks list"
---

# Tasks: Open Pinned-Project Tasks from the Restricted "All Tasks" List

**Input**: Design documents from `specs/007-all-tasks-pinned-open/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/module-interface.md, quickstart.md

**Tests**: Included. The plan's verification section and spec SC-002/SC-004 require automated
regression coverage, following specs 001 and 006.

**Status**: Closed 2026-10-03. All tasks are done. 33/33 automated tests pass, and the user confirmed the browser behaviour.

**Paths**: All source paths are relative to `serichai-odoo/serichai_project_security/`. Doc paths
are relative to `serichai-odoo/specs/007-all-tasks-pinned-open/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Register the new front-end asset location so the JS controller can load.

- [x] T001 Create directory `static/src/views/` and add an `'assets': {'web.assets_backend': ['serichai_project_security/static/src/views/restricted_task_list.js']}` entry in `__manifest__.py`, following `serichai_inventory_barcode/__manifest__.py`
- [x] T002 Bump `'version'` from `1.0.0` to `1.1.0` in `__manifest__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make the list aware of whether each row can be opened, and give the action somewhere to open to. US1 and US2 both depend on this.

- [x] T003 In `views/project_task_views.xml`, record `action_task_all_restricted`: change `view_mode` from `list` to `list,form` (research.md Decision 1). Keep `view_id` pointing at `view_task_list_restricted`.
- [x] T004 In `views/project_task_views.xml`, record `view_task_list_restricted`: remove the ineffective `open_form_view` attribute, and add `<field name="is_expanded_access_task" column_invisible="1"/>` after `tag_ids` so the client receives the per-row flag (data-model.md)

**Checkpoint**: The action can switch to the form and the list loads `is_expanded_access_task`. Every row would open at this point, so US1 and US2 must both land before release.

---

## Phase 3: User Story 1 - Open a pinned-project task straight from "All Tasks" (Priority: P1) 🎯 MVP

**Goal**: Clicking a pinned-project row opens its form. Edits save, and the pager stays on pinned rows.

**Independent Test**: As a user with only the restricted role and a project pinned, click a pinned row in **All Tasks**, edit a field, and save (quickstart M2–M5).

### Tests for User Story 1

- [x] T005 [P] [US1] Add `test_all_tasks_action_has_form_view` in `tests/test_access_restriction.py`, asserting that `action_task_all_restricted.view_mode == 'list,form'`
- [x] T006 [P] [US1] Add `test_restricted_list_uses_gating_controller` in `tests/test_access_restriction.py`, asserting that `get_view` on `view_task_list_restricted` has `js_class="serichai_restricted_task_list"`, `create="0"` and `delete="0"`, and that `is_expanded_access_task` is present with `column_invisible="1"`
- [x] T007 [P] [US1] Add helper `_rpc_request(method)` and `test_restricted_user_form_load_allowed_in_pinned_project` in `tests/test_access_restriction.py`. Patch `odoo.addons.serichai_project_security.models.project_task.request` with `SimpleNamespace(params={'model': 'project.task', 'method': 'web_read'})`, and check that the restricted user can `web_read` on `task_pinned` (research.md Decision 5)

### Implementation for User Story 1

- [x] T008 [US1] Create `static/src/views/restricted_task_list.js`: define `RestrictedTaskListController extends ListController`, set up the `notification` service, and override `openRecord(record, {force, newWindow})`. When `record.data.is_expanded_access_task` is true, call `this.props.selectRecord(record.resId, {activeIds, force, newWindow})`, where `activeIds` holds only the loaded rows whose `data.is_expanded_access_task` is true (FR-001, FR-005). Register it as `registry.category("views").add("serichai_restricted_task_list", {...listView, Controller: RestrictedTaskListController})` (contracts §1).
- [x] T009 [US1] In `views/project_task_views.xml`, record `view_task_list_restricted`: add `js_class="serichai_restricted_task_list"`, `create="0"` and `delete="0"` to the root `<list>` (FR-006, research.md Decision 2)

**Checkpoint**: Pinned rows open, edits save through spec 006's existing write rule, and create and delete stay hidden or refused.

---

## Phase 4: User Story 2 - Tasks from other projects stay closed (Priority: P1)

**Goal**: Non-pinned rows are muted and can't be opened by click, URL, pager or mail link.

**Independent Test**: Click a muted row to see the warning, then paste its `/odoo/project.task/<id>` URL to get an access error (quickstart M1, M6, M7).

### Tests for User Story 2

- [x] T010 [P] [US2] Add `test_restricted_user_form_load_denied_outside_pinned_project` in `tests/test_access_restriction.py`, checking that under the `web_read` request stub, `web_read` on `task_target` raises `AccessError`
- [x] T011 [P] [US2] Add `test_restricted_user_list_read_unaffected_by_form_guard` in `tests/test_access_restriction.py`, checking that under a `web_search_read` request stub, `web_search_read([], …)` returns both `task_target` and `task_pinned` (FR-007)

### Implementation for User Story 2

- [x] T012 [US2] In `static/src/views/restricted_task_list.js` `openRecord`: when `record.data.is_expanded_access_task` is falsy, call `this.notification.add(_t("You can only open tasks of the project allowed for your role."), {type: "warning"})` and return without navigating (FR-002)
- [x] T013 [US2] In `views/project_task_views.xml`, record `view_task_list_restricted`: add `decoration-muted="not is_expanded_access_task"` to the root `<list>` (FR-003)
- [x] T014 [US2] In `models/project_task.py`, add `_is_restricted_form_load()`. It returns False if `env.su`, if there is no `odoo.http.request`, if the user lacks `serichai_project_security.group_project_task_list_only`, or if the user has `project.group_project_user`. Otherwise it returns `request.params.get('model') == self._name and request.params.get('method') == 'web_read'` (contracts §3, research.md Decision 3).
- [x] T015 [US2] In `models/project_task.py`, override `web_read(specification)` to raise `AccessError(self.env._("You can only open tasks of the project allowed for your role."))` when `_is_restricted_form_load()` is true and any record has `not is_expanded_access_task`, and otherwise return `super().web_read(specification)` (FR-004). Add the `AccessError` and `request` imports.

**Checkpoint**: The client and the server both refuse non-pinned tasks, and the list contents are unchanged.

---

## Phase 5: User Story 3 - Everyone else and every existing restriction is unaffected (Priority: P2)

**Goal**: Regular Project users and every existing restriction behave exactly as before.

**Independent Test**: The existing test suite passes unchanged, and the control user can open any task (quickstart M9).

### Tests for User Story 3

- [x] T016 [P] [US3] Add `test_project_user_form_load_unaffected` in `tests/test_access_restriction.py`, checking that under the `web_read` request stub, `control_user` can `web_read` on `task_target` without error (FR-008)
- [x] T017 [US3] Run the full module suite on a throwaway DB as described in quickstart.md §1, and confirm the pre-existing tests (menus, Tags column, stage filter, write limited to the pinned project, create and unlink refused, property access) still pass (SC-004). Result: 32/32 passed, 0 failed.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 [P] Update the help text in `models/res_config_settings.py` (`serichai_expanded_access_project_id`) and `views/res_config_settings_views.xml` to say the task form can be opened "from All Tasks or the project menu" (FR-010)
- [x] T019 [P] Update the `description` in `__manifest__.py` and the comment above `view_task_list_expanded_access` in `views/project_task_views.xml`, so they no longer say the project menu is the only place a form can be opened
- [x] T020 [P] Add a **serichai_project_security** entry under "Custom addon architecture" in the top-level `CLAUDE.md`. It currently documents only `serichai_project_mo` and `serichai_inventory`. Cover: the restricted role; the pinned project setting (`is_expanded_access_task`); the two menus (All Tasks, Project); the `serichai_restricted_task_list` js_class; and the `web_read` guard keyed on the top-level RPC method. Point to specs 001, 006 and 007.
- [x] T021 Mark the superseded assumption in `serichai-odoo/specs/006-product-dev-task-access/spec.md` (Assumptions: "still list-only there, no form") with a note pointing to spec 007
- [x] T022 Deploy to `serichai-db` with `-u serichai_project_security --stop-after-init` (quickstart.md §2), then restart the server and hard-refresh the browser. Done 2026-10-03: upgraded cleanly to 19.0.1.1.0 with no errors or warnings. A smoke check in `odoo-bin shell` on real data confirmed the JS is in `web.assets_backend`, "Product Development" is pinned, and for restricted-only user `demo` the pinned task loads (1) while the other listed task is refused (1)
- [x] T025 Fix bug found in walkthrough (2026-10-03): opening a pinned task failed with "Failed to read field project.task.role_ids". The default task form reads relational fields on models the role had no ACL for. Added read-only ACLs for `group_project_task_list_only` on `project.model_project_role` and `project.model_project_task_recurrence` in `security/ir.model.access.csv`, and added `test_restricted_user_can_read_every_field_of_task_form` in `tests/test_access_restriction.py`. Tests: 33/33 pass. Deployed to `serichai-db`. This also fixes the same latent failure in spec 006's Project menu form.
- [x] T023 Run the manual walkthrough M1–M9 in quickstart.md §3 as a restricted user and as a regular Project user, and record the results in this file. 2026-10-03: the walkthrough found the `role_ids` access error, fixed in T025. After the fix, the user confirmed the behaviour in the browser ("Look good now").
- [x] T024 Commit the changes in the `serichai-odoo/` git repo (module plus `specs/007-all-tasks-pinned-open/`), with no AI co-author or attribution lines (CLAUDE.md)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: depends on Phase 1. It blocks US1 and US2.
- **US1 (Phase 3)** and **US2 (Phase 4)**: each depends on Phase 2. **Release them together.**
  US1 alone would let a muted row open a form that the server then refuses (an error dialog
  instead of a clean warning). US2 alone would block every row, which is the old behaviour.
- **US3 (Phase 5)**: verification only. Run it after US1 and US2.
- **Polish (Phase 6)**: T022 → T023 → T024 must run in that order, after Phases 3–5.

### Within stories

- The JS file is shared by T008 and T012, and `project_task_views.xml` by T003, T004, T009 and T013. Edits to the same file run one after another.
- The test tasks T005–T007, T010, T011 and T016 all live in `tests/test_access_restriction.py`. They are marked [P] because they are independent methods that can be drafted in parallel, but they must be merged into the file one at a time.

### Parallel opportunities

```text
# After Phase 2, these touch different files and can proceed in parallel:
T008 (restricted_task_list.js)   T014+T015 (models/project_task.py)   T018 (settings help)
```

---

## Implementation Strategy

### MVP

Phases 1 + 2 + 3 + 4 together are the minimum releasable unit, because US1 and US2 are both P1
and depend on each other for a clean user experience. Phase 5 is the regression gate before
deploying.

### Remaining work

None. Spec closed 2026-10-03.

---

## Notes

- Total: 25 tasks, all done (T025 was added for the bug found in the walkthrough).
- **Known follow-up (not in scope)**: timesheets are enabled on the pinned project. Once a timesheet line exists on a pinned task, the form reads `account.analytic.line.employee_id` (`hr.employee`), which this role can't read, and the form will fail for the role. Recommended fix: hide the Timesheets tab for restricted-only users. Don't grant `hr.employee` read access, because it exposes private HR data.
- The JS controller has no automated test. If regressions become a concern, add an `HttpCase` tour as a follow-up.
