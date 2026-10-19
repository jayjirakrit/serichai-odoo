# Research: High-Value-First Task Sorting

Phase 0 output. Each item was checked against the vendored Odoo 19 source (`odoo/`), the custom
addons in `serichai-odoo/`, or `serichai-db` (read-only `odoo-bin shell`, `env.cr.rollback()`,
2026-10-19). No "NEEDS CLARIFICATION" remains; Gate 2 decisions (2026-10-19) are folded into V5-V7 and D2.

## V1. Odoo version and conventions (verified)

- `odoo/odoo/release.py:15`: `version_info = (19, 0, 0, FINAL, 0, '')`, i.e. 19.0.
- Views use `<list>` (core `project_task_view_tree_main_base` is `<list ...>`); `attrs` is gone,
  conditions are Python expressions in `invisible=` / `column_invisible=`; optional columns use
  `optional="show"`. Settings use `<app>` / `<block>` / `<setting>` (`project/views/res_config_settings_views.xml`).
- Manifest version: repo modules use `'1.0.0'` (`serichai_project_mo`) / `'1.1.0'`; Odoo prefixes the
  series automatically. **Decision**: `'version': '1.0.0'`, `'license': 'AGPL-3'`, `'author': 'Serichai Group'`,
  `'category': 'Project'` (house style).
- Hook signatures in 19: `pre_init_hook(env)`, `post_init_hook(env)` (e.g. `sale_management/__init__.py`,
  `account_payment/__init__.py`).

## V2. House structure and reuse (verified)

- Reference modules: `serichai_project_access` (spec 009, **installed** in `serichai-db`),
  `serichai_project_mo` (installed), `serichai_project_security` (**not installed**; superseded by 009).
- 009 resolves properties by label: it iterates `project.task_properties_definition` and compares
  `p.get('string')` through `norm_label()` (`serichai_project_access/models/_utils.py`: NFKC, inner
  spaces collapsed, trim, casefold). **Decision**: reuse the *pattern* (iterate the project's
  definition, match `string`, first match wins) but compare with `.strip()` only, because spec FR-002
  and the edge cases say "leading/trailing spaces only; any other spelling difference is not
  matched". No 009 code is reused or referenced (D2).
- `serichai-db` has a real duplicate-label case (three properties labelled "วันที่ลงนาม" in project 3),
  so "first in the project's property order" (spec edge case) is not hypothetical.

## V3. What `task_properties` is, in each layer (verified empirically)

Field: `project.task.task_properties = fields.Properties(definition='project_id.task_properties_definition')`
(`project/models/project_task.py:195`); class in `odoo/orm/fields_properties.py:32`. It is a stored
JSONB column, computed from `project_id` (default values) and `compute_sudo`.

| Layer | Shape | `serichai-db` example (task 8, project 3) |
|---|---|---|
| DB column `project_task.task_properties` | JSON dict `{property_name: value}`, only names with a value | `{"1ab160cbb8328083": 0, "a53bc835cf1914f1": "101 TT", ...}` |
| Definitions `project.project.task_properties_definition` | list of dicts `name`, `string`, `type`, optional `default`, `suffix`, `comodel`, `selection` ... | `[{"name": "1ab160cbb8328083", "type": "float", "string": "มูลค่าโครงการ", "suffix": "บาท", "default": 0}, ...]` |
| Python record access `task.task_properties` | `Property` object (`fields_properties.py:775`), an `abc.Mapping` keyed by **internal name** | `task.task_properties['1ab160cbb8328083']` |
| `task.read(['task_properties'])` / `web_read` | list of definition dicts merged with `value` (definition order) | `[{"name": "1ab160cbb8328083", "string": "มูลค่าโครงการ", "type": "float", "value": 0, ...}, ...]` |

Consequences for the compute:

