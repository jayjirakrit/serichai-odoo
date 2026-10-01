# Phase 0 Research: Expanded Task Access for Product Development Project

## Decision 1: How the "pinned project" is stored and identified

**Decision**: Store the pinned project's `id` as an `ir.config_parameter` system parameter
(`serichai_project_security.expanded_access_project_id`), exposed to administrators through a
`res.config.settings` Many2one field (standard `config_parameter="..."` binding — no custom
model, no new table).

**Rationale**: FR-003/FR-004 require the grant to follow one specific `project.project` record
(survives renames, doesn't leak to a same-named project) and to be repointable by an
administrator without a code change. `ir.config_parameter` + `res.config.settings` is the
standard Odoo idiom for exactly this shape of "one admin-editable singleton value" — it needs
no migration, no new security rules of its own (config settings already require
`base.group_system`), and is trivially readable from Python (`get_param`) wherever the pinned
id is needed.

**Alternatives considered**:
- *Match by project display name at runtime* — rejected per spec's resolved Edge Case: a
  future unrelated project named "Product Development" would silently inherit the grant, and a
  rename would silently drop it.
- *A dedicated one-row model (e.g. `serichai_project_security.settings`)* — rejected as
  needless ceremony; a single scalar value doesn't need its own model/table when
  `ir.config_parameter` already exists for this.
- *Hardcode the project's XML ID in module data* — rejected: the project record already exists
  in the production database and isn't shipped as module data, and hardcoding would require a
  code change to ever repoint it, violating the "administrator repoints it" requirement.

## Decision 2: How write access is scoped to the pinned project

**Decision**: Add one computed + searchable Boolean field on `project.task`,
`is_expanded_access_task`, resolved from the config parameter above. Grant
`perm_write = 1` at the `ir.model.access.csv` level for the restricted group (currently 0), and
add a new `ir.rule` scoped to that group with `perm_write=True` / `perm_read=False` /
`perm_create=False` / `perm_unlink=False` and `domain_force="[('is_expanded_access_task', '=', True)]"`.

**Rationale**: In Odoo, `ir.model.access` sets the model-wide ceiling per group; `ir.rule` can
only *narrow* it further, never grant beyond it — so write must first be allowed at the access
level, then narrowed to the pinned project via the rule. Restricting the rule's `perm_*` flags
to only `perm_write=True` means this new rule leaves read (governed by the existing
`rule_task_stage_restricted`) and create/unlink (still `0` in the access CSV, so blocked
regardless of any rule) untouched — this is the mechanism that keeps FR-002's "edit only, no
create/delete, everywhere else unchanged" true. A single computed/searchable field (rather than
inlining a `user.env['ir.config_parameter']...` expression directly into the `domain_force`
XML string) keeps the config-parameter lookup in one testable Python method and reuses the same
field for the dedicated action's domain in Decision 3, instead of duplicating the lookup logic
in two places.

**Alternatives considered**:
- *Inline the config-parameter lookup directly in `domain_force`'s XML string* — technically
  possible (rule domains are evaluated with the acting `user` in scope, and `user.env[...]` is
  reachable), but no precedent for it exists anywhere in Odoo core's own security XML, and it
  would duplicate the lookup wherever else the pinned project needs to be checked. Rejected for
  a single well-named, testable field instead.
- *Compare `project_id` directly in the rule instead of adding a boolean field* — this is what
  the boolean field's `search` implementation does internally; a named field was kept anyway so
  it can also be reused as the dedicated action's domain and unit-tested on its own.

## Decision 3: How the task **form** becomes reachable for the pinned project only

This was the crux of the research: could "no form view outside the pinned project" be enforced
as a genuine record-level access-control boundary, the way the write restriction is?

**Finding**: No — verified against the Odoo 19 web client's actual call path
(`odoo/addons/web/controllers/json.py`): the view architecture is fetched via
`model.get_view(view_id, view_type)` on an **unbound** recordset (`env[res_model]`, no ids),
strictly *before* any specific record is read — so `get_view` (the method the module's current
`AccessError` override lives on) never has access to *which* task is being opened, and cannot
be made record-aware. Separately, both the list view (`web_search_read` → `web_read`) and a
single form (`browse(id).web_read(...)`) funnel through the same `read()`/`web_read()` methods,
so overriding `read()` to reject reads of non-pinned tasks would also break the list (which must
keep showing tasks from *every* project, per spec Acceptance Scenario 3 — this feature changes
what a task can be *edited* with, not which tasks are visible).

Given that, and given that `project.task` read access is **already** granted broadly to this
role today (list view shows tasks across all projects, filtered only by stage) — the
pre-existing "no form" restriction was always a workflow/UX guardrail on top of that existing
read access, not an independent data-confidentiality boundary. The module's other UI-side
guardrails (hidden menus, `open_form_view="false"` on the shared list view) are the same kind of
control: convention-level, not `ir.rule`-level.

