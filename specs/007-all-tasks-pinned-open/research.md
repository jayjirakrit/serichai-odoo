# Research: Open Pinned-Project Tasks from the Restricted "All Tasks" List

All findings were checked against the vendored Odoo 19.0 source in `odoo/`.

## Decision 1: Root cause of "cannot enter a task from All Tasks"

**Finding**: The `open_form_view="false"` attribute on `view_task_list_restricted` has **no
effect**. `web/static/src/views/list/list_arch_parser.js` (around line 204) reads it only when
the list is `editable`:

```js
treeAttr.openFormView = treeAttr.editable ? exprToBoolean(xmlDoc.getAttribute("open_form_view") || "") : false;
```

The actual block is that `action_task_all_restricted` had `view_mode=list`. In
`web/static/src/webclient/actions/action_service.js`, `openFormView(resId, {force})` switches
to the form only if the action has a form view, and otherwise falls back to a new action only
when `force || !resId`. A plain row click passes neither, so it quietly does nothing.

**Decision**: Add `form` to the action (`view_mode=list,form`) and drop the dead attribute.
Which rows open is then decided per row by a custom controller (Decision 2).

## Decision 2: Per-row gating in the list

**Decision**: Register a list view `serichai_restricted_task_list` (`{...listView, Controller}`)
whose controller extends `ListController` and overrides `openRecord(record, options)`:
- if `record.data.is_expanded_access_task` is false, show a warning through the
  `notification` service and return
- otherwise call `props.selectRecord(resId, {activeIds, force, newWindow})`, with `activeIds`
  filtered to pinned rows only, so the form pager never steps onto a blocked task (FR-005)

The list arch adds `is_expanded_access_task` as a `column_invisible` field, because the client
needs the value. It also adds `decoration-muted="not is_expanded_access_task"` (FR-003) and
`create="0" delete="0"`. `project_todo` gives `base.group_user` create ACLs, so the buttons
would otherwise render, as noted in spec 006 for the kanban.

**Rationale**: `openRecord` is the single funnel for row clicks, both normal and new-window
(`list_renderer.js` → `props.openRecord`). Overriding it changes nothing else about the list.

**Alternatives considered**:
- *`no_open="1"` on the list*: all-or-nothing, so no per-row behaviour.
- *An `action` / `type` open-action attribute calling a server method that checks the record*:
  every click costs a server round-trip, the result is still an action that the guard has to
  back up, and the pager context is lost.
- *Patching the global `ListController`*: affects every list in the system. Rejected in favour
  of a dedicated `js_class`.

## Decision 3: Server-side enforcement without breaking list or kanban

**Finding**: `web_read` is used far beyond form loads. In `web/models/models.py` it is called
from `web_name_search` (line 62), `web_search_read` (68), co-record reads for many2one,
x2many and properties (149, 235, 268, 310–314), `web_read_group` unfolding (492, 537) and
`web_save` (97). A guard that rejects non-pinned tasks in every `web_read` would break the
**All Tasks** list itself, which shows non-pinned tasks. This confirms spec 006 research
Decision 3.

**Decision**: Guard only when the **top-level RPC** is `project.task.web_read`, which is how the
form, the pager, deep links (`/odoo/project.task/<id>`) and mail or activity links load a
record. Both JSON dispatchers in Odoo 19 put `model` and `method` in `request.params`:
`/web/dataset/call_kw` puts them in the JSON-RPC params (`http.py`, about line 2569), and
`/json/2/<model>/<method>` puts them in the path args merged into params (about line 2632).

The guard (`_is_restricted_form_load`) fires only when all of these hold:
1. the call is not superuser
2. there is an HTTP request
3. the user has `group_project_task_list_only` and does **not** have `project.group_project_user`
   (managers imply user)
4. `request.params` has `model == 'project.task'` and `method == 'web_read'`

If any record in `self` is not `is_expanded_access_task`, it raises `AccessError`.

**Rationale**: Internal `web_read` calls happen inside a different top-level method, such as
`web_search_read` or `web_read_group`, so they pass. Co-record reads of related tasks inside a
pinned form also pass: they render as references only, and opening one is a new top-level
`web_read` that gets refused (spec US2 scenario 4).

**Alternatives considered**:
- *A context flag set by `web_search_read` and checked in `web_read`*: you would have to list
  every internal caller, which is fragile across Odoo versions.
- *Tightening the read `ir.rule`*: it would hide non-pinned tasks from the list, which violates FR-007.
- *Overriding the `call_kw` controller*: controller-level patching of a core route is harder to
  test and to scope to one model.

**Known limitation**: this is an interaction boundary, not a confidentiality boundary. The role
can still `search_read` or `web_search_read` the tasks it can see, along with their fields. This
was accepted in spec 006 and restated in spec 007's Assumptions.

## Decision 4: Who is exempt

**Decision**: Users with `project.group_project_user`, including managers, are exempt even if
they also hold the restricted role (FR-008). The restricted group does not imply
`group_project_user`, so the check is unambiguous.

## Decision 5: Testing the request-dependent guard

**Decision**: In `TransactionCase`, patch
`odoo.addons.serichai_project_security.models.project_task.request` with
`SimpleNamespace(params={'model': 'project.task', 'method': <m>})`. That one patch covers
these cases:
- a pinned task is allowed
- a non-pinned task is refused
- `web_search_read` still lists non-pinned tasks
- a control project user is unaffected

**Rationale**: `HttpCase` with a browser tour would also cover the JS, but it is slow and needs
a headless Chrome in WSL. The JS behaviour is covered by the manual walkthrough in
quickstart.md, and a tour can be added later if needed.