- `Property.__getitem__` returns `prop.get('value') or False`: a float `0` comes back as `False`, an
  unset value as `False`, an unknown name raises `KeyError` (so `.get(name)` returns `None`).
  Selection returns the label, many2one/many2many a recordset, tags a joined string. Verified:
  `{name: 60000000.0} -> 60000000.0`, `{name: 0} -> False`, `{} -> False`, `{other: 5} -> False`.
- **Decision**: find the internal name from the project's definition by label, then read
  `task.task_properties.get(name)` and accept it only when the definition `type` is `integer`,
  `float` or `monetary` (number) or `char` / `text` (parse). Any other type (`many2one` returns an id
  recordset, `selection`, `tags`, `boolean`, `date`...) gives 0 (spec edge case "list or another
  non-amount type"). `bool` is excluded explicitly (`True` is an `int`).
- The compute reads the record format, not `read()`, so 009's `read()` filter (hidden properties)
  never applies to it; it runs as superuser anyway (`compute_sudo` defaults to `store`).
- Text parsing: remove whitespace and `,`, then `fullmatch(r'[-+]?\d+(\.\d+)?')`. `float()` alone is
  rejected because it accepts `"nan"`, `"inf"`, `"1e9"` (verified `float('nan')`, `float('inf')`).
  Non-finite numbers are rejected as well.
- Today in `serichai-db`: 5 projects, 11 tasks, one project (id 3) defines the property as `float`;
  both of its tasks hold `0`.

## V4. `nulls last` in `default_order` (verified, dropped)

- Server: `regex_order` (`odoo/orm/models.py:93-104`) accepts `field asc nulls last`.
- Client: `stringToOrderBy` (`web/static/src/search/utils/order_by.js`) splits each term on spaces
  and only reads the direction when there are exactly 2 tokens; `"date_deadline asc nulls last"`
  silently loses `nulls last`, and `"x desc nulls last"` would even become **ASC**. `orderByToString`
  sends `name ASC|DESC` only. List and kanban parse `default_order` with this function
  (`kanban_arch_parser.js:16`).
- PostgreSQL: `ASC` defaults to `NULLS LAST` (verified: `ORDER BY x ASC` returned
  `2025-01-01, 2026-01-01, NULL`). Generated SQL for the order is
  `COALESCE("is_high_value", FALSE) DESC, "date_deadline" ASC, "id" DESC` (booleans are coalesced by
  `_order_field_to_sql`, so NULL booleans sort as False).
- **Decision (round 4)**: `default_order="priority desc, is_high_value desc, state, date_deadline asc, id desc"`,
  with no `nulls` clause, because the priority star supersedes the configuration sort. `id desc`
  keeps today's tie-break (spec assumption "most recently created first").
- Priority (verified): `project.task.priority` is a `Selection` of `'0'` Low, `'1'` Medium,
  `'2'` High and `'3'` Urgent, with `default='0'` and an index
  (`project/models/project_task.py:154-159`).
  - It is stored as varchar, so `DESC` on single-character strings gives `'3','2','1','0'`.
  - The generated SQL is `"priority" DESC, COALESCE("is_high_value", FALSE) DESC, "date_deadline" ASC,
    "id" DESC` (shell probe).
  - In `serichai-db` all 11 tasks are `'0'`, with no NULLs. A NULL priority would sort first under
    `DESC`; that is the same behaviour as core `_order`, and it is accepted.
- Client: each of the 4 comma-separated terms has exactly 2 tokens, so `stringToOrderBy` parses all
  of them, direction included.

## V5. Interaction with spec 009 and which views to inherit (verified; Gate 2 round 5)

**How 009 hides properties at the ORM level** (`serichai_project_access/models/`, verified by reading):
- `project.task.read()` drops the hidden property dicts from `task_properties` in the returned rows.
  `project.project.read()` drops hidden definitions. `web_read` / `web_search_read` call `read()`
  (`web/models/models.py:117`), so the web client never receives hidden properties.
- `_search` / `_read_group` raise `AccessError` only for refs to `task_properties.*` (domain,
  group-by, order). `get_property_definition` returns `{}` for a hidden name. `export_data` raises
  `AccessError` when exporting `task_properties` of a project with hidden properties.
- Nothing else. It does **not** override `fetch` / `_fetch_query`, field `__get__` or
  `check_field_access`. Record field access (`task.task_properties`,
  `project.task_properties_definition`) goes through `_fetch_field` -> `fetch()` -> SQL, with ACL and
  record rules only (`odoo/orm/models.py:3754-3812`). So it returns the **real** amount, even for a
  hidden user, and raises nothing (the user can read granted tasks and projects).

**Consequences and decisions (round 5: no 009 dependency, no hook, no 009 changes)**:
- A `project_value` computed from field access would show hidden amounts to restricted users,
  because 009's `read()` filter only touches the `task_properties` key. **Decision**: compute
  `project_value` (non-stored, `depends_context('uid')`, no sudo) from `self.read(['task_properties'])`
  of the current user. A hidden property is absent from that result, so the label is not found and the
  value is 0.
  - This relies only on the generic rule "what `read()` returns is what the user may see", so any
    property-hiding module that works through `read()` is honoured without being named.
  - A task the user cannot read raises `AccessError` from `read()`. That exception is caught and the
    whole batch shows 0. It is a legitimate addition to the allowed list: it is the specific,
    expected error of a permission check, and FR-007 forbids errors in lists and exports. Nothing
    else is swallowed.
  - Export of `project_value` goes through the compute, so it also gives 0. `project_value` is not
    stored, so it cannot be searched, grouped or ordered.
- `is_high_value` stays stored and computed as superuser from field access, so the order is the same
  for everyone. Hidden users can read it and filter on it; this is accepted (the position already
  shows it). Our order and filter never name `task_properties.*`, so 009 raises no `AccessError`.
- Column and High Value filter are shown to everyone; hidden users see 0 in the column. There is no
  `get_view` stripping.
- Assumption (risk R1): a future module that hides properties only in views, or only in `web_read`,
  would not zero the amount.
- Trade-off: the Project Value column cannot be sorted by clicking its header, because it is not stored.

**Views and actions in scope**

| View (xml id) | Kind | Used by | Gets the new order |
|---|---|---|---|
| `project.project_task_view_tree_main_base` | root list | base of the **portal sharing** list (`project_sharing_project_task_view_tree`, primary) | **No - do not inherit** (FR-010, portal `SELF_READABLE_FIELDS`) |
| `project.project_task_view_tree_base` | primary list, `js_class=project_task_list` | parent of `view_task_tree2`, milestone list, templates list | **Inherit here** |
| `view_task_tree2` -> `open_view_my_tasks_list_view`, `open_view_all_tasks_list_view`; `serichai_project_access.project_task_view_list_access` (`serichai_access_task_list`) | primary children | All Tasks, My Tasks, project tasks, restricted list | yes, by inheritance |
| `project.view_task_kanban` | root kanban, `js_class=project_task_kanban` | project tasks; children: my-task, all-task, default-project, milestone kanban, `serichai_project_access.project_task_view_kanban_access` | **Inherit here** |
| `project.project_task_templates_list` / `_kanban` | primary children | task templates | yes, by inheritance (accepted: internal task screens) |
| `project_todo.project_task_view_todo_kanban`, `project_sharing_*` kanban/search, `project_sub_task_view_kanban_mobile` | standalone | To-do app, portal, mobile subtasks | untouched |

- Extensions on a primary parent propagate to its primary children (an extension on a child would
  apply after the parent's, if template views ever need the core order back).
- Actions: `ir.actions.act_window` has no order field in 19 (`base/models/ir_actions.py:307-333`);
  only the `orderedBy` context key could override, and no project or serichai action sets it.
  `ProjectTaskRelationalModel` only rewrites the domain. So the arch `default_order` takes effect for
  `action_view_all_task`, `action_view_my_task`, `act_project_project_2_project_task_all`,
  `project_task_action_from_partner` and 009's `project_task_action_access_all` / `_project`.
- Model `_order` (`priority desc, sequence, date_deadline asc, id desc`) is **unchanged**, so portal,
  reports, exports and RPC callers keep their order (FR-010, SC-008).
- Search filter goes into `project.view_task_search_form` (internal), not `_base` (the portal search
  `project_sharing_project_task_view_search` is separate; adding portal-unreadable fields to shared
  bases would break portal views).

## V6. Compute dependencies (verified; Gate 2 round 4)

- **Decision**: `@api.depends('task_properties', 'project_id')`. The flag is recomputed instantly only
  when the task's own properties change. The `project_id.task_properties_definition` dependency is
  removed, and `set_values` no longer recomputes anything.
- Odoo cannot depend on one property key. Any edit of `task_properties` recomputes the flag: one
  label lookup and one parse, which is cheap.
  - **No guard is added.** `Field.write` already drops unchanged values (`_filter_not_equal`,
    `odoo/orm/fields.py:1503-1518`), so an unchanged flag is never marked dirty or written to SQL.
- Project move (verified): `task_properties` is a computed field with `_depends == ('project_id',)`
  (shell probe; `fields_properties.py:93-102`). Its `_compute` re-applies the new project's
  definition and defaults, so values of properties the new project does not define are dropped.
  Writing `project_id` therefore recomputes `task_properties` and, transitively, our flag.
  - `project_id` in our depends is redundant but is **kept**. It makes FR-006 explicit, it also
    covers a move where the merged properties come out equal, and the ORM deduplicates it, so it
    costs nothing.
- Definition edits (rename, remove, add) and threshold changes take effect on Recalculate, which is
  the normal step after such a change. The Settings block carries a hint saying so.
- Limitation: the non-stored, per-user `project_value` reads the live definition. After a definition
  change it can show the new amount (often 0) while `is_high_value` still holds the old value, until
  Recalculate.

## V7. Threshold, settings, recalculation, install (verified, revised at Gate 2)

- Key `serichai_project_configuration.high_budget_threshold`. It is module-prefixed; the earlier
  reference plan used `project_task_budget_sort.high_budget_threshold`, a module that does not exist
  here.
- `config_parameter=` cannot hold 0: `res.config.settings.set_values` stores
  `repr(value) if value else False`, which deletes the param for 0 (`base/models/res_config.py:340-341`).
  `get_values` falls back to the field default when the param is missing.
- **Decision (FR-014)**: the settings field `serichai_high_value_threshold` is a plain Float with no
  `config_parameter`. `get_values` (`@api.model` in 19) returns `_get_high_value_threshold()`;
  `set_values` always writes `repr(value)`, so 0 is stored as `"0.0"`. The prefix follows
  `serichai_expanded_access_project_id`, because all settings share one transient model.
- Reader `_get_high_value_threshold()`:
  - Unset (`False`/`None`/`''`) -> 50M. Note `float(False) == 0.0`, so this check comes first.
  - `"0"` / `"0.0"` -> 0.
  - Letters (`TypeError`/`ValueError`), negative or non-finite values -> 50M, with no warning.
- Admin only: the `res.config.settings` ACL is `base.group_system` only
  (`base/security/ir.model.access.csv:131`). The block also has `groups="base.group_system"`, and the
  action checks the group again.
- Saving the threshold never recomputes tasks (round 4). The admin clicks "Recalculate high-value
  flag" afterwards (FR-015); a muted hint under the button says so.
- Button flow: the settings controller (`settings_form_controller.js:67-80`) asks to save a dirty
  form before it runs a button (Save runs `execute`), so the action reads the stored parameter.
- Recalculation `_recompute_high_value()` covers every task (archived included) in batches of 1000,
  and one bad task never stops a batch (FR-015, US4-4). Details are in design.md.
- Install in portions (FR-017): `_auto_init` marks a **new** computed stored column for computation
  on every row at once (`odoo/orm/models.py:3229-3241`). **Decision**: `pre_init_hook` creates the
  column with `odoo.tools.sql.create_column` (core precedent `sale_management/__init__.py`), so the
  ORM computes nothing; `post_init_hook` then runs the batched recalculation.
- Fail-safe parsing: a small `try/except (ValueError, TypeError, KeyError, AttributeError)` around one
  task, then `_logger.debug(..., task.id, exc_info=True)`, with no bare `except`. Support turns it on
  with `--log-handler odoo.addons.serichai_project_configuration:DEBUG`.

## V8. Tests (planned)

- `serichai_project_configuration/tests/test_budget_sort.py` covers US1-US5. That includes threshold
  0, "property deleted, flag unchanged until the explicit recalculation", and the priority-first order.
- It also covers US6 generically:
  - `project.task.read` is patched to strip the property, then to raise `AccessError`.
  - In both cases `project_value` must be 0 with no exception, and `is_high_value` and the list
    order must be unchanged.
  - No 009 is needed. 009's own tests are unchanged, and no test file is added there.
- Run on a dedicated database (name asked at implementation time; see quickstart.md). The
  constitution gate (`-u serichai_project_configuration` on `serichai-db`) runs afterwards, and the
  user runs it.

## V9. Known limitations (documented, accepted by spec)

1. Kanban drag-and-drop inside a column writes `sequence`, but `sequence` is still not a sort key
   (the order is priority, flag, deadline, id), so the card jumps back on reload. Moving a card to another stage works.
2. A threshold change, or a change to a project's property definition, needs the Recalculate
   action. Tasks edited in the meantime already use the new rule. Until Recalculate, the Project Value
   column can disagree with the flag (V6).
3. Position in the list, the High Value filter or an RPC read/search of `is_high_value` lets a user
   infer "high value" for tasks whose amount they cannot see. Their column shows 0 (accepted, Gate 2
   rounds 3 and 5).
4. The Project Value column cannot be sorted from its header.

## D1. Field names

| Choice | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| Task amount | `project_value` (Float, non-stored, per user) | Spec term "project value"; no clash in any addon (grep); the repo uses plain descriptive names (`is_expanded_access_task`, `access_task_detail`, `mrp_production_count`) | `x_project_value`: `x_` is the namespace of manual/Studio fields (`ir.model.fields` requires it for `state='manual'`), so a module field using it would look user-created and could collide with a Studio field. `budget_amount`: not the business term |
| Task flag | `is_high_value` (Boolean, stored) | `is_` prefix for booleans, as in `is_expanded_access_task` and core `is_closed` | `x_high_budget` |
| Settings | `serichai_high_value_threshold` | the shared transient model needs a module prefix | `high_budget_threshold` (collision-prone) |

## D2. No link with spec 009 (decided at Gate 2, round 5)

- **Decision**: `serichai_project_configuration` depends on `project` only and contains no 009
  reference (FR-001). `serichai_project_access` is not modified: no dependency, no version bump, no
  code, no tests. There is no inter-module contract.
- The user accepts that a hidden user simply sees 0, through `read()` (V5), and sees the filter.
- **Alternatives rejected**:
  - 009 depends on configuration (rounds 2-4): rejected by the user.
  - An `auto_install` bridge module: rejected by the user.
  - An overridable hook in the configuration module: rejected by the user. Without a dependency,
    Odoo loads both modules at the same depth in alphabetical order
    (`odoo/modules/module_graph.py:208-225`), so the access module's override would sit under the
    configuration module's base method and be ignored.

## D3. Where the value is computed

- **Decision**: a stored computed boolean on `project.task`, sorted in SQL. The amount is a non-stored
  display field computed from the user's own `read()` (V5).
- **Alternatives rejected**:
  - Ordering by `task_properties.<name>`: the name differs per project, it raises 009's AccessError
    for hidden users, and it gives no text parsing.
  - A non-stored flag: it cannot be ordered.
  - Overriding `_order`: it changes the portal and report order (FR-010).
  - An OWL client-side sort: it breaks paging.