**Decision**: Keep that same convention-level approach, scoped to the new project:
- Add one **new**, separate window action + list view + menu item
  (`action_task_product_development_restricted` / `menu_task_product_development_restricted`),
  visible only to `group_project_task_list_only`, whose list domain is
  `[('is_expanded_access_task', '=', True)]` (same field as Decision 2) — so it only ever lists
  tasks in the pinned project — and which leaves `open_form_view` at its default (`true`), so
  rows are clickable.
- The existing "All Tasks" action/menu/view is untouched, including its
  `open_form_view="false"` attribute, so it keeps behaving exactly as it does today for every
  project (including the pinned one, if reached through that entry point).
- The blanket `AccessError` in `get_view` for `view_type == 'form'` is removed for this group
  (it can no longer be categorically true), since it would otherwise also block the new,
  legitimate action. No replacement record-aware check is added at this layer, for the reason
  above — it isn't achievable, and it isn't where the real security boundary belongs.

**Why this doesn't weaken the module's security posture**: The genuinely enforced boundary —
the one the spec's acceptance criteria treat as load-bearing (SC-002, SC-005) — is *write*
access, which stays fully `ir.rule`-enforced per Decision 2 regardless of which action/menu a
request came through, and regardless of whether it came from the standard client or a raw RPC
call. Removing the `get_view` block only affects whether the form *renders*; since this role
already has model-wide `perm_read=1` on `project.task` (Decision 2's note on the existing
access CSV), a user was already able to read every field of a non-pinned task via the list —
opening the same data in form layout adds no new data exposure, only a workflow affordance that
this design deliberately does not expose (no button/menu links to it) outside the pinned
project.

**Alternatives considered**:
- *A context flag read inside `get_view` (e.g. `self.env.context.get('expanded_task_access')`),
  set only by the new action* — rejected: context is entirely client-supplied on every Odoo RPC
  call (not just this endpoint), so it is no more "secure" than the action/menu-only approach
  above, while being less transparent about the fact that it isn't a real access-control
  boundary. Dropped in favor of just not pretending `get_view` can do this job.
- *Per-row conditional `open_form_view`* — checked against the actual OWL list arch parser
  (`list_arch_parser.js`): `open_form_view` is parsed once as a static boolean for the whole
  view, not per record. Not supported by the framework; not pursued further.
- *Inline editable list (`editable="bottom"`) instead of a form at all* — would have avoided
  this whole question, but the spec's resolved clarification (User Story 1 / FR-002) explicitly
  describes "open the task form and edit fields," which this option doesn't deliver. Rejected
  as not matching the agreed scope.

## Decision 4: No `contracts/` artifact

**Decision**: Skip the `contracts/` output for Phase 1.

**Rationale**: This feature adds no externally-facing API, endpoint, CLI, or schema — it is
entirely a change to one Odoo addon's internal security model (`ir.model.access`, `ir.rule`)
and views. The "interface" a user interacts with is the standard Odoo web client against
existing `project.task`/`project.project` models, which is already fully specified by Odoo core
and unchanged by this feature.

## Decision 5 (2026-10-01): Pinned-project visibility and Kanban stage columns

**Trigger**: After delivery, the restricted user's "Product Development" menu showed column
headers but no tasks. Live DB: pinned project id 57 has a single stage "To Do", which is outside
`rule_task_stage_restricted`'s Production Planning stage list, so the global rule hid every task.
See spec Clarifications (Session 2026-10-01), FR-007, FR-008.

**Decisions**:
- *Visibility*: `rule_task_stage_restricted`'s restricted-role branch becomes
  `['|', ('is_expanded_access_task', '=', True), ('stage_id.name', 'in', [...])]`. Same
  record-id pinning as Decision 1; other projects keep the stage filter unchanged.
- *Kanban columns*: the "Product Development" action becomes `kanban,list,form`. Showing empty
  stages relies on `project.task._read_group_stage_ids`, which only adds a project's stages when
  the context has `default_project_id` (plus `project_kanban`, which the `project_task_kanban`
  JS model adds itself). The pinned id is only known at runtime, so the menu now points at a
  server action (`action_server_task_product_development_restricted`) that calls
  `project.task.action_open_expanded_access_tasks()`, which returns the window action with that
  context injected.
- *No create / column editing in the UI*: `project_todo` (auto-installed with `project`) grants
  `base.group_user` full CRUD ACLs on `project.task`; record rules are what block create/unlink
  in projects. So view post-processing never sets `create="False"`, and a dedicated primary
  Kanban view (`view_task_kanban_expanded_access`) sets `create`/`delete`/`quick_create`/
  `group_create`/`group_edit`/`group_delete` to `0` explicitly; the expanded list sets
  `create`/`delete` to `0`.

**Bug found while implementing**: `_search_is_expanded_access_task` only handled `=`/`!=`, but
Odoo 19 normalizes boolean conditions to `in`/`not in` a set of booleans before calling search
methods. `('is_expanded_access_task', '=', True)` therefore resolved to `project_id != pinned`,
so the menu domain matched tasks *outside* the pinned project. Rewritten for `in`/`not in`.

