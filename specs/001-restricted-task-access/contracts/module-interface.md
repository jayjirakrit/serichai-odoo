# Contract: `serichai_project_security` Module Interface

This module has no HTTP/API surface. Its "contract" is the set of external identifiers (XML IDs)
and access-control records it creates, and the existing Odoo records it modifies. Downstream work
(tasks.md, tests, manual verification) should validate against this table rather than against
implementation prose.

## New records this module creates (stable external IDs)

| XML ID | Model | Purpose |
|---|---|---|
| `serichai_project_security.group_project_task_list_only` | `res.groups` | The restricted role. `privilege_id = project.res_groups_privilege_project`, `sequence = 5`, so it shows as a selectable option in the "Project" dropdown on Settings → Users → Access Rights, below "User"/"Administrator" and mutually exclusive with them. |
| `serichai_project_security.access_project_task_restricted` | `ir.model.access.csv` row | Grants the role `perm_read=1` on `project.task`, all writes denied. |
| `serichai_project_security.access_project_project_restricted` | `ir.model.access.csv` row | Grants the role `perm_read=1` on `project.project`, all writes denied. |
| `serichai_project_security.rule_task_stage_restricted` | `ir.rule` | **Global** rule (no `groups`) with conditional `domain_force`: restricts visible `project.task` rows to `stage_id.name = 'วางแผนการผลิต'` for members of the role, no-op (`[(1,'=',1)]`) for everyone else. Must be global, not group-scoped — see research.md §5. |
| `serichai_project_security.view_task_list_restricted` | `ir.ui.view` | Inherits `project.view_task_tree2`; hides `tag_ids` column (`column_invisible=1`), sets `open_form_view="false"`. |
| `serichai_project_security.action_task_all_restricted` | `ir.actions.act_window` | List-only (`view_mode="list"`) action on `project.task`, domain-filtered to the stage above, `group_ids` limited to the role. |
| `serichai_project_security.menu_task_all_restricted` | `ir.ui.menu` | The role's own "All Tasks" entry, pointing at the action above. **Amended 2026-08-06**: parent changed from `project.menu_project_management` to `project.menu_main_pm` (promoted to a top-level tab, sibling of Projects/Tasks/Reporting/Configuration) and `sequence` changed from `1` to `0`, so it resolves as the lowest-sequence visible top-level menu for the restricted role — Odoo's default-landing-page rule. |

## Existing records this module modifies (`group_ids` field only — no other fields touched)

