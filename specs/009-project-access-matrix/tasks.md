# Tasks: Configurable Project Access by Department

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [design.md](./design.md), [data-model.md](./data-model.md), [research.md](./research.md), [contracts/module-interface.md](./contracts/module-interface.md), [quickstart.md](./quickstart.md)
**Area**: `odoo` (fullstack). Module root `M` = `serichai-odoo/serichai_project_access/`.
**Tests**: included (Constitution Principle IV; list in design.md "Specs must assert").
**Gate per task batch**: `cd odoo && ../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d <test-db> --test-enable --stop-after-init -u serichai_project_access`

## Format: `- [ ] T### [P?] [US?] Description with file path`

---

## Phase 1: Setup

- [X] T001 Create module skeleton: `M/__init__.py` (imports `models`, `hooks`), `M/__manifest__.py` (depends `project`; data list in load order: security groups, ACL csv, rules, views, menus; `post_init_hook: post_init_hook`; assets for `static/src/views/*.js`), empty `M/models/__init__.py`, `M/tests/__init__.py`, `M/hooks.py` with a stub `post_init_hook(env)`.
- [X] T002 [P] Create control group record in `M/security/serichai_project_access_groups.xml`: `serichai_project_access_group_restricted` implying `base.group_user` only (not `project.group_project_user`), privilege Project, help text "assigned automatically; do not assign by hand" (data-model "Control group").

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 [P] Implement `project.access.profile` in `M/models/project_access_profile.py` per data-model.md: `name` Char required; `active` Boolean default True; `group_ids` M2M `res.groups` required, rel `project_access_profile_group_rel`; `line_ids` O2M `project.access.line` (cascade); non-stored computed `user_ids` (members of `group_ids` incl. implied) and `project_ids` (all lines' projects, for list tags). Add `@api.constrains('group_ids')` rejecting forbidden groups `base.group_user`, `base.group_portal`, `base.group_public`, `base.group_system`, `project.group_project_user`, `project.group_project_manager` (design snippet `_check_group_ids`). Register in `M/models/__init__.py`.
- [X] T004 [P] Implement `project.access.line` in `M/models/project_access_line.py` per data-model.md: `profile_id` M2O required ondelete cascade; `project_ids` M2M `project.project` required, rel `project_access_line_project_rel`; `access_level` Selection `read`/`write` default `read`; `task_access` Selection `list`/`detail` default `list`, computed stored `readonly=False` forced to `detail` for write (FR-008); `stage_ids` M2M `project.task.type` rel `project_access_line_stage_rel` (empty = all stages); `hidden_property_names` Text; `stages_exhausted` Boolean stored default False; sequence handle. Constraint: same project at most once per profile (FR-007, design `_check_project_unique_in_profile`). Onchange/clear `stage_ids` and `hidden_property_names` when `access_level == 'write'` (ignored by resolver). Register in `M/models/__init__.py`.
- [X] T005 Implement the resolver in `M/models/res_users.py`: `Grant` namedtuple, `_norm`, `@tools.ormcache('self.id', 'self._get_group_ids()') _get_project_access`, `_merge_grant` exactly per design.md (returns `None` for unrestricted users or holders of `project.group_project_user`; FR-017, FR-018). Respect `stages_exhausted` (grant no stage) and skip inactive projects. Comment every `sudo()`. Register in `M/models/__init__.py`.
- [X] T006 Add `_sync_restricted_group` and `_after_change` to `M/models/project_access_profile.py` (design snippet): link/unlink the control group in `implied_ids` of department groups, idempotent diff, active profiles only; override `create`, `write` (when `group_ids`/`active` change) and `unlink` to call `_after_change` (sync + `registry.clear_cache()`). Add the same cache clearing to `create/write/unlink` of `M/models/project_access_line.py`, and to `project.project` `active` writes in `M/models/project_project.py`. Depends on T003-T005.
- [X] T007 [P] Add ACL in `M/security/ir.model.access.csv`: profile and line full CRUD for `project.group_project_manager`; for `serichai_project_access_group_restricted`: `project.task` read/write/create, `project.project`, `project.role`, `project.task.recurrence` and `project.task.type` read only.
- [X] T008 Add `stages_exhausted` ondelete hook: in `M/models/project_access_line.py` (or new `M/models/project_task_type.py`, then import in `__init__.py`) override `project.task.type.unlink` to set `stages_exhausted=True` on lines whose entire `stage_ids` is being deleted; reset it when an admin writes `stage_ids` (data-model `stages_exhausted`).
- [X] T009 [P] Write resolver and profile tests in `M/tests/test_access_resolver.py`: single grant unchanged; merge cases FR-018 (write over read, detail over list, stage union with "all", hidden intersection); ormcache invalidation on group add/remove, line edit, profile archive, project archive; forbidden groups rejected; restricted group added/removed on profile create/archive/delete; project user/manager returns `None`; `stages_exhausted` grants no stage.

**Checkpoint**: configuration data and the resolver work; nothing is enforced yet.

---

## Phase 3: User Story 1 - Administrator defines a department's project access (P1)

**Goal**: managers create and maintain departments, lines and warnings (FR-001..FR-009).
**Independent test**: a manager creates "Manufacturing" with one Read line; list shows name and project tags; User tab lists members; warnings appear; duplicate project refused; a non-manager cannot open the screens.

- [X] T010 [US1] Add computed `warning_message` to `M/models/project_access_line.py` (design `_compute_warning_message`): hidden names matching no property in the line's projects (case-insensitive, trimmed) and projects whose visibility is not `employees`/`portal` (FR-009).
- [X] T011 [US1] Create admin views in `M/views/project_access_profile_views.xml`: list (Department `name` + `project_ids` as `many2many_tags`, FR-002), form with notebook tabs **User** (read-only `user_ids`) and **Project** (editable `line_ids` list: project tags, access level, task access; line form popup with warning alert, `stage_ids` tags, `hidden_property_names`, group invisible when `access_level == 'write'`) (FR-004..FR-006, FR-008), search view, and action.
- [X] T012 [US1] Add menu `project_access_profile_menu` "Project Access Group" under `project.menu_project_config`, `groups=project.group_project_manager`, in `M/views/project_access_menus.xml`; add the file to the manifest.
- [X] T013 [P] [US1] Tests in `M/tests/test_access_resolver.py` (or new `M/tests/test_access_admin.py`): manager can CRUD profile/line, non-manager (project user and restricted user) gets AccessError, duplicate project in one profile refused, write line forces `detail`, warning text for unknown property name and `followers` visibility.

---

## Phase 4: User Story 2 - Read access with stage and property limits (P1)

**Goal**: restricted members see only granted projects and allowed stages, and cannot see hidden properties (FR-010, FR-011, FR-013, FR-016, FR-017).
**Independent test**: Read line with stages and a hidden property: ungranted project and its tasks invisible everywhere; only allowed stages; hidden property absent; Read user cannot edit/create/delete.

- [X] T014 [US2] Add searchable computed fields `access_can_read` and `_search_access_can_read` in `M/models/project_project.py` (design snippet; `Domain.TRUE` for unrestricted users).
- [X] T015 [US2] Add `access_task_visible/writable/detail` computes, `_access_domain`, `_search_access_task_*` (using one `_search_bool` helper) in `M/models/project_task.py` per design.md.
- [X] T016 [US2] Add global rules in `M/security/project_project_security.xml` (read rule on `access_can_read`, no write/create/unlink rule) and `M/security/project_task_security.xml` (`project_task_rule_access_read` perm_read only on `access_task_visible`; `project_task_rule_access_write` perm_write+perm_create on `access_task_writable`; `project_task_rule_access_unlink` using the group test per design.md). Names `<model>_rule_access_<perm>`. Add to the manifest. Early spike: confirm create/write checks work with non-stored search fields (risk R1).
- [X] T017 [US2] Override `read` in `M/models/project_task.py` to drop hidden properties per task project, matching `string` trimmed and case-folded (design snippet), and the defensive `write` that merges stored hidden values back (research D7).
- [X] T018 [US2] Override `_read_group_stage_ids` in `M/models/project_task.py` so disallowed stages do not appear as empty kanban columns (design snippet).
- [X] T019 [P] [US2] Tests in `M/tests/test_access_enforcement.py`: ungranted project/task invisible via `search`, `read_group`, direct `read`; stage filter (allowed only, empty = all, `stages_exhausted` = none, kanban columns); Read refuses write/create/unlink and project write; changes apply to existing group members without re-assignment (FR-016).
- [X] T020 [P] [US2] Tests in `M/tests/test_property_hiding.py`: hidden property absent in `read`/`web_read` for Read user, present for Write and unrestricted users; stored hidden value survives a save; name matching case/space insensitive.

---

## Phase 5: User Story 3 - Task access level: list only or open detail (P1)

**Goal**: list-only tasks cannot be opened by any route; open-detail tasks can (FR-014, FR-015, FR-020).
**Independent test**: list-only task row greyed with warning on click, `web_read` refused; open-detail task opens; list searches keep working.

- [X] T021 [US3] Add `_is_restricted_form_load` (spec 007 logic, test `user._get_project_access() is not None`) and the `web_read` override raising `AccessError` when `access_task_detail` is false, in `M/models/project_task.py` (design snippet). Reuse the pattern of `serichai_project_security/models/project_task.py`.
- [X] T022 [P] [US3] Create `M/static/src/views/access_task_list.js` (`AccessTaskListController.openRecord`: warn and return when `!record.data.access_task_detail`, pager `activeIds` filtered to openable rows; registry key `serichai_access_task_list`) per design snippet.
- [X] T023 [P] [US3] Create `M/static/src/views/access_task_kanban.js` (same logic on `KanbanController`, no `force` param, key `serichai_access_task_kanban`).
- [X] T024 [US3] Create task views/actions in `M/views/project_task_views.xml`: restricted list view (`js_class="serichai_access_task_list"`, `create="0"`, `delete="0"`, loads `access_task_detail`, `decoration-muted` for non-openable rows, no Tags column) and restricted kanban view (`serichai_access_task_kanban`, `create="0"`); window actions `project_task_action_access_all` and `project_task_action_access_project`. Add to the manifest.
- [X] T025a [P] [US3] Add an `HttpCase` tour (or OWL unit test) in `M/tests/test_access_tour.py` and `M/static/tests/` covering the list and kanban controllers: non-openable row is greyed, click shows the warning and does not navigate, pager skips non-openable rows (Constitution Principle IV).
- [X] T025 [P] [US3] Tests in `M/tests/test_detail_guard.py`: list-only refused and open-detail allowed under patched `request` top-level `project.task.web_read`; `web_search_read` and `web_read_group` still work; project users exempt; Write implies detail.

---

## Phase 6: User Story 4 - Write access (P2)

**Goal**: Write lines allow editing and creating tasks, never deleting (FR-012).
**Independent test**: Write user edits/creates tasks in the project, sees all stages and properties; delete refused; no Write on other projects.

- [X] T026 [US4] Verify and, if needed, fix create/write behaviour of `project_task_rule_access_write` for Write projects (create task with `project_id` of a Write project succeeds, Read project fails) in `M/security/project_task_security.xml` and `M/models/project_task.py`.
- [X] T027 [P] [US4] Tests in `M/tests/test_access_enforcement.py`: write/create allowed only with Write; `unlink` refused for Write users on tasks and projects; Write ignores stage and hidden-property settings.

---

## Phase 7: User Story 5 - Restricted navigation and project dashboard (P2)

**Goal**: restricted users see only All Tasks and Project; Project lists accessible projects and opens a project's tasks by allowed stage (FR-019..FR-021, SC-007).
**Independent test**: restricted user sees exactly two Project menus, reaches a granted project's tasks in at most 2 clicks; a project user in a department sees only the standard menus.

- [X] T028 [US5] Implement `_load_menus_blacklist` in `M/models/ir_ui_menu.py` per design (unrestricted users: blacklist the two own menus; restricted: blacklist everything under `project.menu_main_pm` except the own menus). Register in `M/models/__init__.py`.
- [X] T029 [US5] Add menus `menu_task_all_access` (All Tasks, action `project_task_action_access_all`) and `menu_project_access` (Project, action showing the stock project kanban) in `M/views/project_access_menus.xml`; add `M/views/project_project_views.xml` with the restricted project action/kanban (no create, project cards).
- [X] T030 [US5] Override `action_view_tasks` in `M/models/project_project.py` to return the restricted task action for restricted users (design snippet), keeping stock behaviour otherwise.
- [X] T031 [P] [US5] Tests in `M/tests/test_access_enforcement.py` (or `M/tests/test_menus.py`): restricted user's menu set equals All Tasks + Project; project user in a department sees standard menus only; `action_view_tasks` returns the restricted action; Project lists only granted projects.

---

## Phase 8: User Story 6 - Several departments merge (P2)

**Goal**: users in several departments get the most permissive combination (FR-018, SC-004).
**Independent test**: user in two departments gets Write over Read, detail over list, stage union, hidden intersection.

- [X] T032 [US6] Add end-to-end merge tests in `M/tests/test_access_enforcement.py` using a user in two profiles on the same project (visibility, writability, detail, stages, properties), plus a user whose second department is added/removed with immediate effect.
- [X] T033 [US6] Fix any resolver/rule gaps found by T032 in `M/models/res_users.py` and `M/models/project_task.py`.

---

## Phase 9: User Story 7 - Migrate current behaviour and retire the old role (P3)

**Goal**: reproduce the old role, move its users, then remove the old module without leftovers (FR-023..FR-026, SC-005).
**Independent test**: on a restored DB copy, install the new module, compare each former role user before/after, uninstall the old module, menus unchanged.

- [X] T034 [US7] Implement `post_init_hook` in `M/hooks.py` per design (idempotent, skips on fresh install or when the migrated profile exists): create the migrated group (implying `base.group_user`), pinned project from `serichai_project_security.expanded_access_project_id` as Write line, all other non-template projects as Read/list line with the 4 Thai production stages and hidden property names derived from `project.task.property.access`, move old-group users, restore the six core menus' `group_ids` to core values. Warn if stages are missing.
- [X] T035 [US7] Wire the hook in `M/__manifest__.py` (`post_init_hook`) and ensure it runs after data files load.
- [X] T036 [P] [US7] Tests in `M/tests/test_migration.py`: profile, lines, users moved, hidden names, idempotent rerun, core menu groups restored, fresh install does nothing.
- [X] T037 [US7] Write rehearsal procedure in `serichai-odoo/specs/009-project-access-matrix/quickstart.md` (if not already complete): restore DB copy via `scripts/restore_odoo_local.sh`, install, per-user before/after comparison (tasks, menus, actions), uninstall old module, verify no leftover rules or menus (FR-025, FR-026).

---

## Phase 10: Polish and cross-cutting

- [X] T037a [US7] Uninstall `serichai_project_security` on the rehearsal DB copy and verify no old rules, groups or menu restrictions remain and the six core menus match core values (FR-025). Files: none (manual, results noted in `serichai-odoo/specs/009-project-access-matrix/quickstart.md`).
- [X] T038 [P] Run the full test suite and fix failures: `-u serichai_project_access --test-enable` (gate command above); confirm no edits to `odoo/` or `muk_web_theme/`.
- [ ] T039 Manual browser pass (also time an admin setting up one department grant, target under 5 minutes, SC-001) with a restricted user per quickstart.md (greyed rows and warning, kanban stages, missing properties, write denied on Read project, 2-click reach, SC-007).
- [ ] T040 Cutover docs: amend `CLAUDE.md` (replace `serichai_project_security` section with `serichai_project_access`) and run `/speckit-constitution` (PATCH) to update the Technology Standards addon list; record in the cutover PR (design open question 5).

---

## Dependencies and order

- Phase 1 -> Phase 2 (blocks all). T006 needs T003-T005; T008 needs T004.
- US1 (Phase 3) needs Phase 2. US2 (Phase 4) needs Phase 2 (can run parallel with US1). US3 needs US2 (T015). US4 needs US2 rules. US5 needs US3 views (T024) and T014. US6 needs US2 and US4. US7 needs US1-US6 complete (models, rules, menus) and the old module present for rehearsal.
- Polish after all stories.

## Parallel examples

- Phase 2: T003, T004 and T007 touch different files and can run together; T005 after them.
- US3: T022 and T023 (two JS files) in parallel, then T024.
- Tests marked [P] in different files can run alongside implementation of the next story.

## Implementation strategy

- **MVP**: Phases 1-5 (US1 + US2 + US3, all P1): configurable departments, Read with stage/property limits, list-only vs detail guard. Stop and validate with quickstart before continuing.
- Then US4 (Write), US5 (navigation), US6 (merge hardening), and finally US7 (migration and removal) with a rehearsal on a DB copy before go-live.

## Phase 11: Convergence

- [X] T041 CRITICAL: add a one-line `# sudo: <why it is safe>` comment above each uncommented `sudo()` call in `serichai-odoo/serichai_project_access/hooks.py` (config parameter read, group creation, `ir.model.data` creation) per Constitution III (contradicts)
- [ ] T042 Install `websocket-client` in `.venv` (or use a browser-capable environment), run `serichai_access_task_list_tour` and `serichai_access_task_kanban_tour` from `serichai-odoo/serichai_project_access/static/tests/tours/access_task_list_tour.js` via `tests/test_access_tour.py` on a throwaway DB, and fix the selectors and menu navigation until both pass, per FR-014, US3, US5 (partial)
- [X] T043 [P] Document the extra rule `project_task_rule_access_group_write` (why core's private-task group rule requires it) in `serichai-odoo/specs/009-project-access-matrix/design.md`, `research.md` and `contracts/module-interface.md`, per plan: Complexity Tracking (partial)
- [ ] T044 Before go-live: re-enable `'post_init_hook': 'post_init_hook'` in `serichai-odoo/serichai_project_access/__manifest__.py` (currently commented out on purpose for the dev database) and re-run `tests/test_migration.py` with `serichai_project_security` installed, per FR-023, FR-024 (partial)
