# Quickstart: Validating `serichai_project_security`

## Prerequisites

- `.venv` active, PostgreSQL reachable, `serichai-db` exists (see repo root `CLAUDE.md`).
- A `project.task.type` record named exactly `วางแผนการผลิต` already exists in `serichai-db`, with
  at least one `project.task` in that stage (for meaningful manual verification).
- Module is scaffolded at `serichai-odoo/serichai_project_security/` per `data-model.md` and
  `contracts/module-interface.md`.

## Install / upgrade the module

```bash
source .venv/bin/activate
cd odoo
python3 odoo-bin \
  --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-db \
  -i serichai_project_security \
  --stop-after-init
```

Re-run with `-u serichai_project_security` (instead of `-i`) for subsequent iterations.

## Automated verification

```bash
cd odoo
python3 odoo-bin \
  --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-db \
  --test-enable --test-tags=/serichai_project_security \
  -u serichai_project_security \
  --stop-after-init
```

Expected: all test cases implementing the six verification-contract checks in
`contracts/module-interface.md` pass, in particular:

- `AccessError` raised on `get_view(view_type='form')` for a restricted-only user.
- `search([])` on `project.task` as that user returns only `วางแผนการผลิต`-stage tasks.
- The unaffected-control-case test (`project.group_project_user`) shows no behavior change.

## Manual validation (backend UI)

1. As an administrator, go to **Settings → Users**, create or edit a test user:
   - Assign group **"Task List Viewer (Production Planning Only)"**.
   - Confirm this user does **not** hold `project.group_project_user` or
     `project.group_project_manager` (remove if present — required per spec Assumptions).
2. Log in as that test user.
3. Confirm the **Project** app icon is visible in the sidebar.
3a. *(Added 2026-08-06.)* Click the **Project** app icon directly (not a submenu) — confirm the
    **All Tasks** list loads immediately, not the Projects Kanban board and not an intermediate
    Tasks menu.
4. Open **All Tasks** (now the app's default/only top-level tab for this role):
   - Confirm only tasks in the `วางแผนการผลิต` stage appear.
   - Confirm no Tags column is present.
   - Confirm no Kanban/Calendar/Pivot/Graph/Activity view-switcher icons appear.
   - Click a task row — confirm nothing opens.
5. Copy a task's direct form URL (e.g. from an admin session) and paste it while logged in as the
   test user — confirm an access-denied error is shown, not the form.
6. Confirm the Project app's top menu shows **only** "All Tasks" — Projects, Tasks (and its My
   Tasks child), Reporting, and Configuration are all absent. *(Amended 2026-08-06: previously
   "Tasks" was the one visible top menu with All Tasks nested under it; now All Tasks itself is the
   only top-level tab and the default landing page — see step 3a.)*
7. As a control, log in as an existing normal Project user (`project.group_project_user`, not the
   new role) and confirm nothing changed: default landing page is still Projects, all stages
   visible, Kanban switcher present, Tags column present, tasks open normally, and all four top
   menus (Projects, Tasks, Reporting, Configuration) present.
8. Confirm no other app's behavior changed for any user (spot-check Sales, Inventory, Invoicing,
   Manufacturing, Employees for a user who has those roles).

## Note on stage-grouped Projects (2026-08-06)

This database has "Use Stages on Project" enabled, which every internal user (including the
restricted role) holds automatically. Odoo swaps in a second "Projects" menu
(`project.menu_projects_group_stage`) for such users instead of the plain one — both are now
hidden for the restricted role, but if this setting is ever toggled off, double-check the top menu
bar again rather than assuming the fix still applies unchanged.

## Known limitation to note during validation

The Dashboards app icon will **still be visible** to the restricted-role test user — this is an
intentional, user-approved scope reduction (see `research.md` §6 and `spec.md` Assumptions), not a
defect. Do not fail validation on this point; it is tracked as a documented follow-up outside this
module's scope.
