# Contract: serichai_project_access (area `odoo`, client <-> server delta)

Single area; this is the delta contract for the interface between the OWL list/kanban
controllers and the server guard, plus what administrators and testers rely on. It supersedes
the specs 001/002/006/007 module contracts of `serichai_project_security`.

## 1. Web client view registry

| Key | Category | Definition | Used by |
|---|---|---|---|
| `serichai_access_task_list` | `views` | `{...listView, Controller: AccessTaskListController}` | list views of `project.task` for restricted users |
| `serichai_access_task_kanban` | `views` | `{...kanbanView, Controller: AccessTaskKanbanController}` | kanban of restricted task action |

Both controllers override `openRecord(record, opts)`:
- **Pre**: the arch loads field `access_task_detail`.
- If `record.data.access_task_detail` is falsy: show `warning` notification
  "You are not allowed to open this task." and do not navigate.
- Else behave like core, with `activeIds` limited to loaded records whose
  `access_task_detail` is true (list passes `{activeIds, force, newWindow}`, kanban
  `{activeIds, newWindow}` through `props.selectRecord`).
- List rows with `access_task_detail` false get `decoration-muted`.

Assets: `web.assets_backend` -> `serichai_project_access/static/src/views/*.js`.

## 2. Server: `project.task`

### `_access_is_restricted_form_load() -> bool`
(Named differently from the old module's `_is_restricted_form_load`: a shared name made each module's `web_read` call the other's predicate while both are installed.)

True only if all hold: `not env.su`; HTTP `request` active; `env.user._get_project_access()` is
not `None`; `request.params['model'] == 'project.task'` and `['method'] == 'web_read'`.

### `web_read(specification)`
If `_access_is_restricted_form_load()` and any record of `self` has `access_task_detail == False`,
raise `AccessError("You are not allowed to open this task.")`. Internal calls (search_read,
read_group, co-record reads) are unaffected (research D6).

### `read(fields, load)`
For restricted users removes entries of `task_properties` whose normalised `string` is in the
grant's `hidden` set of the task's project. Unrestricted/su: untouched.

### `write(vals)`
If `task_properties` is written by a restricted user, hidden stored values of the task are
merged back before saving (research D7).

### Search fields
`access_task_visible`, `access_task_writable`, `access_task_detail`: operators `in`/`not in`
over booleans (Odoo 19 normalisation); other operators return `NotImplemented`.

## 3. Server: `res.users._get_project_access() -> dict | None`
`None` = unrestricted (no restricted group, or holds `project.group_project_user`).
Otherwise `{project_id: Grant}`; empty dict = restricted with nothing granted.
Cache: `ormcache('self.id', 'self._get_group_ids()')`. Cleared by
`registry.clear_cache()` on profile/line writes and project `active` changes.
Return value is immutable (tuples/frozensets); callers must not mutate it.

## 4. Server: `project.project`
- `action_view_tasks()`: restricted users get `action_task_access_project` (kanban, list, form;
  `default_project_id` and `active_id` in context, domain on project).
- Restricted users: only fields read; no write/create/unlink (ACL read-only + rule).

## 5. Security records (XML ids, module `serichai_project_access`)

| XML id | Model | Kind | Domain |
|---|---|---|---|
| `project_project_rule_access_read` | project.project | global, perm_read | `[('access_can_read','=',True)]` |
| `project_task_rule_access_read` | project.task | global, perm_read | `[('access_task_visible','=',True)]` |
| `project_task_rule_access_write` | project.task | global, write+create | `[('access_task_writable','=',True)]` |
| `project_task_rule_access_group_write` | project.task | group (restricted), write+create | `[(1,'=',1)]`; needed because core's `base.group_user` rule only covers private tasks; narrowed by the global write rule |
| `project_task_rule_access_unlink` | project.task | global, unlink | false for restricted (`has_group`), true otherwise |
| `serichai_project_access_group_restricted` | res.groups | implies `base.group_user` | |

ACL (`ir.model.access.csv`, group restricted): project.task r/w/c; project.project r;
project.role r; project.task.recurrence r; project.access.profile and .line: manager full.

## 6. Admin UI

| XML id | Contract |
|---|---|
| `project_access_profile_menu` | under `project.menu_project_config`, groups `project.group_project_manager` |
| `project_access_profile_action` | list (Department, Project tags) + form (tabs User read-only, Project lines) |
| `menu_task_all_access`, `menu_project_access` | restricted-only menus "All Tasks" (seq 0) and "Project" (seq 1) under `project.menu_main_pm` |

## 7. Behaviour matrix (restricted user, one project)

| Grant | List shows | Open detail | Edit/create | Delete | Properties |
|---|---|---|---|---|---|
| none | no | no | no | no | - |
| Read, list only | allowed stages | refused (guard) | no | no | minus hidden |
| Read, open detail | allowed stages | yes | no | no | minus hidden |
| Write | all stages | yes | yes | no | all |
