# Phase 0 Research: Restricted "All Tasks" Access (serichai_project_security)

All findings below were verified directly against the **vendored Odoo 19.0 source** in this
repository (`odoo/addons/project/`, `odoo/odoo/addons/base/`, `odoo/addons/spreadsheet_dashboard/`),
not assumed from the Odoo 18-era source document (`odoo-project-restricted-task-access-spec.md`).
Several details differ from that document; each is called out explicitly.

## 1. Module placement and house style

- **Decision**: New addon lives at `serichai-odoo/serichai_project_security/`, inside the existing
  `serichai-odoo` git repo — the same location as the sibling addon `serichai_project_mo`, and
  already on `run_odoo.sh`'s addons path. No changes to `run_odoo.sh` are needed.
- **Rationale**: Matches existing project convention (per `CLAUDE.md`) and avoids introducing a
  new untracked top-level directory (like `serichai_inventory`, which the addons path does *not*
  include — a trap to avoid repeating).
- **House style observed** (from `serichai_project_mo/__manifest__.py`): manifest keys `name`,
  `summary`, `version` (plain `X.Y.Z`, not Odoo's `19.0.X.Y.Z` convention), `description`,
  `depends`, `data`, `installable`, `author`. No `license` key is present in the existing addon.
  This plan follows the same shape for consistency, and adds `category` and `application: False`
  since this is a technical/security module, not an app.
- **Alternatives considered**: Following the source document's own manifest shape (`version:
  "18.0.1.0.0"`, explicit `license`) was considered, but rejected in favor of matching this repo's
  actual precedent — introducing a new convention in a sibling module would be inconsistent for no
  benefit.

## 2. Menu structure — verified current XML IDs (Odoo 19)

The source document assumed Odoo 18 XML IDs that turned out to still be accurate for some items
but wrong for others. Verified current structure, all in `odoo/addons/project/views/project_menus.xml`:

| Purpose | XML ID (verified) | Notes |
|---|---|---|
| Project app root menu (sidebar icon) | `project.menu_main_pm` | Has `groups="project.group_project_manager,project.group_project_user"` |
| "Projects" top menu | `project.menu_projects` | |
| "Tasks" top menu (parent of All/My Tasks) | `project.menu_project_management` | |
| **"All Tasks" menu item** | `project.menu_project_management_all_tasks` | **Not** `project.menu_project_task_all` as the source doc assumed — that ID does not exist in Odoo 19 |
| "Reporting" top menu | `project.menu_project_report` | |
| "Configuration" top menu | `project.menu_project_config` | Already has `groups="project.group_project_manager"` |
| Existing "All Tasks" action | `project.action_view_all_task` | `view_mode = list,kanban,form,calendar,activity,pivot,graph` |

- **Decision**: Reference the verified IDs above (not the source document's guesses) in
  `views/project_menus.xml`.
- **Critical finding not addressed by the source document**: `project.menu_main_pm` (the Project
  app's sidebar icon itself) is gated to `group_project_manager,group_project_user`. A user
  holding **only** the new restricted group and no other project group would not see the Project
  app icon at all, since the app root menu's `group_ids` doesn't include the new group. **The new
  restricted group must be additively granted on `project.menu_main_pm`** (`(4, ref(...))`, not a
  replace) so the app icon appears, while manager/user access is left untouched (satisfies FR-009).
- **Decision on hiding Projects/Reporting/Configuration**: Odoo's `group_ids` on `ir.ui.menu` is a
  whitelist, not a blacklist — there is no way to say "everyone except group X". To guarantee the
  new restricted group cannot see `menu_projects` / `menu_project_report` / `menu_project_config`,
  this module must set each menu's `group_ids` to an explicit whitelist of
  `project.group_project_manager` and `project.group_project_user` only (using replace semantics,
  `(6, 0, [...])`), never including the new group.
  - `menu_project_config` was confirmed to currently hold `groups="project.group_project_manager"`
    only (no `group_project_user`). The replacement value must reproduce this exact set, not widen
    it, to respect FR-009 ("no change for existing roles").
  - `menu_projects` and `menu_project_report` did not have a confirmed current `group_ids` value
    from static inspection (they may be unrestricted, relying only on the parent app-icon gate).
    **Verification task carried into implementation**: before finalizing `views/project_menus.xml`,
    confirm each menu's actual current `group_ids` via Developer Mode → Settings → Technical → User
    Interface → Menu Items in the target database, and reproduce that exact set (plus excluding the
    new group) rather than guessing. This mirrors the original source document's own "Open
    Verification Items" instruction, scoped now to just this one remaining unknown.
- Same "All Tasks" menu item — must be excluded from the restricted group for the same reason (it
  points at the unrestricted `action_view_all_task`, which allows all view modes and form access).
  Apply the same explicit-whitelist treatment to `project.menu_project_management_all_tasks`, then
  add a new sibling `menuitem` for the restricted group's own "All Tasks" entry pointing at the new
  restricted action, `groups="serichai_project_security.group_project_task_list_only"`.

## 3. List view base and Tags column

- **Decision**: Inherit `project.view_task_tree2` (`project/views/project_task_views.xml:809-820`),
  confirmed unchanged in Odoo 19 and still the view used by `action_view_all_task`.
- **Root tag confirmed as `<list>`, not `<tree>`**: Odoo 17+ renamed the list-view root tag; the
  source document (Odoo 18) already used `<list>`, and this is confirmed still correct for Odoo 19 —
  no changes needed to the xpath in the source document's `project_task_views.xml` example on this
  point.
- **Tags field**: confirmed `tag_ids` (many2many to `project.tags`), currently declared in the base
  arch (`project_task_view_tree_main_base`) as `optional="show"` — meaning it's already visible but
  user-toggleable via the list's optional-fields dropdown.
- **Decision**: Use `column_invisible="1"` on the `tag_ids` field via xpath in the inherited
  restricted view, rather than relying on `optional="hide"`. `column_invisible` removes the column
  unconditionally and removes it from the optional-fields toggle entirely, which better satisfies
  FR-006 ("MUST NOT display", not "hidden by default but re-enable-able").
- **Decision**: Use `<list position="attributes"><attribute name="open_form_view">false</attribute></list>`
  on the inherited view's root, confirmed valid syntax for Odoo 19 list views, to disable row click
  as a first line of defense (UI-level). This is a defense-in-depth measure; the hard enforcement
  is the `get_view` server-side override (below), since a UI attribute alone doesn't stop a direct
  form URL.

## 4. Server-side form-access blocking (`get_view` override)

- **Decision**: Override `get_view` on `project.task`, raising `AccessError` when `view_type ==
  'form'` and the user holds only the restricted group, following the existing precedent pattern
  found in Odoo core itself (`hr_recruitment/models/hr_applicant.py`, which overrides `get_view` to
  swap forms based on group membership — same method, same signature, same technique family).
- **Confirmed signature unchanged in Odoo 19**: `get_view(self, view_id=None, view_type='form',
  **options)`, defined in `odoo/odoo/addons/base/models/ir_ui_view.py` inside the `Base` abstract
  model, callable via `super().get_view(view_id=view_id, view_type=view_type, **options)`.
- **Rationale**: `open_form_view="false"` on the list view only stops the *default* row-click action in the
  web client; it does not stop a direct URL to the task's form, an API call, or a link from another
  view (e.g. a kanban card elsewhere the user might reach via a different, unrestricted action).
  Blocking at `get_view` for `view_type == 'form'` is a single enforcement point that covers all of
  these paths, matching FR-005/FR-010's "not only hidden in the interface" requirement.
- **Alternatives considered**: relying solely on `ir.rule` write/unlink restrictions plus
  `open_form_view="false"` was rejected because record rules don't prevent *reading* a single record's form
  (the user could still read the record, since perm_read=1) — only `get_view`'s `AccessError` fully
  blocks the form.

## 5. Record rule (stage-based row filtering) — corrected during implementation

- **Original plan (superseded)**: a single `ir.rule` on `project.task`,
  `domain_force="[('stage_id.name', '=', 'วางแผนการผลิต')]"`, scoped via
  `groups eval="[(4, ref('group_project_task_list_only'))]"` — mirroring the `groups`-scoped shape
  used by core examples like `task_visibility_rule`.
- **Why this was wrong, discovered by a failing automated test (T004)**: Odoo's rule engine ORs
  together every group-scoped rule that applies to any group a user belongs to — it does not
  AND-restrict. Because `group_project_task_list_only` implies `base.group_user` (§ addendum
  below), and `project` core itself attaches several `ir.rule` records **directly to
  `base.group_user`** (e.g. follower/visibility rules granting access to any task in a project
  whose `privacy_visibility` is `employees`/`portal`), those permissive rules were OR'd in
  alongside our stage-scoped rule. The net effect: our rule only ever *added* visibility, it could
  never *subtract* from what `base.group_user`'s own rules already granted — the decoy-stage task
  in the test project remained visible because the project's default privacy setting satisfied one
  of `project`'s own `base.group_user`-scoped rules. This is a real, reproducible flaw in the
  original spec/plan/research's mental model of `ir.rule`, not a database-specific quirk — it will
  bite in any Odoo install with `project`'s default rules present, since those rules are core, not
  optional.
- **Corrected decision**: make the rule **global** (no `groups` set at all — and explicitly clear
  any previously-set value with `eval="[(5, 0, 0)]"`, since omitting a field on an XML *update*
  does not reset it) with a **conditional `domain_force`** that only restricts members of the
  restricted role and is a no-op for everyone else:
  ```
  [('stage_id.name', '=', 'วางแผนการผลิต')] if user.has_group('serichai_project_security.group_project_task_list_only') else [(1, '=', 1)]
  ```
  `domain_force` is evaluated via `safe_eval` with `user` (`self.env.user`) in the eval context
  (confirmed in `odoo/odoo/addons/base/models/ir_rule.py`'s `_eval_context`/`_compute_domain`), so
  an arbitrary Python expression — including a ternary referencing `user.has_group(...)` — is valid,
  not just a literal domain list. A **global** rule is ANDed with the combined result of every
  other applicable rule (rather than OR'd), so it can only narrow the restricted user's visibility
  on top of whatever `base.group_user`'s rules already grant, and it leaves every other user's
  domain completely untouched (`[(1, '=', 1)]` matches everything).
- **Verified via automated test**: `test_restricted_user_sees_only_target_stage_tasks` failed twice
  under the original group-scoped design (leaking the decoy-stage task) before this fix, and passed
  once the rule became global + conditional — this is exactly the kind of defect a test written
  before implementation is meant to catch, and it did.
- **Filtering by stage name** (not stage ID / external ID) is necessary because "วางแผนการผลิต" is
  a instance-specific custom stage, not a stage that ships with a stable XML ID in core `project`.
  This matches the source document's approach and is carried forward as a documented assumption
  (see spec.md Assumptions) rather than treated as an open question — the exact string must match
  the live `project.task.type.name` value exactly (encoding/whitespace).
- Access rights: `project.task` and `project.project` both need `perm_read=1` with
  `perm_write/create/unlink=0` for the new group — confirmed this is the same shape used by core's
  own read-mostly rules (e.g. `task_visibility_rule` sets write/create/unlink `eval="False"` for its
  scoped group), so this is standard practice, not a special case.

## 6. Hiding the Dashboards app — deviation from the source document

- **Source document's assumption**: "Do not assign the Dashboards app's access group to this user"
  — implying a single group gates the app icon, matching a common Odoo Enterprise pattern.
- **What Odoo 19 actually does** (verified in `odoo/addons/spreadsheet_dashboard/views/menu_views.xml`):
  the Dashboards app's root menu (`spreadsheet_dashboard.spreadsheet_dashboard_menu_root`) has **no
  `groups` attribute at all** — it is visible to any internal user (anyone with `base.group_user`)
  by default. Content-level filtering happens per-dashboard via an `ir.rule` on `spreadsheet.dashboard`,
  not via an app-level group. There is a `spreadsheet_dashboard.group_dashboard_manager` group, but
  it only grants *edit* rights over dashboards, not visibility of the app icon.
  - Consequence: simply "not assigning a group" (the source doc's approach) **does nothing** in
    this Odoo 19 instance, since no such gating group exists to withhold. FR-007 cannot be met by
    omission; the module must actively restrict the menu's `group_ids`.
- **Decision (confirmed with user)**: Out of scope for this module. Hiding the Dashboards app icon
  outright would require enumerating and reproducing the exact `group_ids` whitelist for every group
  in the live database that currently relies on seeing `spreadsheet_dashboard_menu_root` — getting
  this wrong would silently regress Dashboards access for unrelated departments (Sales, Inventory,
  Invoicing, Manufacturing, Employees), directly violating FR-009. The user chose to **not** build
  any Dashboards-hiding mechanism (neither a menu `group_ids` rewrite nor a content-emptying
  `ir.rule`) and instead treat this as a documented, manual, module-external limitation.
- **Consequence for spec/requirements**: FR-007 and SC-007's "Dashboards app is invisible" clause is
  **not implemented** by this module. This is a deliberate, user-approved scope reduction, not an
  oversight — call this out explicitly in the module's `README`/description and in the final
  deployment/testing checklist so nobody mistakes its absence for a bug.
- **Alternatives considered and rejected for this iteration**:
  - Content-emptying `ir.rule` on `spreadsheet.dashboard` scoped to the new group (icon stays
    visible, but shows no dashboards) — zero blast-radius risk, but rejected by the user in favor of
    not touching this area of the system at all right now.
  - `post_init_hook` rewriting the shared menu's `group_ids` outright — rejected due to the
    whitelist-enumeration risk described above.
  - Hard `depends` on `spreadsheet_dashboard` — rejected regardless of approach, since it would
    force-install the Dashboards app on databases that don't already have it.

## 7. Testing approach

- **Decision**: Use Odoo's built-in test framework (`odoo.tests.common.TransactionCase` /
  `HttpCase`), run via `--test-enable --stop-after-init -u serichai_project_security` per
  `CLAUDE.md`'s documented workflow — no external test runner needed.
- **Rationale**: Matches repository convention; no dedicated test suite exists yet in either custom
  addon, so this module would be the first to establish the pattern, using standard Odoo idioms
  (`new_test_user`, `with self.assertRaises(AccessError)`, etc.).

## Summary of resolved unknowns

| Unknown | Resolution |
|---|---|
| Exact XML IDs for Project app menus in Odoo 19 | Verified directly from source (table in §2) |
| List/tree tag naming in Odoo 19 | Confirmed `<list>` root tag, same as source doc assumed |
| `get_view` override viability in Odoo 19 | Confirmed signature unchanged, precedent exists in core (`hr_recruitment`) |
| Mechanism gating the Dashboards app | Confirmed it's an unrestricted menu, not a group-gated one; user chose to leave Dashboards-hiding out of scope for this module (documented limitation) rather than risk regressing other departments |
| Module placement / manifest conventions | Follow `serichai_project_mo` precedent |
| Exact current `group_ids` on `menu_projects` / `menu_project_report` | Not resolvable from static source alone — flagged as a pre-implementation verification step against the live database |

## Addendum: field renames discovered during implementation (not caught by Phase 0 research)

The Phase 0 research above verified XML IDs and view/menu structure but did not exhaustively check
every field name against the actual Odoo 19 Python model source — two `many2many` fields were
renamed from their Odoo 18 names (which the source document used, and which Phase 0 research did
not catch since it focused on IDs/structure, not field names). Both were caught by real install
errors (`ValueError: Invalid field ...`) while executing tasks.md, not by static review:

- **`res.groups.category_id` → `res.groups.privilege_id`** (→ `res.groups.privilege` →
  `category_id`). In this Odoo 19 build, groups are organized via a `res.groups.privilege` model
  rather than a direct category field. For a purely technical/hidden group with no
  business-visible privilege (this module's exact case), the idiomatic pattern — confirmed via
  `hr_recruitment.group_applicant_cv_display` in core — is to omit `privilege_id` entirely, not to
  set any equivalent of the old `base.module_category_hidden`.
- **`ir.ui.menu.group_ids` and `ir.actions.act_window.group_ids`** — both were named `groups_id` in
  Odoo 18 (and in the source document); confirmed renamed to `group_ids` in this Odoo 19 build's
  `odoo/odoo/addons/base/models/ir_ui_menu.py` and `ir_actions.py`. `ir.rule.groups` (used for the
  stage-filter rule) is unaffected — that field name is unchanged.

All references to these fields throughout this feature's design docs (`data-model.md`,
`contracts/module-interface.md`, `plan.md`, `tasks.md`) have been corrected to `group_ids`
accordingly. `ir.model.access.group_id` (singular, many2one) is unrelated and unchanged.

Also adopted during implementation, not just a rename fix: `group_project_task_list_only` now sets
`implied_ids` → `base.group_user` (following `hr_recruitment.group_hr_recruitment_interviewer`'s
precedent), so assigning this one group is sufficient for a valid internal-user login — the
original spec/plan left `base.group_user` as a separate assumed prerequisite; this is a strict
improvement (fewer manual steps for an administrator) and doesn't change the security boundary,
since `base.group_user` alone grants no project permissions.
