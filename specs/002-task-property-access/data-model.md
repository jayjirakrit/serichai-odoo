# Phase 1 Data Model: Task Property Group Visibility

## New entity: `project.task.property.access`

Represents one visibility rule: a task-property label, and the groups permitted to see it.

| Field | Type | Required | Notes |
|---|---|---|---|
| `property_string` | `Char` | Yes | Exact displayed label of the property to restrict (matches the `'string'` key in the property's definition, e.g. `"Client Budget"`). Case-sensitive exact match, per spec FR-005. |
| `group_ids` | `Many2many` → `res.groups` | Yes | Groups permitted to see this property. A user needs membership in **at least one** (inclusive OR), per FR-004. |
| `active` | `Boolean` (standard Odoo `active` field) | — | Default `True`. Deactivating a rule has the same effect as deleting it (property becomes visible to everyone) — supports FR-007's "no restart required" without needing a separate audit trail in v1. |

**Validation rules**:
- `property_string` must be non-empty (enforced via `required=True`; no additional format constraint — any label text is a valid match target, per spec's Assumptions on label-based matching).
- `group_ids` must contain at least one group (enforced via `required=True` on the field plus a `_check_group_ids` SQL/Python constraint if empty many2many sets need explicit rejection — Odoo's `required=True` on a Many2many does not by itself prevent an empty set post-creation, so a `@api.constrains('group_ids')` guard is needed to reject a rule with zero groups, since a rule with no groups would make its property invisible to everyone with no way to see it — not a stated requirement and a likely misconfiguration).
- No two rules should silently target the exact same `property_string` with different group sets (ambiguous - which one wins). Enforce a SQL unique constraint on `property_string` so each label has at most one rule.

**Relationships**:
- No foreign key to `project.task` or `project.project` — deliberately global by label, not scoped to a specific project or task, per the spec's Assumptions ("Rules apply wherever a property with the matching label appears").
- Many2many to `res.groups` (existing model, no changes).

**Lifecycle**: Plain CRUD via the admin-facing list/form view; no state machine, no workflow.

## Existing entities referenced (unchanged)

- **`project.task.task_properties`** (`fields.Properties`, `odoo/addons/project/models/project_task.py:195`): read/write value per task; unchanged field definition. This feature only affects the *value returned by `read()`*, never the field's own definition/storage.
- **`project.project.task_properties_definition`** (`fields.PropertiesDefinition`, `odoo/addons/project/models/project_project.py:146`): unchanged. Still the sole source of each property's `name`/`string`/`type`/etc.
- **`res.groups`**: unchanged, existing model reused for `group_ids`.

## Read-time shape (for reference, not a stored entity)

`task_properties` on a `project.task` record, as returned by `read()`, is a list of dicts such as:

```python
[
    {'name': '3adf37f3258cfe40', 'string': 'Color Code', 'type': 'char', 'default': 'blue', 'value': 'red'},
    {'name': 'a1b2c3d4e5f6a7b8', 'string': 'Client Budget', 'type': 'monetary', 'value': 50000},
]
```

After this feature's `read()` override, for a user without a permitted group for `"Client Budget"`, the same call returns:

```python
[
    {'name': '3adf37f3258cfe40', 'string': 'Color Code', 'type': 'char', 'default': 'blue', 'value': 'red'},
]
```

The `"Client Budget"` dict is removed entirely (not masked/blanked), so the property does not appear in the UI at all, per FR-002.
