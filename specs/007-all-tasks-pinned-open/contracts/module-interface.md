# Module Interface Contract: serichai_project_security (spec 007 additions)

This lists what other code, administrators and testers can rely on. It is additive to the
contracts from specs 001 and 006.

## 1. Web client view registry

| Key | Category | Definition | Used by |
|---|---|---|---|
| `serichai_restricted_task_list` | `views` | `{...listView, Controller: RestrictedTaskListController}` | `view_task_list_restricted` (`js_class`) |

`RestrictedTaskListController.openRecord(record, {force, newWindow})`:
- **Pre**: the list arch loads the field `is_expanded_access_task`.
- If `record.data.is_expanded_access_task` is falsy, it shows a `warning` notification with the
  text "You can only open tasks of the project allowed for your role." and does not navigate.
- Otherwise it calls `props.selectRecord(record.resId, {activeIds, force, newWindow})`, where
  `activeIds` holds only the pinned rows currently loaded in the list.

Asset bundle: `web.assets_backend` → `serichai_project_security/static/src/views/restricted_task_list.js`.

## 2. Views and actions (XML ids)

| XML id | Contract |
|---|---|
| `serichai_project_security.action_task_all_restricted` | `view_mode = "list,form"`. The list view is `view_task_list_restricted`. The form view is the default `project.task` form. |
| `serichai_project_security.view_task_list_restricted` | The root `<list>` has `js_class="serichai_restricted_task_list"`, `create="0"`, `delete="0"` and `decoration-muted="not is_expanded_access_task"`. It contains `<field name="is_expanded_access_task" column_invisible="1"/>`. `tag_ids` stays `column_invisible="1"` (spec 001). |

## 3. Server: `project.task`

### `_is_restricted_form_load() -> bool`
Returns True only if **all** of these hold:
- `not env.su`
- an HTTP `request` is active
- the user has `serichai_project_security.group_project_task_list_only`
- the user does **not** have `project.group_project_user`
- `request.params['model'] == 'project.task'` and `request.params['method'] == 'web_read'`

### `web_read(specification)`
- If `_is_restricted_form_load()` is True and any record in `self` has
  `is_expanded_access_task == False`, it raises `odoo.exceptions.AccessError` with the message
  "You can only open tasks of the project allowed for your role."
- Otherwise it behaves exactly like the parent method.

### Not affected (guaranteed pass-through)
`web_search_read`, `web_read_group`, `web_name_search`, `web_save`, `read`, `search_read`, and
co-record `web_read` calls nested in any of these.

## 4. Behaviour matrix (restricted user, pinned project P)

| Path | Task in P | Task not in P |
|---|---|---|
| All Tasks: row listed | yes | yes, if in the production stages (spec 001/006 rule) |
| All Tasks: row styling | normal | muted |
| All Tasks: click / new-tab click | form opens | warning, no navigation |
| Form pager (opened from All Tasks) | steps through P rows only | not reachable |
| Direct URL / mail or activity link | form opens | AccessError |
| Edit and save on the form | allowed (spec 006 write rule) | n/a |
| Create / delete | refused | refused |

A user with `project.group_project_user` sees standard Odoo behaviour on every path.
