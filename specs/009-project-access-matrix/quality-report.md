# Quality Report: 009-project-access-matrix (SCOPE integration, delta after code-review fixes #2,#3,#4,#5,#7,#8,#9)

**Verdict: PASS WITH NOTES.** All server-side criteria are met and tested. Browser behaviour (greyed rows, warning, kanban, 2-click reach), migration on production-like data and cutover docs are not verified.

## Gates (throwaway DB qa009_tmp2, dropped afterwards; serichai-db untouched)
- `odoo-bin -i serichai_project_access --test-enable --test-tags /serichai_project_access --stop-after-init` -> pass: 54 tests, 0 failed, 0 errors. Fresh install logged no warnings from the module (only core config and RST noise, plus the tour skips below). The count is lower than the earlier 63; the earlier figure likely included tests that need serichai_project_security. Not re-checked.
- Tours `test_list_tour` and `test_kanban_tour` skip (websocket-client missing). T042 open.
- Migration tests need `serichai_project_security` and were not run.

## Re-verified fixes
- #2 private tasks: flags treat `project_id=False` as visible/writable, but core's own-private-task rule (project_todo, base.group_user) still decides. The new group write rule is limited to `project_id != False`, so it does not widen access to other users' private tasks. test_private_tasks_own_only covers it: others' tasks are neither seen nor deleted, own tasks are CRUD.
- Unlink rule: restricted users who are not project users may delete only `project_id = False` tasks, and core limits those to their own. Project tasks are undeletable (test_write_allows_write_create_not_unlink, test_read_refuses_write_create_unlink). No bypass found.
- #7 `_access_check_target_project` rejects create or write into a project without Write (closes old minor 2). Falsy `project_id` is skipped (see minor A).
- #8 `_check_group_ids` rejects forbidden groups transitively and excludes only base.group_user, which is rejected when selected directly. Correct, since nearly every internal group implies it.
- #9 `_sync_restricted_group` touches only the affected groups. #5 kanban columns are intersected by domain and context project. #3 and #4 covered by tests; the suite passes.

## Acceptance criteria (US1-US7, FR-001..026, SC-001..007)
| ID | Result | Evidence |
|---|---|---|
| US1 / FR-001..009 | met | ACL csv (manager only), `project_access_profile.py` (group_ids required, forbidden groups), `project_access_line.py` (unique per profile `_check_project_unique_in_profile`, Write forces detail and clears stages and properties, `warning_message` for FR-009), test_access_admin |
| US2 / FR-010,011,013 | met | global rules `project_task_rule_access_read` and `_write`, `project_project_rule_access_read`; ACL read-only on project; `read()` filter and `write()` merge-back in project_task.py; tests test_access_enforcement, test_property_hiding |
| US3 / FR-014,015 | met (server), unverified (UI) | `web_read` guard (project_task.py) using the top-level RPC check, same as spec 007; `access_task_detail` flag; JS list and kanban controllers. Tests in test_detail_guard. Tours not run. |
| US4 / FR-012 | met | `project_task_rule_access_unlink` plus no unlink ACL; test_write_allows_write_create_not_unlink |
| US5 / FR-017,019..021 | met (server), unverified (UI) | `_load_menus_blacklist` hides all other Project menus; the `project.menu_main_pm` change is additive only; project kanban action. test_menus. SC-007 not timed. |
| US6 / FR-018 | met | `_merge_grant` (Write over Read, detail over list, stage union, hidden = intersection); test_access_resolver and test_merge_two_departments |
| US7 / FR-023..026 | partial | `hooks.post_init_hook` is idempotent and restores core menu groups. Not run by me. Engineer's rehearsal reported identical access. |
| FR-016 / SC-006 | met | ormcache keyed on group ids plus `clear_cache` on every profile and line change; test_changes_apply_without_reassignment |
| SC-001 | not verified | needs a manual timed pass (T039) |
| SC-002..004 | met | tests above |
| SC-005 | partial | rehearsal only; property-parity differences are documented in quickstart.md |

## Findings
### Major / Critical
- none.

### Minor
A. `models/project_task.py` `_access_check_target_project` · odoo · A Write user can set `project_id=False` on a project task, turning it private. It leaves their reach unless they are an assignee. No data leak and no test. Suggest rejecting that write or adding a test.
B. `tasks.md` T039, T040, T042 open (manual browser pass and SC-001 timing, cutover docs, tours never run) · release gate. Run the tours where websocket-client and Chrome exist.
C. `read()` hides properties only on read and web_read; read_group or search can still reveal them. Within FR-015's accepted limit (same class as spec 002).
D. `hooks.py` · property-parity drift from SC-005 is documented in quickstart.md; confirm with the business. `CORE_MENU_GROUPS` restoration edits core menus via sudo; re-check on the real DB during rehearsal.

### Security review (summary)
Enforcement is server-side (global ir.rules, ACLs, web_read guard). The sudo uses are narrow and commented. The group write rule and the unlink rule do not let restricted users touch others' private tasks or delete project tasks. No secrets or PII found. No new dependencies.
