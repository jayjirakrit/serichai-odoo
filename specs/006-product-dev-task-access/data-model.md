# Phase 1 Data Model: Expanded Task Access for Product Development Project

No new persistent tables/models are introduced. This feature adds one system parameter, one
computed field, and one security rule on top of existing entities.

## `ir.config_parameter` (existing Odoo model, new key)

| Key | Value | Notes |
|-----|-------|-------|
| `serichai_project_security.expanded_access_project_id` | `id` of a `project.project` record (string-encoded int), or unset/`0` | Edited via the `res.config.settings` field below. Absent/`0` ⇒ the expanded-access grant matches no tasks (Edge Case: "no project ... exists yet"). |

## `project.task` (existing model — extended)

| Field | Type | Description |
|-------|------|-------------|
| `is_expanded_access_task` | `Boolean`, computed, **searchable**, not stored | `True` iff `project_id.id` equals the id stored under the config parameter above. Computed per-record via `_compute_is_expanded_access_task`; the paired `_search_is_expanded_access_task` translates `('is_expanded_access_task', '=', True)` into `[('project_id', '=', <pinned id>)]` (or `[('id', '=', False)]` when no project is pinned) so it can be used inside both `ir.rule.domain_force` and the new action's `domain`. |

No change to any other existing field on `project.task` or `project.project`.

## `res.config.settings` (existing transient model — extended)

| Field | Type | `config_parameter` | Description |
|-------|------|---------------------|-------------|
| `serichai_expanded_access_project_id` | `Many2one('project.project')` | `serichai_project_security.expanded_access_project_id` | Administrator-facing field (Settings screen) used to pin/repoint the project. No `domain` restriction on which projects are selectable — any `project.project` record, active or not, may be pinned (consistent with FR-003's "administrator explicitly re-configures it"). |

## `ir.rule` (existing model — one new record)

| id | Model | Groups | perm_read | perm_write | perm_create | perm_unlink | domain_force |
|----|-------|--------|-----------|------------|-------------|-------------|--------------|
| `rule_task_write_pinned_project` | `project.task` | `group_project_task_list_only` | `False` | `True` | `False` | `False` | `[('is_expanded_access_task', '=', True)]` |

This is additive to the existing `rule_task_stage_restricted` (which continues to govern
`perm_read` only, unchanged by this feature).

## `ir.model.access` (existing model — one row modified)

| id | perm_read | perm_write (before → after) | perm_create | perm_unlink |
|----|-----------|------------------------------|--------------|-------------|
| `access_project_task_restricted` | `1` (unchanged) | `0` → `1` | `0` (unchanged) | `0` (unchanged) |

`perm_write=1` is the ceiling; `rule_task_write_pinned_project` above narrows the actual
writable set down to the pinned project's tasks.

## `ir.actions.act_window` / `ir.ui.menu` (existing models — one new record each)

| id | Type | Key attributes |
|----|------|-----------------|
| `action_task_product_development_restricted` | `ir.actions.act_window` | `res_model='project.task'`, `view_mode='list'`, a dedicated list view (see below) with `open_form_view` left at its default (`true`), `domain="[('is_expanded_access_task','=', True)]"`, `group_ids` limited to `group_project_task_list_only` |
| `view_task_list_expanded_access` | `ir.ui.view` (`list`) | Inherits `project.view_task_tree2` the same way `view_task_list_restricted` does, but **without** the `open_form_view="false"` override, so rows are clickable |
| `menu_task_product_development_restricted` | `ir.ui.menu` | Sibling of `menu_task_all_restricted` under `project.menu_main_pm`, visible only to `group_project_task_list_only` |

No relationships change on `project.task` ↔ `mrp.production` or any other cross-model relation
from other addons — this feature is scoped entirely to `serichai_project_security`.
