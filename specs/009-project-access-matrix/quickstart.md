# Quickstart: validating 009-project-access-matrix

## 1. Automated tests (throwaway DB)

```bash
cd odoo && source ../.venv/bin/activate
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai_pacc_test_tmp -i serichai_project_access --without-demo=all \
  --test-enable --test-tags /serichai_project_access --stop-after-init --no-http
dropdb serichai_pacc_test_tmp
```
Expected: 0 failed, 0 errors; module installs with no warnings.

## 2. Manual walkthrough (rehearsal DB copy via `scripts/restore_odoo_local.sh`)

1. As a project manager: Project > Configuration > Project Access Group > New. Name
   "Manufacturing", pick a test user group, Project tab: add line (Project A, Read, list only,
   two stages, hidden property "Cost"); add line (Project B, Write).
2. As a member (log in, hard refresh): only menus **All Tasks** and **Project**.
3. Project menu: cards for A and B only; open A: kanban shows only the two stages.
4. All Tasks: rows of A greyed; click -> warning, no form. Open a B task: form opens, edit and
   save work, Delete is absent/refused. "Cost" never shown on A tasks.
5. Add the member to a second department granting A with open detail: A tasks now open and
   "Cost" is visible only if the second line hides nothing (merge, FR-018).
6. Remove the member from the group: menus and tasks return to the normal view on next load.
7. Negative checks: open a task of A by URL (`/odoo/tasks/<id>`) -> access error; RPC edit of an
   A task -> AccessError; project manager unaffected.

## 3. Migration rehearsal (FR-023..FR-026, SC-005)

Never run this on `serichai-db`. Use a restored copy (`scripts/restore_odoo_local.sh`, restore
into a throwaway database such as `serichai_pacc_reh`) and drop it afterwards.

Commands below run from `odoo/` with `A="--addons-path=addons,../muk_web_theme,../serichai-odoo -d <rehearsal-db>"`.

1. **Before snapshot** (old module only). In `odoo-bin shell $A`, for each user of the old role
   (and one project user and one user with an extra property group), record what
   `serichai_project_access.tests.test_migration.snapshot(env, user, projects)` returns:
   visible task ids, editable task ids, visible property labels per task, Project menu entries.
   Dump to JSON (`snapA.json`). Always `env.cr.rollback()` between users.
2. **Install**: `python3 odoo-bin $A --stop-after-init -i serichai_project_access`. Check the log
   line `Migration: N user(s) moved to Production Planning (migrated), M project(s) granted
   read-only` and that there is no `Migration: production stages not found` warning (if there
   is, create or rename the stages, then drop the profile and group and reinstall).
3. **Idempotence**: `-u serichai_project_access` again; there must still be one profile
   "Production Planning (migrated)".
4. **Coexistence snapshot** (`snapB.json`): both modules active, results are AND-ed, so it must
   equal `snapA.json` for every old-role user.
5. **Uninstall the old module** (rehearsal DB only): in a shell,
   `env['ir.module.module'].search([('name','=','serichai_project_security')]).button_immediate_uninstall()`.
6. **After snapshot** (`snapC.json`, new module alone) and compare with `snapA.json` per user:
   `visible`, `editable` and `menus` must be equal for every old-role user (SC-005). Differences
   in `properties` are expected and must be reviewed (see "Known differences").
7. **Leftover check** (FR-025). Expected: no `ir.model.data` rows for `serichai_project_security`;
   table `project_task_property_access` gone; no old group, rules, ACL, views or menus; the six
   core menus have core groups: `project.menu_main_pm` = Project manager + Project user + our
   control group, `menu_projects_group_stage` = `project.group_project_stages`,
   `menu_projects`, `menu_project_report`, `menu_project_management` and
   `menu_project_management_all_tasks` = no groups. **One manual step**: the system parameter
   `serichai_project_security.expanded_access_project_id` survives the uninstall (Odoo does not
   remove parameters it does not own); delete it in Settings > Technical > System Parameters.
8. Sign off, then update `CLAUDE.md` and the constitution addon list (T040).

### Rehearsal result (2026-10-10, throwaway DB, synthetic data)

Fixture: pinned project, two other projects, 3 tasks each (two production stages, one other),
properties "Cost" (finance group only) and "Note" (old role only), users: role member, role member
plus the finance group, plain project user.

| Check | Result |
|---|---|
| Hook on install | profile created, 2 users moved, 2 projects as Read/list line, pinned project as Write line |
| Old-role users: visible, editable, menus, A vs B vs C | identical |
| Role member, properties | identical while both modules coexist (B); after uninstall (C) "Cost" is also shown on the pinned project (Write lines show every property) |
| Role member + finance group, properties | C hides "Cost" on the two non-pinned projects (the finance group is not copied into the migrated department; risk R3) |
| Project user, properties | A/B: nothing visible (old rules hide any property whose rule excludes the user); C: everything visible. The new module does not replicate that rule for non-role users |
| Project user, menus | the duplicate "Projects" entry disappears (the old module's rewrite of the core menus is undone) |
| Uninstall `serichai_project_security` | no xml ids, table, groups, rules, ACL, views or menus left; six core menus match core values; only the system parameter remains (step 7) |

### Known differences to accept or fix before go-live

1. Property hiding on the pinned (Write) project: old role hid restricted labels there; the new
   Write line shows all properties (FR-012).
2. Users with extra property groups (risk R3): hide-list is computed for the bare old role.
3. Property rules no longer apply to users outside the migrated department.