| XML ID (owned by `project`) | Field changed | New value (this module's `data`) |
|---|---|---|
| `project.menu_main_pm` | `group_ids` | Existing groups **+** `serichai_project_security.group_project_task_list_only` (additive `(4, ref(...))`) |
| `project.menu_projects` | `group_ids` | Replaced with `[project.group_project_manager, project.group_project_user]` exactly (verify current value matches before shipping — see research.md §2) |
| `project.menu_project_report` | `group_ids` | Replaced with `[project.group_project_manager, project.group_project_user]` exactly (verify current value matches before shipping — see research.md §2) |
| `project.menu_project_config` | `group_ids` | Replaced with `[project.group_project_manager]` exactly (matches confirmed current value) |
| `project.menu_project_management_all_tasks` | `group_ids` | Replaced with `[project.group_project_manager, project.group_project_user]` exactly |
| `project.menu_project_management` (the "Tasks" top menu) | `group_ids` | **Added 2026-08-06**: Replaced with `[project.group_project_manager, project.group_project_user]` exactly — live-DB-verified empty (no groups) before this change, per T005-style check re-run 2026-08-06 (see research note below); closes the gap where the restricted role could otherwise still see "Tasks" (and its "My Tasks" child, itself also groups-empty) once its own `menu_task_all_restricted` moved out from under it. |
| `project.menu_projects_group_stage` (twin of `menu_projects`, shown instead of it when the user holds `project.group_project_stages` — see `project/models/ir_ui_menu.py`'s `_load_menus_blacklist()`) | `group_ids` | **Added 2026-08-06**: Replaced with `[project.group_project_manager, project.group_project_user]` exactly. **Gap found during this amendment**: `project.group_project_stages` is implied by `base.group_user` in this database (a project-settings toggle applied org-wide), so every internal user — including the restricted role — holds it, meaning this twin menu (not the plain `menu_projects` T006 had whitelisted) is the one that actually renders, and it had never been restricted. Native `groups="project.group_project_stages"` alone does not exclude the restricted role here since they hold that group too. |

**Contract rule**: every "replace" row above must reproduce the *live database's actual current
value* for that field, plus explicitly excluding the new role — never blindly narrow to just the
two listed groups if the live value turns out to include more. This is a pre-merge verification
gate, not a design choice (see research.md §2's carried-forward verification task).

**2026-08-06 live-DB re-verification** (default-landing-page amendment): queried `ir_ui_menu` /
`ir_ui_menu_group_rel` directly against `serichai-db`. Confirmed `project.menu_main_pm` (id 293,
sequence 70) has no parent; `project.menu_project_management` ("Tasks", id 296, sequence 2, parent
293) had **no groups at all** prior to this change — matches the assumed empty baseline, safe to
apply the whitelist above. Also confirmed no other menu under `menu_main_pm` remains visible to
the restricted role with sequence lower than `menu_task_all_restricted`'s new `sequence="0"`:
`menu_projects`(1)/`menu_project_report`(99)/`menu_project_config`(100) are already
whitelisted away, and `menu_projects_group_stage`(1) is gated by `project.group_project_stages`,
which the restricted role does not hold.

## Explicitly out of scope for this module (do not implement without a new spec/plan change)

- Anything touching `spreadsheet_dashboard.spreadsheet_dashboard_menu_root` or any other
  Dashboards-app record — user-approved scope reduction, see research.md §6.
- Any field, view, or access change to models other than `project.task`, `project.project`, and the
  `ir.ui.menu` records listed above.
- Any change to `project.group_project_user` or `project.group_project_manager` definitions
  themselves (only their appearance in the `group_ids` whitelist of specific menus is touched, and
  only to preserve — never reduce — their existing access).

## Verification contract (how to check compliance)

For a test user holding **only** `group_project_task_list_only`:

1. `env['project.task'].get_view(view_type='form')` MUST raise `AccessError`.
2. `env['project.task'].search([])` MUST return only records where `stage_id.name ==
   'วางแผนการผลิต'`.
3. `env['ir.ui.menu'].search([('id', '=', ref('project.menu_projects'))])` filtered through
   `_visible_menu_ids()` (or equivalent) for this user MUST be empty, likewise for
   `menu_project_report`, `menu_project_config`, `menu_project_management_all_tasks`, and
   (**added 2026-08-06**) `menu_project_management` ("Tasks") and
   `menu_project_management_my_tasks` ("My Tasks").
4. `env['ir.ui.menu'].search([('id', '=', ref('project.menu_main_pm'))])` filtered the same way
   MUST include the menu (app icon visible).
4a. *(Added 2026-08-06.)* Among the top-level children of `menu_main_pm` visible to this user,
    `menu_task_all_restricted` MUST have the lowest `sequence` (i.e. `0`), so it resolves as the
    default landing page.
4b. *(Added 2026-08-06.)* `env['ir.ui.menu'].with_user(<restricted user>).load_menus(False)` —
    the method the web client actually uses to build the top menu bar, which (unlike
    `_visible_menu_ids()`) drops any menu whose ancestor chain up to its app root isn't itself
    visible — MUST return `menu_main_pm.id` with `children == [menu_task_all_restricted.id]`
    exactly, and MUST NOT contain `menu_project_management` ("Tasks") or
    `menu_project_management_my_tasks` ("My Tasks") as keys.
5. The `action_task_all_restricted` action's `view_mode` MUST equal exactly `"list"` (no other view
   types present).
6. The rendered arch for `view_task_list_restricted` MUST contain `tag_ids` with
   `column_invisible="1"`.

For a test user holding `project.group_project_user` (unaffected control case):

7. All of 1–6 above MUST behave as they did before this module was installed (form opens, all
   stages visible, all four menus visible, Kanban/etc. view modes available, Tags column visible).
