# Data Model: Open Pinned-Project Tasks from the Restricted "All Tasks" List

**No schema changes.** This feature adds no fields, tables or system parameters. It reuses what
spec 006 introduced and adds one derived rule.

## Reused entities

| Entity | Element | Origin | Role in this feature |
|---|---|---|---|
| `res.groups` | `serichai_project_security.group_project_task_list_only` | spec 001 | Who the gating applies to |
| `res.groups` | `project.group_project_user` (and the manager group, which implies it) | Odoo core | Exempt from the server guard (FR-008) |
| `ir.config_parameter` | `serichai_project_security.expanded_access_project_id` | spec 006 | The pinned project id (0 or missing = none) |
| `project.task` | `is_expanded_access_task` (computed, searchable, not stored) | spec 006 | True if `project_id` == pinned id. **This is the single source of truth for whether a task can be opened.** |
| `ir.rule` | `rule_task_write_pinned_project` | spec 006 | Write limited to pinned tasks. Unchanged, and it governs edits made from the newly reachable form |
| `ir.actions.act_window` | `action_task_all_restricted` | spec 001 | `view_mode` changed from `list` to `list,form` |
| `ir.ui.view` | `view_task_list_restricted` | spec 001 | Arch gains `js_class`, `create/delete=0`, `decoration-muted`, and the invisible `is_expanded_access_task` column |

## Derived rule: can a task be opened?

For a user U and a task T, opening T's form is allowed when **any** of these hold:

```text
U has project.group_project_user                       → allowed (unaffected)
U lacks group_project_task_list_only                   → allowed (unaffected)
T.is_expanded_access_task == True                      → allowed
otherwise                                              → refused (client: warning; server: AccessError)
```

Because `is_expanded_access_task` is computed live from the config parameter and `project_id`,
the rule changes immediately when any of these happen:
- the administrator repoints or clears the pinned project
- a task is moved into or out of the pinned project

On the client, the muted styling and the openable flag update on the next list reload. The
server refusal is always current (spec edge cases).

## State transitions

None. This feature adds no workflow state. Task stage changes are still governed by spec 006,
and editing in the pinned project still includes changing the stage.
