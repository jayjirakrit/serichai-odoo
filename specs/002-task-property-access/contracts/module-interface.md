# Contract: `serichai_project_security` Module Interface (Task Property Visibility addition)

This module has no HTTP/API surface. Its "contract" is the set of new external identifiers (XML
IDs) it creates, the model/field surface it exposes, and the behavior change to `project.task`
reads. Downstream work (tasks.md, tests, manual verification) should validate against this table
rather than against implementation prose. This document only covers what this feature *adds* to
the module — see `specs/001-restricted-task-access/contracts/module-interface.md` for the
module's pre-existing contract (task-list-viewer role), which this feature does not modify.

## New records this feature creates (stable external IDs)

| XML ID | Model | Purpose |
|---|---|---|
| `serichai_project_security.model_project_task_property_access` | `ir.model` (auto-generated) | The new `project.task.property.access` model. |
| `serichai_project_security.access_project_task_property_access_manager` | `ir.model.access.csv` row | Grants `project.group_project_manager` full CRUD (`perm_read=1, perm_write=1, perm_create=1, perm_unlink=1`) on `project.task.property.access`. |
| `serichai_project_security.view_project_task_property_access_list` | `ir.ui.view` | List view for the rule model: `property_string`, `group_ids`. |
| `serichai_project_security.view_project_task_property_access_form` | `ir.ui.view` | Form view for creating/editing a single rule. |
| `serichai_project_security.action_project_task_property_access` | `ir.actions.act_window` | Opens the list/form views above. |
| `serichai_project_security.menu_project_task_property_access` | `ir.ui.menu` | Entry point for the action, placed under Project → Configuration (`project.menu_project_config`), visible only to `project.group_project_manager` (matches that parent menu's existing group restriction). |

## Model surface: `project.task.property.access`

| Field | Type | Access |
|---|---|---|
| `property_string` | `Char`, required | CRUD limited to `project.group_project_manager` per the access row above |
| `group_ids` | `Many2many(res.groups)`, required, at least one entry (constraint) | same |
| `active` | `Boolean`, default `True` | same |

Constraints:
- Unique `property_string` across active rules (SQL constraint) — at most one rule per label.
- `group_ids` must be non-empty (Python constraint) — a rule with zero groups is rejected at save time rather than silently hiding a property from everyone.

## Behavior contract: `project.task.read()`

**Before this feature**: `read()` returns `task_properties` exactly as computed by the core `Properties` field — the full list of property dicts the user has task-level read access to, with no group-based filtering of individual entries.

**After this feature**: for any `project.task` recordset read with `task_properties` in the requested fields, the returned `task_properties` list for each record MUST:
1. Include every property dict whose `'string'` does **not** match any active `project.task.property.access.property_string` — unchanged from today (FR-003).
2. Include a property dict whose `'string'` **does** match an active rule, **iff** `self.env.user` is a member of at least one group in that rule's `group_ids` (FR-002, FR-004).
3. Omit (not mask/blank) a property dict whose `'string'` matches an active rule the current user has no permitted group for.
4. Apply this filtering identically regardless of call path — direct `read()`, `web_read()` (confirmed to delegate to `read()` per `odoo/addons/web/models/models.py:117`), and therefore all form/list/kanban/search rendering.

**Unaffected**: `write()`/`create()` on `task_properties` — no write-time enforcement in this iteration (FR-006). A user could still write to a property they cannot see, if they know its internal `name` (accepted limitation, matches spec scope).

## Explicitly out of scope for this feature (do not implement without a new spec/plan change)

- Any write-time / API-level blocking of writes to hidden properties.
- Any UI control inside the Properties definition editor itself (`property_definition.js`) for setting visibility at property-creation time.
- Any change to how properties are defined, added, or removed on `project.project.task_properties_definition`.
- Any change to the core Properties JSON schema (`PropertiesDefinition.ALLOWED_KEYS`) or `odoo/odoo/orm/fields_properties.py`.
- Any change to the existing task-list-viewer role/stage-filtering feature from `specs/001-restricted-task-access/`.

## Verification contract (how to check compliance)

For two test users — `user_finance` (member of a `group_finance` test group, in `group_ids` of a rule for `"Client Budget"`) and `user_other` (no membership in that group, otherwise normal `project.group_project_user` access) — both able to read the same task:

1. `task.with_user(user_finance).read(['task_properties'])[0]['task_properties']` MUST include a dict with `'string': 'Client Budget'`.
2. `task.with_user(user_other).read(['task_properties'])[0]['task_properties']` MUST NOT include any dict with `'string': 'Client Budget'`.
3. Both users' results MUST include every other property on the task unchanged (list equality on all non-`'Client Budget'` entries).
4. With the rule deleted (or `active=False`), both users' results MUST include `'Client Budget'` identically.
5. A user with only `project.group_project_user` (not `group_project_manager`) attempting `env['project.task.property.access'].create(...)` MUST raise `AccessError`.
6. Attempting to create a `project.task.property.access` record with `group_ids = []` MUST raise a validation error.
7. Attempting to create a second active rule with the same `property_string` as an existing active rule MUST raise a validation error (unique constraint).
