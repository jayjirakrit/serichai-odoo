# Quickstart / Validation Guide: spec 007

See [contracts/module-interface.md](./contracts/module-interface.md) §4 for the full behaviour matrix.

## Prerequisites

- `.venv` activated and PostgreSQL reachable.
- The module code from this feature is in `serichai-odoo/serichai_project_security/` (version 1.1.0).

## 1. Automated tests (throwaway DB — does not touch `serichai-db`)

```bash
cd odoo && source ../.venv/bin/activate
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai_psec_test_tmp -i serichai_project_security --without-demo=all \
  --test-enable --test-tags /serichai_project_security --stop-after-init --no-http
dropdb serichai_psec_test_tmp
```

**Expected**: `0 failed, 0 error(s)` for all tests (32 at the time of writing). The log line
`duplicate key value violates unique constraint "project_task_property_access_property_string_uniq"`
is expected: it comes from `test_duplicate_property_string_rejected` (spec 002).

## 2. Deploy to the working database

```bash
cd odoo && source ../.venv/bin/activate
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db \
  -u serichai_project_security --stop-after-init
./run_odoo.sh   # from repo root
```

Hard-refresh the browser so the new asset bundle loads.

## 3. Manual walkthrough

Setup, as administrator:
1. Pin a project in Settings > Project > Task List Viewer Role (for example "Product Development").
2. Make sure there is a test user with **only** the "Task List Viewer (Production Planning Only)" role.
3. Make sure **All Tasks** will show at least one task from the pinned project and at least one
   production-stage task from another project.

As the restricted user:

| # | Step | Expected | Spec |
|---|---|---|---|
| M1 | Open **Project** app → **All Tasks** | Pinned-project rows look normal, other rows are muted, and there is no **New** button | FR-003, US2-1 |
| M2 | Click a pinned-project row | The task form opens | FR-001, US1-1 |
| M3 | Edit a field (for example a property or the stage) and save | Saved, and the chatter logs the change | FR-006, US1-2 |
| M4 | Use the pager (next/previous) | Moves only through pinned-project rows | FR-005, US1-3 |
| M5 | Look for Delete in the gear menu / try to create | Not offered, or refused | FR-006, US1-4 |
| M6 | Go back and click a muted row | A warning toast appears and nothing opens | FR-002, US2-2 |
| M7 | Paste `/odoo/project.task/<id of a muted task>` | An access error appears and no task details are shown | FR-004, US2-3 |
| M8 | Clear the pinned project (as admin), then reload **All Tasks** as the restricted user | All rows are muted and every click shows the warning | Edge: no project pinned |

As a regular Project user:

| # | Step | Expected | Spec |
|---|---|---|---|
| M9 | Open any task from Tasks / All Tasks, or by direct URL | Opens normally | FR-008, US3-1 |
