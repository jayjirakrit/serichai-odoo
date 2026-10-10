# Research: Configurable Project Access by Department

Phase 0 output. Every item was checked against the vendored Odoo 19 source
(`odoo/`) or the old module (`serichai_project_security`). Items marked **PLAN DOES NOT HOLD**
differ from `PROJECT_ACCESS_PLAN.md`. No "NEEDS CLARIFICATION" remains; residual choices are in
design.md "Open questions".

## D1. Record rules must be GLOBAL, not group rules (PLAN DOES NOT HOLD)

- **Finding**: `ir.rule._compute_domain` (`odoo/addons/base/models/ir_rule.py:141-173`) ANDs
  global rules and ORs group rules. The restricted user also holds `base.group_user`, which
  carries core group rules (`task_visibility_rule`, `project_public_members_rule`) and, via
  auto-installed `project_todo`, `task_edition_rule_internal` plus a full-CRUD ACL on
  `project.task` for `base.group_user` (`project_todo/security/ir.model.access.csv:3`).
  A rule bound to the restricted group would be OR-ed with those and could only widen access.
- **Decision**: all narrowing rules are global (`groups` empty). Their domains use searchable
  computed fields whose search methods return `Domain.TRUE` for unrestricted users, so no
  `has_group` trick is needed in read/write rules (old `ir_rule.xml:12` pattern avoided).
  Only the unlink rule uses `user.has_group` (one place, commented).
- **Alternatives rejected**: group rules (widen only); `has_group` conditional in every rule
  (duplicates the "restricted" definition in XML, harder to test).

## D2. Project write/create rule is not needed (PLAN DOES NOT HOLD)

Plan item "project write" rule. Core ACL gives `base.group_user` read-only on `project.project`
(`project/security/ir.model.access.csv`, `access_project_user`). Restricted users get no project
write ACL, so FR-011/FR-012 (never change or delete projects) hold by ACL alone. Only a project
**read** rule is added.

### D1a. Exception: one group rule, `project_task_rule_access_group_write`

Core gives `base.group_user` write/create on `project.task` only through a group rule limited to
private tasks (no project). Group rules OR together and global rules AND on top, so with no group
rule of its own the restricted group could never write a project task, whatever the global write
rule allows. The extra group rule (restricted group, `[(1, '=', 1)]`, write+create) widens the
group side; the global `project_task_rule_access_write` then narrows it to Write projects.

## D3. Task unlink is blocked by a rule, not by ACL

`project_todo` (auto_install) grants `base.group_user` unlink on `project.task`, so withholding
unlink from our own ACL row is not enough. A global unlink rule returns the false domain for
restricted users (FR-012, SC-003). Decision on "Write deletes?" is closed: no.

## D4. Group field names and cache invalidation (plan wording corrected)

- `res.users.group_ids` (explicit) and `all_group_ids` (with implied) exist in 19
  (`res_users.py:257-259`); `groups_id` is gone. `res.groups.implied_ids` and
  `res.groups.user_ids` are the other sides.
- Writes to `res.users.group_ids` already call `ir.model.access.call_cache_clearing_methods`
  (clears only the `stable` cache) and, because `group_ids` is in `_get_invalidation_fields`,
  `registry.clear_cache()` (default cache). A group-membership change via `res.groups.user_ids`
  or implied-group edits does not necessarily pass there.
- **Decision**: key the helper cache on the user's resolved group ids:
  `@tools.ormcache('self.id', 'self._get_group_ids()')`. Membership changes then miss the
  cache by construction (FR-016, SC-006). Profile, line and project-`active` writes call
  `self.env.registry.clear_cache()` (propagates across workers at commit).
- `_get_group_ids` is itself `ormcache('self.id')` (`res_users.py:1098`) and is invalidated by
  the core on group edits.

## D5. "Restricted" status through `implied_ids` is feasible but needs a guard

- Adding the control group to `implied_ids` of each profile group makes every member restricted
  (existing members included) and is removed with the group on uninstall (cascade).
- **Risk**: choosing `base.group_user` (or portal/public) as the department group would make
  everyone restricted. **Decision**: constraint on profile `group_ids` forbidding
  `base.group_user`, `base.group_portal`, `base.group_public`, `base.group_system` and the
  Project user/manager groups. A user who has `project.group_project_user` is exempt at runtime
  (helper returns `None`), as FR-017 requires.
