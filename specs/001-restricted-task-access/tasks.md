---

description: "Task list template for feature implementation"
---

# Tasks: Restricted "All Tasks" Access (serichai_project_security)

**Input**: Design documents from `/specs/001-restricted-task-access/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/module-interface.md, quickstart.md (all present)

**Tests**: Included, bundled into each implementation task rather than split out separately — write
the test method(s) first, confirm they fail, then implement. `contracts/module-interface.md`'s
verification contract is the source of truth for what each test asserts.

**Organization**: Tasks are grouped by user story (from `spec.md`). Each task below is intentionally
coarse-grained — a full unit of work (test + implementation + upgrade + validate) rather than one
file per task — to keep the task count manageable for a small, single-developer addon.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Every file path is relative to the repository root
  (`/home/odoo/serichai-odoo`) unless stated otherwise

## Path Conventions

Single Odoo addon module at `serichai-odoo/serichai_project_security/`, sibling to the existing
`serichai_project_mo` addon, per `plan.md`'s Project Structure.

---

## Phase 1: Setup

- [X] T001 Scaffold the addon at `serichai-odoo/serichai_project_security/`: `__init__.py` (`from . import models`), `__manifest__.py` (`depends: ["project"]`, `data` listing all five data files below, `installable: True`, `application: False`, matching `serichai_project_mo`'s manifest style), `models/__init__.py` (`from . import project_task`) with a stub `models/project_task.py` (`ProjectTask` inheriting `project.task`, no overrides yet), and minimal valid stub files `security/security_groups.xml`, `security/ir.model.access.csv` (header row only), `security/ir_rule.xml`, `views/project_task_views.xml`, `views/project_menus.xml`. Install and confirm it loads cleanly: `cd odoo && python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db -i serichai_project_security --stop-after-init`.

**Checkpoint**: Module installs with no functional behavior yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Define the restricted role and its base access in `serichai-odoo/serichai_project_security/security/security_groups.xml` (`group_project_task_list_only`, name "Task List Viewer (Production Planning Only)", no `privilege_id` — matches the technical/hidden-group pattern used by `hr_recruitment.group_applicant_cv_display` in this Odoo 19 build, where the old Odoo 18 `category_id` field no longer exists on `res.groups`; `implied_ids` → `base.group_user` so assigning this one group is sufficient for internal-user login) and `serichai-odoo/serichai_project_security/security/ir.model.access.csv` (read-only rows `access_project_task_restricted` on `project.task` and `access_project_project_restricted` on `project.project`, `perm_read=1`, all other perms `0`) — per `data-model.md` "Restricted Role", `contracts/module-interface.md` rows 1–3.
- [X] T003 Grant the restricted role visibility of the Project app icon: in `serichai-odoo/serichai_project_security/views/project_menus.xml`, add `<record id="project.menu_main_pm" model="ir.ui.menu">` with `group_ids eval="[(4, ref('group_project_task_list_only'))]"` (additive only — per `research.md` §2). Then scaffold `serichai-odoo/serichai_project_security/tests/__init__.py` and `tests/test_access_restriction.py`: a `TransactionCase` with `setUp()` creating a `วางแผนการผลิต` stage + task, a decoy stage + task, a restricted test user (only `group_project_task_list_only`), and a control test user (`project.group_project_user`). Upgrade the module (`-u serichai_project_security --stop-after-init`) and confirm the group exists and the app icon is visible to the restricted user.

**Checkpoint**: Foundation ready — role exists, base read access granted, app icon reachable, test scaffold in place.

---

## Phase 3: User Story 1 - View only my relevant tasks (Priority: P1) 🎯 MVP

**Goal**: A user holding only the restricted role can open Tasks → All Tasks and see exclusively tasks in the "วางแผนการผลิต" stage.

**Independent Test**: Assign the restricted role to a test user (and only that role); confirm opening All Tasks shows only `วางแผนการผลิต`-stage tasks, from any project.

- [X] T004 [US1] In `tests/test_access_restriction.py`, add `test_restricted_user_sees_only_target_stage_tasks` (restricted user's `search([])` returns only `วางแผนการผลิต`-stage tasks; contract check #2) and confirm it fails. Then implement: stage-filter rule `rule_task_stage_restricted` in `serichai-odoo/serichai_project_security/security/ir_rule.xml` — **must be a global rule with a conditional `domain_force`** (`[('stage_id.name', '=', 'วางแผนการผลิต')] if user.has_group('serichai_project_security.group_project_task_list_only') else [(1, '=', 1)]`, no `groups` field), not a naively group-scoped one — see research.md §5 for why a group-scoped rule silently leaks other-stage tasks (it gets OR'd with `base.group_user`'s own core `project` rules instead of restricting on top of them); the restricted list view shell `view_task_list_restricted` (inherits `project.view_task_tree2`) and action `action_task_all_restricted` (`view_mode="list"`, same domain, `group_ids` = the group) in `serichai-odoo/serichai_project_security/views/project_task_views.xml`; and the menu entry `menu_task_all_restricted` (parent `project.menu_project_management`) in `serichai-odoo/serichai_project_security/views/project_menus.xml`. Upgrade, confirm the test passes, and manually validate `quickstart.md` steps 1–4a.

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Cannot see or reach anything beyond the permitted list (Priority: P1)

**Goal**: The restricted-role user cannot open task forms (by click or direct link), cannot switch views, and cannot see Projects/Reporting/Configuration or the original All Tasks menu.

**Independent Test**: As the restricted test user, attempt each forbidden action (click a row, switch view, direct-link to a task form, open the three hidden top menus) and confirm each is blocked.

- [X] T005 [US2] Before writing anything, verify the *current* live-database `group_ids` on `project.menu_projects` and `project.menu_project_report` (queried directly via `psql` against `serichai-db`'s `ir_ui_menu`/`ir_ui_menu_group_rel` tables — equivalent to the Developer Mode → Settings → Technical → User Interface → Menu Items check). **Result**: both `menu_projects` and `menu_project_report` currently have **no groups at all** (empty — visible to any internal user who can reach the parent), and so does `menu_project_management_all_tasks`; `menu_project_config` is confirmed `Administrator` (`project.group_project_manager`) only, matching the prior assumption exactly. No other/unexpected groups found — safe to proceed with the whitelist as planned in T006.
- [X] T006 [US2] In `tests/test_access_restriction.py`, add `test_restricted_user_form_access_denied` (`get_view(view_type='form')` raises `AccessError`; contract check #1) and `test_restricted_user_hidden_menus_not_visible` (`menu_projects`/`menu_project_report`/`menu_project_config`/`menu_project_management_all_tasks` absent from the restricted user's menu tree; contract check #3), and confirm both fail. Then implement: `get_view()` override in `serichai-odoo/serichai_project_security/models/project_task.py` (raise `AccessError` for `view_type == 'form'` when the user holds only the restricted group, following the `hr_recruitment` precedent per `research.md` §4); `open_form_view="false"` xpath on `view_task_list_restricted`'s root in `views/project_task_views.xml`; and, using the whitelist confirmed in T005, explicit-whitelist `group_ids` overrides (`(6, 0, [...])`) for `project.menu_projects`, `project.menu_project_report`, `project.menu_project_management_all_tasks` (→ `group_project_manager` + `group_project_user`) and `project.menu_project_config` (→ `group_project_manager` only) in `views/project_menus.xml`. Upgrade, confirm both tests pass, and manually validate `quickstart.md` steps 4b–4d and 6.

**Checkpoint**: User Stories 1 AND 2 both work independently — the restricted role now has a hard, enforced boundary.

---

## Phase 5: User Story 3 - Simplified list without irrelevant columns (Priority: P3)

**Goal**: The restricted All Tasks list does not show a Tags column.

**Independent Test**: As the restricted test user, open All Tasks and confirm the Tags column is absent.

- [X] T007 [US3] In `tests/test_access_restriction.py`, add `test_restricted_list_hides_tags_column` (`get_view(view_type='list')`'s `arch` has `tag_ids` with `column_invisible="1"`; contract check #6) and confirm it fails. Then add `<xpath expr="//field[@name='tag_ids']" position="attributes"><attribute name="column_invisible">1</attribute></xpath>` to `view_task_list_restricted` in `serichai-odoo/serichai_project_security/views/project_task_views.xml`. Upgrade, confirm the test passes, and manually validate `quickstart.md` step 4.

**Checkpoint**: All three functional user stories (US1, US2, US3) are independently functional.

---

## Phase 6: User Story 4 - No impact on existing users and other apps (Priority: P1)

**Goal**: Prove, not just assume, that nothing built in US1–US3 changed behavior for anyone outside the new restricted role.

**Independent Test**: As an existing normal Project user (`project.group_project_user`, not the new role), confirm all previously available menus, stages, view switchers, Tags column, and task-opening behavior are unchanged.

- [X] T008 [US4] In `tests/test_access_restriction.py`, add `test_existing_project_user_unaffected`: as the control test user, assert `get_view(view_type='form')` succeeds, `search([])` returns tasks from all stages, `menu_projects`/`menu_project_report`/`menu_project_management_all_tasks` are visible (note: `menu_project_config` is correctly **excluded** from this check — it was already Administrator-only before this module per T005, so a plain `group_project_user` control user correctly does not see it; that's pre-existing behavior, not a regression), and `tag_ids` is not `column_invisible` on the standard `project.view_task_tree2` view (contract check #7) — passed with **no implementation changes**, confirming US1–US3 were properly group-scoped. Automated part done (5/5 tests passing). Manual spot-check of `quickstart.md` step 8 (log in as a Sales/Inventory/etc. user in a browser) was **not performed** in this session — no browser access available; left for the user to verify before production rollout.

**Checkpoint**: All four user stories independently verified — the additive-only guarantee (FR-009) is now backed by a passing regression test, not just design intent.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T009 [P] Run the full automated suite (`--test-enable --test-tags=/serichai_project_security -u serichai_project_security --stop-after-init`) and walk through the full `quickstart.md` manual checklist (steps 1–8) once as the restricted test user and once as the control user; record results. **Automated suite: 0 failed, 0 error(s) of 5 tests** (final clean run). **Manual browser checklist: not performed** in this session (no browser/UI access) — automated tests cover the equivalent assertions at the ORM level (steps 3–6, 9 per the Testing Checklist in the original source doc), but steps requiring actual login-as-different-users in a browser (visual sidebar/menu confirmation, clicking through the UI) are left for the user to walk through before production rollout. See quickstart.md for the exact steps.
- [X] T010 [P] Add a short note in `serichai-odoo/serichai_project_security/__manifest__.py`'s `description` (or a `README.md` alongside it) that hiding the Dashboards app icon is **out of scope** by design (per `research.md` §6, `spec.md` Assumptions) so it isn't mistaken for a bug later. Then do a final review pass of every row in `contracts/module-interface.md`'s "New records" and "Existing records" tables against the actual files, confirming no extra/missing XML IDs and that every "replace" `group_ids` matches what T005 found. **Result**: all 7 "New records" rows and all 5 "Existing records" rows verified against the actual XML/CSV/Python files — exact match, no drift.

---

## Phase 8: User Story 5 - All Tasks is the default landing page (Priority: P1)

*(Added 2026-08-06 amendment — see spec.md User Story 5 / FR-011 / FR-012 / SC-008 / SC-009.)*

**Goal**: Clicking the Project app icon lands the restricted-role user directly on All Tasks, with
only "All Tasks" shown in the top menu bar — no intermediate Tasks/Projects navigation.

**Independent Test**: As the restricted test user, click the Project app icon from the launcher
(not a submenu) and confirm All Tasks loads immediately with the top menu bar showing only "All
Tasks". As a control (`project.group_project_user`), confirm the default landing page (Projects)
and full four-tab menu bar are unchanged.

- [X] T011 [US5] Live-DB-verified (2026-08-06, see `contracts/module-interface.md`) that
  `project.menu_project_management` ("Tasks", id 296) and `project.menu_project_management_my_tasks`
  ("My Tasks", id 297) both had no `group_ids` set — the gap causing the extra navigation step. In
  `serichai-odoo/serichai_project_security/views/project_menus.xml`: added an explicit-whitelist
  `group_ids` override on `project.menu_project_management` (→ `[project.group_project_manager,
  project.group_project_user]`, same pattern as the T006 overrides — hiding it also hides its
  "My Tasks" child for the restricted role, since visibility is inherited from the parent);
  reparented `menu_task_all_restricted` from `project.menu_project_management` to
  `project.menu_main_pm` and changed its `sequence` from `1` to `0`, promoting it to a top-level tab
  that resolves as the default landing page. Confirmed no other top-level child of `menu_main_pm`
  visible to the restricted role has a lower sequence (see contracts doc).

  **Gap discovered mid-implementation and fixed in the same task**: this database has "Use Stages on
  Project" (`project.group_project_stages`) implied by `base.group_user` — every internal user,
  including the restricted role, holds it automatically. `project/models/ir_ui_menu.py`'s
  `_load_menus_blacklist()` blacklists the plain `menu_projects` (the one T006 had whitelisted) for
  anyone holding `group_project_stages`, and instead renders its twin,
  `project.menu_projects_group_stage` — which had never been touched by T006 and still carried only
  its native `groups="project.group_project_stages"`, so the restricted role could still see a
  "Projects" tab despite T006's intent. Fixed by adding the same explicit-whitelist `group_ids`
  override to `project.menu_projects_group_stage`. This also exposed that `_visible_menu_ids()` (the
  method T006's own tests use) doesn't walk the ancestor chain the way the web client's `load_menus()`
  does, so it can't actually prove a submenu like "My Tasks" is unreachable once its parent is
  hidden — added `test_restricted_user_menu_bar_shows_only_all_tasks`, which calls `load_menus()`
  directly and asserts `menu_main_pm`'s only visible child is `menu_task_all_restricted`, plus
  `test_restricted_user_all_tasks_is_default_landing_menu` (lowest-sequence check) and extended
  `test_existing_project_user_unaffected` with a `load_menus()`-based check that a control user still
  sees a Projects tab (either twin) and Tasks.

  Upgraded the module (`-u serichai_project_security --stop-after-init`) and re-verified via direct
  `psql` query against `serichai-db`'s `ir_ui_menu`/`ir_ui_menu_group_rel` that: `menu_task_all_restricted`
  now has `parent_id = menu_main_pm.id` and `sequence = 0`; `menu_project_management` and
  `menu_projects_group_stage`'s groups are now exactly Administrator+User; the restricted group's
  app-icon grant on `menu_main_pm` and all prior T005/T006 whitelists are untouched. Ran the full
  automated suite: **0 failed, 0 error(s) of 7 tests** (5 pre-existing + 2 new). No changes to
  `ir_rule.xml`, the Tags column xpath, the `get_view()` override, or `ir.model.access.csv`, per the
  update's explicit "do not touch" scope. Manual browser walk-through of `quickstart.md` steps 3a/6/7
  not performed in this session (no browser access) — left for the user before rollout.

**Checkpoint**: All five user stories (US1–US5) independently functional; the restricted role's
navigation surface is now exactly one tab, and that tab is the default landing page.

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002 → T003)** → **US1 (T004)** → **US2 (T005 → T006)** → **US3 (T007)** → **US4 (T008)** → **Polish (T009, T010)** → **US5 (T011, 2026-08-06 amendment)**.
- T011 depends on T006 (it further restricts a menu whose whitelist pattern T006 established) but is otherwise independent of T007–T010.
- US2 and US3 both extend `view_task_list_restricted` (created in T004), so they must run in that
  order to avoid `arch` merge conflicts in `views/project_task_views.xml`.
- US4 (T008) inherently depends on US1–US3 being implemented, since it verifies their *absence* of
  side effects.
- T009 and T010 (Polish) have no dependency on each other — run in parallel.

### Parallel Opportunities

Given the coarse granularity of these tasks, most work within a task is inherently sequential
(test → implement → validate on the same files). The only true parallel opportunity is:

- **T009** and **T010** — different concerns (test/validation run vs. documentation), no shared files.

---

## Implementation Strategy

### MVP First

1. T001 (Setup) → T002–T003 (Foundational) → T004 (US1).
2. **STOP and VALIDATE**: run T004's test, then `quickstart.md` steps 1–4a.
3. This is a demoable MVP — the restricted user can see their relevant tasks — but **not**
   production-safe yet: the form-open block and menu-hiding (US2) aren't in until T006.

### Incremental Delivery

1. T001–T003 → foundation ready.
2. T004 (US1) → validate → MVP demoable.
3. T005–T006 (US2) → validate → security boundary enforced; safe to consider for production rollout.
4. T007 (US3) → validate → cosmetic polish.
5. T008 (US4) → regression test proves nothing else broke; safe to merge/deploy with confidence.
6. T009–T010 (Polish) → final documentation and full-suite confirmation.

---

## Notes

- No test currently exists in `serichai_project_mo` or `serichai_inventory` — this module
  establishes the first automated-test pattern in this repo; keep `test_access_restriction.py`
  as the template for any future addon's test suite.
- T005's live-database check gates T006's menu `group_ids` overwrite — do not skip it or hardcode a
  guess, per `research.md` §2 and `contracts/module-interface.md`'s "Contract rule".
- Hiding the Dashboards app is intentionally not a task in this file — see T010 and `research.md`
  §6 for why, and don't reintroduce it without a spec/plan update.
- Commit after each task; stop at any checkpoint to validate a story independently before moving on.
