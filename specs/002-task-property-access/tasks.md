---

description: "Task list for Task Property Group Visibility"
---

# Tasks: Task Property Group Visibility

**Input**: Design documents from `/specs/002-task-property-access/`

All paths relative to repo root, inside `serichai-odoo/serichai_project_security/`.

## Phase 1: Setup

- [X] T001 [P] Create `models/project_task_property_access.py` skeleton (`_name = 'project.task.property.access'`) and register it in `models/__init__.py`.
- [X] T002 [P] Add `'views/project_task_property_access_views.xml'` to the `data` list in `__manifest__.py`.

## Phase 2: Foundational (blocks all stories)

- [X] T003 In `models/project_task_property_access.py`: add fields `property_string` (Char, required), `group_ids` (Many2many res.groups, required), `active` (Boolean, default True); add a `models.Constraint` unique on `property_string` (this Odoo build no longer supports `_sql_constraints`); add `@api.constrains('group_ids')` rejecting an empty set. (Depends on T001.)
- [X] T004 [P] Add access rows to `security/ir.model.access.csv` granting `project.group_project_manager` full CRUD on `project.task.property.access`.

**Checkpoint**: rules can be created/validated via the ORM.

## Phase 3: US1 (P1) — Restrict a property to specific groups 🎯 MVP

- [X] T005 [US1] In new `tests/test_task_property_access.py` (TransactionCase, style of `tests/test_access_restriction.py`): test that a permitted-group user sees a restricted property via `read(['task_properties'])` and a non-permitted user doesn't.
- [X] T006 [US1] In `models/project_task.py`, add a `read()` override (next to the existing `get_view()` override) that strips `task_properties` entries whose `'string'` matches an active rule the current user has no permitted group for. Confirm T005 passes. (Depends on T003.)

## Phase 4: US2 (P2) — Unrestricted properties unaffected

- [X] T007 [US2] In `tests/test_task_property_access.py`: test that unrelated properties on a task with one restricted property are identical for both users, and that with zero rules configured, all users get identical `task_properties`. (Depends on T006.)

## Phase 5: US3 (P3) — Admin manages rules

- [X] T008 [P] [US3] Create `views/project_task_property_access_views.xml`: list + form view (`property_string`, `group_ids`), action, and a menu under `project.menu_project_config` restricted to `project.group_project_manager`. (Depends on T003, T004.)
- [X] T009 [P] [US3] In `tests/test_task_property_access.py`: test non-manager gets `AccessError` on create, empty `group_ids` raises `ValidationError`, duplicate `property_string` raises a validation/integrity error. (Depends on T003, T004.)

## Phase 6: Polish

- [X] T010 Run `--test-enable --stop-after-init -u serichai_project_security` (full suite). All 8 new tests pass; only pre-existing, unrelated `test_restricted_list_hides_tags_column` still fails (disabled xpath predating this feature - see plan.md's follow-up note). Manual browser walkthrough of `quickstart.md` not performed (no browser available in this environment) - automated tests cover the same scenarios (steps 5-8). (Depends on T005-T009.)

## Dependencies

Setup → Foundational → {US1 → US2} and US3 in parallel → Polish.

## MVP

T001-T006 delivers the core restriction (rules manageable via ORM/technical UI before T008's screen exists).
