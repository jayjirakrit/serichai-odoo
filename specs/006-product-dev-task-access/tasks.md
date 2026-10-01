---

description: "Task list for expanded task access on the Product Development project"
---

# Tasks: Expanded Task Access for Product Development Project

**Input**: Design documents from `specs/006-product-dev-task-access/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — the addon already has an automated `TransactionCase` suite
(`tests/test_access_restriction.py`) covering this exact role, and the plan/quickstart
explicitly extend it; new behavior gets the same treatment.

**Organization**: Tasks are grouped by user story (US1 = P1, US2 = P2) per spec.md.

## Path Conventions

All paths are relative to `serichai-odoo/serichai_project_security/` (the addon being
extended) unless otherwise noted.

---

## Phase 1: Setup

**Purpose**: Create the new files this feature needs before they're filled in.

- [X] T001 [P] Create empty `models/res_config_settings.py` with the module's standard header/imports (`from odoo import fields, models`) and an empty `ResConfigSettings(models.TransientModel)` class stub inheriting `res.config.settings`
- [X] T002 [P] Create empty `views/res_config_settings_views.xml` with a bare `<odoo>` root, ready for the settings form inheritance in T009

**Checkpoint**: New files exist; nothing wired up yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The security plumbing both user stories depend on — the pinned-project config
value, the field that resolves it per task, and the access/rule changes that will govern write
access. No user-visible behavior yet.

**⚠️ CRITICAL**: Both user stories require this phase complete first.

- [X] T003 In `models/project_task.py`, add `@api.model def _get_expanded_access_project_id(self)` returning `int(self.env['ir.config_parameter'].sudo().get_param('serichai_project_security.expanded_access_project_id', 0)) or False`
- [X] T004 In `models/project_task.py`, add the computed+searchable field `is_expanded_access_task = fields.Boolean(compute='_compute_is_expanded_access_task', search='_search_is_expanded_access_task')`, plus `_compute_is_expanded_access_task` (sets `True` iff `task.project_id.id == self._get_expanded_access_project_id()`, guarding against a falsy pinned id) and `_search_is_expanded_access_task(self, operator, value)` (translates `('is_expanded_access_task', '=', True)` / `('=', False)` into a `project_id` domain against the pinned id, or `[('id', '=', False)]` when no project is pinned) — depends on T003
- [X] T005 In `models/res_config_settings.py` (from T001), add `serichai_expanded_access_project_id = fields.Many2one('project.project', string='Expanded-Access Project (Task List Viewer role)', config_parameter='serichai_project_security.expanded_access_project_id')`
- [X] T006 In `views/res_config_settings_views.xml` (from T002), add a `res.config.settings` form-view inheritance that adds the `serichai_expanded_access_project_id` field under a labeled block (e.g. next to the Project settings block), following the standard `res_config_settings_view_form` inheritance pattern
- [X] T007 Update `models/__init__.py` to import `res_config_settings`
- [X] T008 Update `security/ir.model.access.csv`: change `access_project_task_restricted`'s `perm_write` from `0` to `1` (leave `perm_create`/`perm_unlink` at `0`)
- [X] T009 Add a new rule to `security/ir_rule.xml`: `rule_task_write_pinned_project` on `project.task`, `groups` = `group_project_task_list_only`, `perm_read="0"` `perm_write="1"` `perm_create="0"` `perm_unlink="0"`, `domain_force="[('is_expanded_access_task', '=', True)]"` — depends on T004
- [X] T010 Add `views/res_config_settings_views.xml` to the `data` list in `__manifest__.py` — depends on T002

**Checkpoint**: An administrator can pin a project in Settings; `is_expanded_access_task` and the
new `ir.rule` correctly gate `write` at the ORM level for any client (RPC or shell), even though
no UI path to it exists yet. Verifiable directly via `env['project.task'].with_user(restricted_user).write(...)` in an Odoo shell per quickstart.md §3.3–3.4.

---

## Phase 3: User Story 1 - Restricted user works tasks in Product Development (Priority: P1) 🎯 MVP

**Goal**: A `group_project_task_list_only` user can open the full task form and edit fields for
tasks in the pinned project, through the normal web client — not just via direct ORM calls.

**Independent Test**: Per spec.md — log in as the restricted user, open a task in the pinned
project, edit and save a field successfully; confirm create/delete are still refused.

### Tests for User Story 1

- [X] T011 [P] [US1] In `tests/test_access_restriction.py`, add a test that pins a test project via the `serichai_project_security.expanded_access_project_id` config parameter, then asserts `env['project.task'].with_user(restricted_user)` can `write()` a field on a task in that project
- [X] T012 [P] [US1] In `tests/test_access_restriction.py`, add a test asserting the same restricted user gets `AccessError` attempting `create()` on `project.task`, and `AccessError` attempting `unlink()` on a task in the pinned project

### Implementation for User Story 1

- [X] T013 [US1] In `models/project_task.py`, relax `get_view`'s `AccessError` for `view_type == 'form'` so it no longer unconditionally blocks the group (see research.md Decision 3 — the real boundary is the write ACL from Phase 2, not this method) — depends on T004
- [X] T014 [US1] In `views/project_task_views.xml`, add `view_task_list_expanded_access` (`ir.ui.view`, `list`, `inherit_id="project.view_task_tree2"`, `mode="primary"`) — same base as `view_task_list_restricted` but WITHOUT an `open_form_view="false"` override, so rows stay clickable
- [X] T015 [US1] In `views/project_task_views.xml`, add `action_task_product_development_restricted` (`ir.actions.act_window`, `res_model="project.task"`, `view_mode="list"`, `view_id` = T014's view, `domain="[('is_expanded_access_task', '=', True)]"`, `group_ids` limited to `group_project_task_list_only`) — depends on T004, T014
- [X] T016 [US1] In `views/project_task_views.xml`, add `menu_task_product_development_restricted` (`ir.ui.menu`, sibling of `menu_task_all_restricted` under `project.menu_main_pm`, `action` = T015's action, `groups` limited to `group_project_task_list_only`) — depends on T015

**Checkpoint**: User Story 1 fully functional and independently testable — a restricted user
can find, open, and edit "Product Development" tasks through the standard UI; create/delete
remain refused everywhere.

---

## Phase 4: User Story 2 - Existing restrictions remain intact everywhere else (Priority: P2)

**Goal**: Confirm the expanded access is exactly and only as wide as the pinned project — no
regression to any existing restriction, and no silent widening if the project is renamed or a
same-named project appears later.

**Independent Test**: Per spec.md — run the existing menu/column/form-denial regression checks
against a task in a non-pinned project; confirm they still pass unchanged.

### Tests for User Story 2

- [X] T017 [P] [US2] In `tests/test_access_restriction.py`, add a test asserting `env['project.task'].with_user(restricted_user).write(...)` on a task in a project OTHER than the pinned one raises `AccessError` — depends on Phase 2
- [X] T018 [P] [US2] In `tests/test_access_restriction.py`, add a test for FR-004: rename the pinned project, then assert the same restricted user can still write to its tasks (grant follows the record, not the name) — depends on Phase 2
- [X] T019 [P] [US2] In `tests/test_access_restriction.py`, add a test for FR-003/Edge Case: create a second, unrelated project also named "Product Development" (or any name matching the pinned one) and assert the restricted user CANNOT write to its tasks — only the originally-pinned record's id qualifies — depends on Phase 2
- [X] T020 [US2] In `tests/test_access_restriction.py`, update/replace `test_restricted_user_form_access_denied` (which currently asserts `get_view(view_type='form')` always raises) to instead assert: (a) `view_task_list_restricted` ("All Tasks") still carries `open_form_view="1"`'s negation i.e. `column`/attribute check unchanged, and (b) attempting to `write()` a task outside the pinned project still raises `AccessError` — depends on T013, T017

**Checkpoint**: All pre-existing regression tests (menus, Tags column, landing menu,
non-restricted control user) plus the new project-scoping tests pass together.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency pass.

- [X] T021 [P] Update `__manifest__.py` `description` to mention the pinned-project expanded-access exception, alongside the existing read-only/list-only summary
- [X] T022 Run the full `tests/` suite via `--test-enable --stop-after-init -u serichai_project_security` and confirm all pre-existing tests (menus, landing menu, Tags column, control user) still pass alongside the new ones
- [ ] T023 Walk through `quickstart.md` end-to-end manually in a running Odoo instance (pin a project via Settings, verify UI behavior for both the pinned and a non-pinned project as the restricted user)

---

## Phase 6: Pinned-project visibility + Kanban stage columns (2026-10-01, FR-007/FR-008)

**Purpose**: Make every task of the pinned project visible regardless of stage, and open it as
a Kanban board with one column per stage (research.md Decision 5).

- [X] T024 Fix `_search_is_expanded_access_task` in `models/project_task.py` for Odoo 19's `in`/`not in` boolean operators
- [X] T025 Exempt pinned-project tasks from the stage filter in `security/ir_rule.xml` (`rule_task_stage_restricted`)
- [X] T026 Add `project.task.action_open_expanded_access_tasks()` and server action `action_server_task_product_development_restricted`; point `menu_task_product_development_restricted` at it
- [X] T027 Switch `action_task_product_development_restricted` to `kanban,list,form` with `view_task_kanban_expanded_access` (no create / column editing) and `view_task_list_expanded_access` (no create/delete)
- [X] T028 Replace the stale `test_restricted_user_sees_all_stage_tasks_while_stage_filter_disabled` with stage-filter tests for both sides; add tests for the action context, Kanban stage columns (empty stage included), and Kanban create/column flags
- [ ] T029 Upgrade `serichai_project_security` on `serichai-db` and walk through the Kanban board as a restricted user (drag a task between columns; confirm no New / column edit controls)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001/T002 create the files T005/T006 fill in) — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion; T020 additionally depends on US1's T013 (the `get_view` change it re-asserts around)
- **Polish (Phase 5)**: Depends on Phases 3 and 4 both being complete

### User Story Dependencies

- **US1 (P1)**: No dependency on US2 — testable purely against Phase 2's ORM-level boundary plus its own view/menu/action additions
- **US2 (P2)**: Mostly regression + boundary-precision tests against Phase 2's mechanism; T020 touches a file US1 also modifies (`project_task.py` / `test_access_restriction.py`) so should land after US1's T013 to avoid re-asserting stale behavior

### Parallel Opportunities

- T001, T002 together (different new files)
- T011, T012 together; T017, T018, T019 together (independent test methods in the same test file — safe to co-author, land as one commit if easier, but logically independent)
- T014 must precede T015, which must precede T016 (same action → menu chain)

---

## Parallel Example: Foundational Phase

```bash
# T001 and T002 (new empty files) can be created together.
# T005 and T006 (filling those two new files) can then proceed together once T001/T002 exist.
# T008 (access CSV) and T009 (ir.rule) touch different files and can proceed together once T004 exists.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational) — the security boundary is fully correct
   and testable via direct ORM calls even before any UI exists.
2. Complete Phase 3 (US1) — the actual user-facing capability (menu, action, list, form access).
3. **STOP and VALIDATE**: run T011/T012, and quickstart.md §1–2, independently.
4. This is a shippable MVP: restricted users can work Product Development tasks; nothing else
   has changed yet from a code perspective (US2's tests only *prove* that, they don't add code).

### Incremental Delivery

1. Setup + Foundational → boundary correct, no UI yet.
2. US1 → the feature is usable end-to-end (MVP).
3. US2 → proves no regression/leakage; safe to treat as a required gate before merging, since it
   is what SC-002/SC-004/SC-005 in spec.md are measured against.
4. Polish → docs + full regression run + manual walkthrough.

---

## Notes

- No task in this feature touches a second addon or the vendored `odoo/` core — everything is
  inside `serichai_project_security`.
- Commit after each phase checkpoint, consistent with the rest of this addon's history (one
  `[ADD]`/`[IMP]` commit per delivered slice).
- Task IDs are sequential across the whole file, not restarted per phase, so they can be
  referenced unambiguously in commits/PRs.