- Sync is a single idempotent method `_sync_restricted_group()` (set-difference between "groups
  of active profiles" and "groups that imply the control group"), called after
  create/write/unlink of profiles. Uses `sudo()` because only project managers edit profiles
  but `res.groups` needs settings rights; commented as such (Principle III).

## D6. List-only guard: top-level RPC detection still works in 19

`web/controllers/dataset.py:28-32` routes `call_kw` with `model`/`method` as request params, so
`request.params['model'] == 'project.task' and ['method'] == 'web_read'` (old
`_access_is_restricted_form_load`) holds. `web_read` is also called by `web_search_read`
(`web/models/models.py:66-68`), so a blanket guard would break lists. Pattern reused unchanged;
only the "is restricted" test and the per-task test (`access_task_detail`) change.

## D7. Property hiding: filter on read, merge on write (partly unreachable)

- `fields.Properties.write` with a list replaces the stored dict (`fields_properties.py:
  convert_to_cache` list branch keeps only given names), so a client that never received a
  hidden property would erase it. The plan's write-merge is therefore technically correct.
- By construction a user whose merged access hides a property cannot write that task (hidden
  names exist only on Read lines; Write wins in the merge), so the path is reachable only if
  a task is moved between projects or rules race. **Decision**: implement the merge as a small
  defensive override (FR-013 says "never erase"), covered by one test; not a primary control.
- Hiding in `read()` is per task project (`project_id`), keyed on the normalised label
  (`strip().casefold()`) against each property's `string`. `web_read` goes through `read`, as
  the old module relies on. Search/group-by on property values is not covered (as in spec 002).

## D8. Stage filtering also needs the kanban column expansion

`project.task._read_group_stage_ids` (`project/models/project_task.py:138-145`) adds every stage
linked to `default_project_id` as an empty column. Without an override a restricted user would
see disallowed stage names as empty columns, breaking FR-021. **Decision**: override it to
intersect with the grant's allowed stages (and return none when the project is not granted).

## D9. Menus: use `_load_menus_blacklist`, not data overrides (improves plan, helps FR-025)

- The old module rewrote `group_ids` of six core menus in XML. Those writes are not reverted on
  uninstall (core records stay), which is the "lingering restriction" FR-025 forbids.
- `ir.ui.menu._load_menus_blacklist()` (`ir_ui_menu.py:210`; extended by `project` at
  `project/models/ir_ui_menu.py:10`) is a code hook evaluated per user, cached under
  `load_menus` (cache cleared with the registry cache). **Decision**: for restricted users the
  hook blacklists every menu under `project.menu_main_pm` except our two; for unrestricted
  users it blacklists our two (so a Project manager who is also in a department sees no
  duplicates). The only data change to core is additive: the control group on
  `project.menu_main_pm`, removed by cascade with the group.
- Migration also restores the six core menus' `group_ids` to the core values (D12).

## D10. "Project" menu reuses the stock project kanban

Core `view_project_kanban` has `action="action_view_tasks" type="object"`, so clicking a card
opens that project's tasks (`project_project.py:930`). A primary-inherited kanban (create/edit/
delete off) behind the project read rule gives "list of accessible projects" with 1 click to
tasks (SC-007) and no JS. `action_view_tasks` is overridden for restricted users to return our
restricted task action (kanban + list + form with the guards). Open question 1: spec text says
"list"; a project list view would need a custom row-click controller.

## D11. Core rules still AND in

`project_public_members_rule` and `task_visibility_rule*` (`project_security.xml`) require
`privacy_visibility in (employees, portal)` or following. Granted projects with `followers` /
`invited_users` visibility stay hidden; the line form shows a warning (FR-009) built from
`project.privacy_visibility`. Not worked around (would need sudo rewrites; out of scope).

## D12. Migration runs from `post_init_hook`, not `migrations/`

A `migrations/<version>` script runs only when the module is *updated*; a fresh install of the
new module (with the old one still installed) never triggers it. `post_init_hook(env)` runs at
install, is idempotent, and can be re-run on a restored DB copy (FR-026).
Data captured: pinned project (`ir.config_parameter serichai_project_security.
expanded_access_project_id`), `project.task.property.access` rules, members of
`serichai_project_security.group_project_task_list_only`.

- The old group disappears with the old module, so a **new** group
  (`serichai_project_access.group_production_planning`, implies `base.group_user`) is created by
  the hook and given to the old users; the profile uses it.
- Hidden names = labels of active property-access rules whose `group_ids` do not contain the old
  group (same logic as `_get_restricted_strings_for_user` for a user with only that group).
  Users holding extra permitted groups could differ; rehearsal diff must cover them (risk R3).
- Stage names: the four Thai names from old `ir_rule.xml:12`, resolved by name to
  `project.task.type`; names that match nothing are logged (they cannot be silently dropped,
  an empty selection would mean "all stages").
- Lines: one Write/detail line for the pinned project; one Read/list line for every other
  active project (`is_template = False`). New projects created later are not auto-added
  (old behaviour covered "every project"; open question 3).
- After old-module uninstall, the hook step "restore core menus" resets the six menus to core
  values (`menu_main_pm`: manager+user; `menu_projects_group_stage`: `group_project_stages`;
  `menu_projects`, `menu_project_report`, `menu_project_management`,
  `menu_project_management_all_tasks`: no groups). Those with no group are harmless for users who
  cannot reach the app root, as before.

## D13. Other verified items

- Rule evaluation on `create` for a global rule that uses a non-stored search field is done by
  searching the freshly inserted record; tests must prove `access_task_writable` works at
  create (specs must assert).
- `project_todo` is `auto_install`; `task_edition_rule_internal` (own private tasks, group rule)
  is neutralised for restricted users because the global write/create/read rules require a
  granted project (private tasks have none).
- `res.users.has_group` is available in rule eval context (old module uses it). `request` is
  patched in tests via `odoo.addons.serichai_project_access.models.project_task.request`.
- Old module conflicts (both override `web_read`/`read`): during the rehearsal window both
  restrict; results are AND-ed, which equals the migrated behaviour. Uninstall the old module
  before declaring go-live.
