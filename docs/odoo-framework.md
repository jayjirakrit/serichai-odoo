# Odoo 19.0 Framework: Core Logic and Server Mechanisms

Architecture reference for the Serichai ERP deployment, based on a scan of the
vendored core in `odoo/odoo/` (`version_info = (19, 0, 0, FINAL)`). Paths are
relative to `odoo/odoo/` unless they start with `addons/` (meaning
`odoo/addons/`) or name a custom addon. Line numbers refer to that source. The
code was read, not executed. Concepts from the official reference
(https://www.odoo.com/documentation/19.0/developer/reference.html) come from
general knowledge; the page itself was not fetched.

The client side (OWL, services, views, the relational model) is covered in
[`odoo-web-framework.md`](odoo-web-framework.md).

Contents

Part I: ORM and business layer

1. Layers
2. Module system
3. Model definition and inheritance
4. Fields
5. Method decorators
6. Environment, records, cache
7. Recordset API and CRUD lifecycle
8. Computed fields and dependency tracking
9. Search, domains, ordering, aggregation
10. Security layers
11. Views and actions (server side)
12. QWeb and PDF reports
13. Data files, XML IDs, upgrades
14. Caching (`ormcache`)
15. Exceptions
16. Cross-cutting services in `base` and `mail`
17. Testing

Part II: Server framework

18. Boot sequence
19. Server models: threaded, prefork, gevent
20. WSGI entry and the `Application` object
21. `_serve_db`: cursor and transaction strategy
22. Routing and dispatch
23. Multi-process coherence (signaling)
24. Database layer
25. Cron engine
26. Configuration cheat-sheet
27. Implications for this repo

---

# Part I: ORM and business layer

## 1. Layers

```
 WSGI / server      service/server.py   Threaded | Gevent | Prefork(+WorkerHTTP, WorkerCron)
 HTTP + routing     http.py             Application → Request → Dispatcher → @route controllers
 Module system      modules/            module.py, module_graph.py, loading.py, migration.py
 Registry           orm/registry.py     one per database, holds all model classes
 ORM                orm/                models.py (BaseModel, 7.1k lines), fields*.py, environments.py,
                                        domains.py, decorators.py, commands.py, table_objects.py
 DB access          sql_db.py           Cursor, connection pool, savepoints
 Base addon         addons/base         ir.* meta-models, res.*, security, views, QWeb, reports, assets
 Web addon          addons/web          JSON-RPC model API (web_read, web_save, …), web client
```

The framework itself is small. Most behaviour (views, access rules, cron,
reports, assets, routing) is implemented as models in `addons/base`, which the
ORM then drives. In Odoo 19 the ORM was split out of the old `models.py` and
`fields.py` into the `orm/` package. `odoo.models`, `odoo.fields` and
`odoo.api` remain the public import paths (`from odoo import api, fields, models`).

## 2. Module system

**Manifest.** `__manifest__.py` is a dict, merged over `_DEFAULT_MANIFEST`
(`modules/module.py:56`). The keys that matter:

| Key | Meaning |
|---|---|
| `depends` | modules that must load first. Defines load order, MRO order for `_inherit`, and asset order |
| `data` | XML/CSV loaded on install and on every `-u`, in list order (security first, then views, then menus) |
| `demo` | loaded only without `--without-demo` (this repo runs `--without-demo=all`) |
| `assets` | bundle contributions (see the web doc, §2) |
| `auto_install` | `True` (install when all `depends` are installed) or a subset list (`:450`) |
| `application` | shows the module as an app in the Apps menu |
| `pre_init_hook` / `post_init_hook` / `uninstall_hook` | function names in the package's `__init__.py`, called with `env` |
| `external_dependencies` | `{'python': [...], 'bin': [...]}`, checked before install (`:254`) |
| `license` | defaults to `LGPL-3` (`:433`) |
| `version` | `19.0.x.y.z`; drives migration scripts |

**Loading.** `ModuleGraph` (`modules/module_graph.py`) resolves the
dependency order. `load_modules` (`modules/loading.py:340`):
1. Loads `base` first, since the graph can't be computed without it.
2. `load_module_graph` (`:115`) goes through modules in dependency order:
   - imports the Python package, which executes the `class X(models.Model)` definitions;
   - registers each class in the registry;
   - `registry._setup_models__` and `init_models` create or alter tables and columns;
   - runs `pre-` migrations, loads `data` (`load_data` `:41`) and `demo`, runs `post-` migrations.
3. Processes modules marked `to install`, `to upgrade` or `to remove`, runs
   `end-` migrations, then the post-install hooks and tests.

The module state machine lives in `ir.module.module`
(`uninstalled → to install → installed → to upgrade → installed`,
`→ to remove → uninstalled`). If a crash leaves states half-way,
`reset_modules_state` (`loading.py:611`) clears them; cron does this
automatically (§25).

**Registry (`orm/registry.py`).** One `Registry` per database, a process-level
singleton. It is a `Mapping` of model name to model class. It also holds the
field-dependency trigger trees (`get_trigger_tree`), the ormcache LRUs, the
routing cache, and the multi-worker signalling state (§23).

## 3. Model definition and inheritance (`orm/model_classes.py`)

A Python class is a **model definition**. The **model class** `registry['x']` is
built dynamically by combining every definition sharing a `_name`. The comment
block at lines 55–140 of that file describes it and gives the MRO.

| Pattern | Declaration | Effect |
|---|---|---|
| Classical extension | `_inherit = 'a'` (no `_name`) | Modifies model `a` in place. Definitions load in module order and the later one is first in the MRO, so `super()` works. |
| Prototype | `_name='b'`, `_inherit='a'` | New model `b` copying `a`'s fields and methods, with a new table. |
| Mixin | `_inherit=['mail.thread', ...]` | Multiple parents. This is how chatter and activities are added. |
| Delegation | `_inherits={'res.partner': 'partner_id'}` | Composition. The child gets a many2one and transparently exposes the parent's fields. `res.users` works this way. |

At load time `_setup` and `_setup_fields` resolve inherited fields. Fields that
are not overridden are shared between registries to save memory.

**Model types.** `Model` (persistent, `_auto=True`, `models.py:7057`),
`TransientModel` (wizard-like, vacuumed by `ir.autovacuum`; see
`models_transient.py`), `AbstractModel` (no table; mixins and service-like
models such as `ir.qweb`, `ir.http`).

**Class attributes** (`orm/models.py:392-464`):

| Attribute | Default | Purpose |
|---|---|---|
| `_name` / `_description` | — | technical name / human label (a missing `_description` is warned about) |
| `_inherit` / `_inherits` | `()` | see the table above |
| `_table` / `_auto` | derived from `_name` / `True` | SQL table, and whether the ORM manages its schema |
| `_table_query` | `None` | makes the model a read-only SQL view (reporting models) |
| `_order` | `'id'` | default `ORDER BY` for `search` |
| `_rec_name` / `_rec_names_search` | `name` / `None` | `display_name` source / fields searched by `name_search` |
| `_parent_name` / `_parent_store` | `parent_id` / `False` | hierarchy; `_parent_store` maintains `parent_path` for fast `child_of` |
| `_active_name` | `active` (if the field exists) | archived records are hidden from `search` unless `active_test=False` |
| `_fold_name` | `fold` | folded kanban columns |
| `_check_company_auto` | `False` | run `_check_company()` on create/write for `check_company=True` fields |
| `_log_access` | `True` | adds `create_uid/date`, `write_uid/date` |
| `_allow_sudo_commands` | `True` | whether x2many commands are allowed on this model in sudo mode |

**Constraints and indexes are class attributes in Odoo 19.** `_sql_constraints`
is replaced by `orm/table_objects.py`:

```python
class ResGroups(models.Model):
    _name_uniq = models.Constraint("UNIQUE (privilege_id, name)", "The name of the group must be unique!")
    _active_idx = models.Index("(active) WHERE active IS TRUE")      # CREATE INDEX res_groups__active_idx …
    _code_uniq  = models.UniqueIndex("(company_id, code)")
```

`Constraint` (`:79`), `Index` (`:125`), `UniqueIndex` (`:185`). The SQL object is
named `{table}_{attribute}`. `_auto_init` creates them, and a violated
constraint's message reaches the user through `retrying` (§21).

## 4. Fields

All field classes derive from `Field` (`orm/fields.py:92`). The `odoo.fields`
module re-exports them.

| Type | Class (file:line) | Column / storage | Notes |
|---|---|---|---|
| `Boolean` | `fields_misc.py:22` | `bool` | |
| `Integer` | `fields_numeric.py:17` | `int4` | |
| `Float` | `fields_numeric.py:60` | `numeric` or `float8` | `digits=(16, 2)` or a `decimal.precision` name |
| `Monetary` | `fields_numeric.py:184` | `numeric` | needs a `currency_field` (default `currency_id`) |
| `Char` / `Text` | `fields_textual.py:465 / 530` | `varchar` / `text` | `translate=True` stores JSONB keyed by lang |
| `Html` | `fields_textual.py:545` | `text` | sanitized on write (`sanitize=True` and its variants) |
| `Selection` | `fields_selection.py:20` | `varchar` | `selection=[...]` or a method name; `selection_add` when extending, with `ondelete` |
| `Date` / `Datetime` | `fields_temporal.py:106 / 191` | `date` / `timestamp` | datetimes are naive UTC in the DB; the client converts to the user's tz |
| `Binary` / `Image` | `fields_binary.py:29 / 246` | `ir.attachment` (`attachment=True` default) | `Image` resizes (`max_width`, `max_height`) |
| `Json` | `fields_misc.py:55` | `jsonb` | |
| `Many2one` | `fields_relational.py:213` | `int4` FK | `ondelete='set null'/'restrict'/'cascade'`, `domain`, `check_company`, `auto_join`/`bypass_search_access` |
| `One2many` | `fields_relational.py:836` | none (inverse of a many2one) | `inverse_name` required |
| `Many2many` | `fields_relational.py:1199` | relation table | `relation`, `column1`, `column2`; derived automatically if omitted |
| `Reference` / `Many2oneReference` | `fields_reference.py:14 / 59` | `varchar` `model,id` / `int` + model field | |
| `Properties` / `PropertiesDefinition` | `fields_properties.py:32 / 844` | `jsonb` | user-defined fields: the definition lives on a parent record (e.g. `project.project.task_properties_definition`), the values on the child (`project.task.task_properties`) |

**Common attributes** (documented at `fields.py:97-250`): `string`, `help`,
`required`, `readonly`, `index` (`True`/`'btree'`, `'btree_not_null'`,
`'trigram'`), `default` (value or callable), `groups` (comma-separated xmlids,
which hide the field from users outside those groups), `copy`, `store`,
`company_dependent` (value per company, stored as JSONB), `tracking` (with `mail.thread`),
`aggregator` (`'sum'`, `'avg'`, `'max'`, … used by read_group; this replaces
`group_operator`), `group_expand` (show empty groups such as kanban stages),
`search` (method implementing search on a non-stored field), `precompute`,
`compute_sudo`, `recursive`, `inverse`, `related`.

**Computed and related fields** (§8): `compute='_compute_x'` +
`@api.depends(...)`. Add `store=True` to persist the value (it can then be
searched and grouped), `inverse='_inverse_x'` to make it writable, and
`search='_search_x'` to make a non-stored field searchable. `related='a.b'` is
shorthand for a compute plus an inverse.

**Odoo 19 search-method convention.** Before calling a field's `search=`
method, the ORM normalises operators: equality on booleans arrives as
`in`/`not in` with a set of values. A method can return `NotImplemented` for
operators it does not handle, and can return a `Domain` object. The custom
`_search_is_expanded_access_task` follows this pattern
(`serichai_project_security/models/project_task.py`).

**x2many write commands** (`orm/commands.py:11`):
`Command.create(vals)` (0), `update(id, vals)` (1), `delete(id)` (2),
`unlink(id)` (3), `link(id)` (4), `clear()` (5), `set(ids)` (6). Writing a
plain list of ids to a many2many is not allowed; use `Command.set(ids)`.

## 5. Method decorators (`orm/decorators.py`, exposed as `odoo.api`)

| Decorator | Line | Use |
|---|---|---|
| `@api.model` | `:309` | `self` is just the model (an empty recordset). On `create` it becomes `model_create_multi` |
| `@api.model_create_multi` | `:353` | `create(vals_list)`. **Every `create` override must take a list** |
| `@api.depends(*paths)` | `:244` | dependencies of a compute method. Paths can traverse relations (`'line_ids.price'`) |
| `@api.depends_context(*keys)` | `:269` | context keys that affect the computed value (`company`, `lang`, custom keys) |
| `@api.constrains(*fields)` | `:88` | Python validation, run after create/write when one of the fields is written; raise `ValidationError`. Only **direct** field names trigger it, not dotted paths |
| `@api.onchange(*fields)` | `:185` | form-only UI helper; runs on the pseudo-record in `onchange()`; may return `{'warning': …}` |
| `@api.ondelete(at_uninstall=False)` | `:126` | pre-unlink checks that are skipped during module uninstall |
| `@api.autovacuum` | `:295` | method run daily by the `ir.autovacuum` cron |
| `@api.private` | `:324` | public-named method that **cannot be called over RPC** |
| `@api.readonly` | `:341` | method callable over RPC on a read-only (replica-capable) cursor |

RPC exposure rule: any method whose name does not start with `_` and isn't
`@api.private` can be called by any authenticated user through
`/web/dataset/call_kw` or `/json/2`. Access rights still apply to what it
touches, but the method body runs. Business methods that should not be
callable from the client must be prefixed with `_`.

## 6. Environment, records, cache

**Environment (`orm/environments.py:40`).** The tuple `(cr, uid, context, su)`.
It is immutable; `env(user=..., context=..., su=True)` (`:126`) returns a new
one, and `with_user`, `with_context`, `with_company`, `sudo` are shortcuts on
recordsets (`models.py:5952-6019`). Useful properties:

| Property | Line | Returns |
|---|---|---|
| `env.ref(xmlid, raise_if_not_found=True)` | `:151` | record by XML ID |
| `env.user` | `:208` | current `res.users` |
| `env.company` / `env.companies` | `:216 / :246` | active company / allowed companies, from the `allowed_company_ids` context key (the company switcher) |
| `env.lang` | `:297` | validated language code |
| `env.is_superuser()` / `is_admin()` / `is_system()` | `:178-187` | sudo mode / Settings admin / technical admin |
| `env.execute_query(SQL(...))` | `:527` | runs a composed query after flushing the fields it references |

A `Transaction` (`:552`) is shared by all environments of one cursor. It holds
the record cache, pending computations, protected fields and the to-flush
bookkeeping.

**Recordsets.** A record is a recordset of `_ids` plus an environment. They are
immutable and ordered, with set operations (`|`, `&`, `-`).

**Field access.** The `Field.__get__` descriptor looks in the cache. On a miss
it prefetches the field for all ids in `_prefetch_ids`, so a loop over records
issues one query, not N. If the field is computed it calls
`_compute_field_value` (`models.py:4951`).

**Write-behind.** `write` and `create` update the cache first and mark fields
as to-flush. `flush_model` / `flush_recordset` (`models.py:6351/6365`) and
`env.flush_all()` (`environments.py:380`) send them to SQL. Flushing happens
automatically before searches, `read_group` and at commit. When using
`cr.execute` directly you must flush the affected fields yourself, and
`invalidate_model` / `invalidate_recordset` (`:6707/6722`) afterwards if you
wrote data. `env.execute_query` with `SQL` objects does the flushing for you.

**Common context keys:** `lang`, `tz`, `uid`, `allowed_company_ids`,
`active_test` (False shows archived records), `default_<field>` (create
defaults; this is how `default_project_id` reaches a new task),
`tracking_disable` / `mail_notrack` / `mail_create_nolog` (mail), `bin_size`
(binary fields return their size instead of content).

## 7. Recordset API and CRUD lifecycle

**Recordset helpers** (`orm/models.py`): `browse(ids)` (`:5881`), `exists()`
(`:5543`), `ensure_one()` (`:5929`), `mapped(path|fn)` (`:6126`),
`filtered(fn|path|Domain)` (`:6184`), `filtered_domain(domain)` (`:6250`),
`grouped(key)` (`:6224`, returns a dict of recordsets), `sorted(key, reverse)`
(`:6261`), `copy(default)` (`:5528`, with `copy_data` `:5404` honouring
`copy=False`), `get_external_id()` (`:5714`), `action_archive` /
`action_unarchive` (`:5795/5806`), `_has_cycle()` (`:5622`).

**Reading.** `read(fields)` (`:3469`) returns a list of dicts and is the
access-checked path. `web_read(spec)` (`addons/web/models/models.py:109`) calls
`read` (`:117`) and then expands relational fields recursively from the
specification. `fetch(fields)` (`:3775`) only loads into the cache. Overriding
`read` therefore also affects the web client's form loads.

**Naming.** `display_name` is computed by `_compute_display_name` (`:1425`)
from `_rec_name`. `name_search` (`:1514`) uses `_search_display_name`
(`:1442`) over `_rec_names_search`. `name_create` (`:1493`) backs the "Create
'xyz'" entry in many2one dropdowns.

**`default_get(fields)`** (`:1271`): field `default=`, then `ir.default`
user/company defaults, then `default_*` context keys.

**`create(vals_list)`** (`:4611`), always batch:
1. Apply defaults (`_add_missing_default_values` `:1546`) and check access (`check_access('create')`).
2. Split values into stored fields, inherited fields (forwarded to the `_inherits` parent) and relational commands. Compute `precompute=True` fields.
3. `_create` runs the INSERT.
4. Fill the cache and call `modified()` to trigger dependent recomputes.
5. Process x2many commands.
6. Run the `@api.constrains` checks (`_validate_fields` `:1253`) and `_check_company` (`:4009`) if `_check_company_auto`.

**`write(vals)`** (`:4334`): check access; `modified(before=True)` to find
records whose computed values will change; update the cache and `_write`;
`modified()` again; run the inverse methods for computed-stored fields; run the
constraints.

**`unlink()`** (`:4194`) runs the `@api.ondelete` checks, applies the
`ondelete` behaviour of relational fields (cascade, set null, restrict) and
removes the related `ir.model.data`, `ir.attachment` and `ir.default` rows.

**`onchange(values, field_names, fields_spec)`** (`:6993`, extended by the web
addon at `addons/web/models/models.py:1965`) builds a `new` record
(NewId) from the form's current values, applies `@api.onchange` methods and
computed fields, and returns only the changed values, shaped by the spec.
Nothing is written to the database.

Rule: override `create`, `write` and `unlink` to add business logic, always
calling `super()`. Logic that must run on UI edits only goes in
`@api.onchange`; logic that must always hold goes in a compute or a
`@api.constrains`.

## 8. Computed fields and dependency tracking

- `@api.depends('a', 'b.c')` builds a **trigger tree** (`registry.get_trigger_tree`, `TriggerTree`), an inverted index from "a field changed" to "which fields on which records must be recomputed".
- `modified()` (`models.py:6754`) walks that tree, using `_modified_triggers` (line 6860) to translate through relations. It invalidates the cached values of dependents, and for stored fields queues them with `env.add_to_compute` (`environments.py:453`).
- Stored fields are recomputed lazily, on the next read or at flush (`_recompute_field`, line 6946). Non-stored fields are recomputed when the cache is cold.
- `env.protecting` (`environments.py:411`) stops recursion when a compute writes to its own field.
- `@api.depends_context('company')` includes context keys in the cache key (`env.cache_key`, `:471`); `company_dependent` fields use this.
- Related fields are computed fields with an auto-generated path and inverse.
- A compute method must assign the field on **every** record in `self`, otherwise the ORM raises `ValueError` ("Compute method failed to assign").
- A non-stored compute with **no** `@api.depends` (like `is_expanded_access_task`) is recomputed whenever the cache is cold, i.e. once per transaction per record. It never goes stale within a request, but it also cannot be grouped or sorted on.
- `@api.onchange` runs only on the form and is not part of the server-side data flow.

## 9. Search, domains, ordering, aggregation

**Domains.** A domain is a list in prefix notation
(`['|', ('a', '=', 1), ('b', '!=', False)]`) or, in Odoo 19, a `Domain` object
(`orm/domains.py:196`, imported as `from odoo.fields import Domain`):

```python
d = Domain('project_id', '=', pid) & ~Domain('stage_id.fold', '=', True)
Domain.AND([d1, d2]); Domain.OR([...]); Domain.TRUE; Domain.FALSE
records.filtered_domain(d)                 # evaluate in Python
```

Operators (`STANDARD_CONDITION_OPERATORS`, `:81`): `=`, `!=`, `in`,
`not in`, `<`, `>`, `<=`, `>=`, `like`, `ilike`, `=like`, `=ilike` (and
negations), `any` / `not any` (sub-domain on a relational field), `any!`
(the same, skipping record rules on the comodel), `child_of` / `parent_of`.
Paths such as `stage_id.name` are rewritten into `any` sub-queries. Searching
a `translate=True` field matches the value in the **current user's language**
(falling back to `en_US`).

**Pipeline.** `search(domain, offset, limit, order)` (`models.py:1363`) →
`_search` (`:5322`): normalise and `optimize()` (`domains.py:417`) the domain,
add record rules (`_apply_ir_rules`), add `active=True` unless
`active_test=False`, compile to a `Query` via `_to_sql`, and order via
`_order_to_sql` (`:5222`). JOINs for related paths are generated lazily.
`search_fetch` (`:1383`) searches and fetches fields in one query;
`search_count` (`:1347`) counts.

**Aggregation.** `_read_group(domain, groupby, aggregates, having, …)`
(`:1861`) is the modern API. It returns plain tuples, one per group:
`_read_group([], ['stage_id'], ['__count', 'allocated_hours:sum'])` →
`[(stage_rec, 12, 40.0), …]`. It and supports `field:granularity` (`day`,
`week`, `month`, `quarter`, `year`) and `aggregate:function`. `read_group`
(`:2749`) is **deprecated**. The web client uses `formatted_read_group` and
`web_read_group` (`addons/web/models/models.py:794, :349`). `group_expand`
(e.g. `_read_group_stage_ids` on `project.task`) adds empty groups, which is
how kanban shows all stages of a project.

## 10. Security layers

| Layer | Model / mechanism | Granularity | Checked in |
|---|---|---|---|
| Menu / action / view visibility | `groups` on `ir.ui.menu`, actions, view nodes | UI only | menu load, `_postprocess_access_rights` (`ir_ui_view.py:1318`) |
| Model ACL | `ir.model.access` (CSV: per group, r/w/c/u) | Model + operation; union across a user's groups | `IrModelAccess.check` (`ir_model.py:2072`) |
| Record rules | `ir.rule` (`domain_force` per group, per operation) | Row. **Global rules (no group) are ANDed; group rules are ORed together**, then ANDed with the global ones | `_compute_domain` (`ir_rule.py:141`), `_apply_ir_rules` in `_search` |
| Field groups | `groups=` on a field | Column | `fields_get`, read/write checks |
| Multi-company | `company_id` + `check_company=True` + company rules | Row | `_check_company` (`models.py:4009`), standard rules using `company_ids` |
| RPC surface | method name prefix `_`, `@api.private` | Method | `call_kw` dispatch |

**Access-check flow** (`models.py:4100-4192`):
`check_access(op)` → `_check_access(op)`: first `ir.model.access.check(model, op)`
(model level), then for non-empty recordsets `ir.rule._compute_domain(model,
op)` and a search of `self` against it. Failing records become an `AccessError`
built by `_make_access_error` (`ir_rule.py:208`), which lists the failing rules
in debug mode. `has_access(op)` (`:4117`) is the boolean form, and
`_filtered_access(op)` (`:4124`) returns the allowed subset.
`check_access_rights` / `check_access_rule` remain as deprecated aliases.

**Rule evaluation context** (`ir_rule.py:38`): `user`
(`env.user.with_context({})`), `company_ids`, `company_id`, `time`, plus
anything added by overriding `_eval_context`. `domain_force` is Python, so
expressions like `[...] if user.has_group('x') else [(1, '=', 1)]` work.
`_compute_domain` is cached with `ormcache` on `(uid, su, model, mode, …context
keys)` (`:138`), so rule results don't change within a session unless the cache
is cleared (editing rules clears it).

**Groups** (`addons/base/models/res_groups.py`). In Odoo 19 groups belong to a
`res.groups.privilege` (`privilege_id`, `:36`), which replaces the old
"category" in the user form. `implied_ids` (`:69`) and the computed
`all_implied_ids` (`:71`) make group membership transitive: belonging to
`project.group_project_manager` implies `project.group_project_user`.
`user.has_group('module.xmlid')` checks the transitive set.

**`sudo()`** bypasses ACLs and record rules (and field `groups`), but not
business logic or constraints. It is the most common source of privilege bugs:
keep sudo'd recordsets local, and never return a sudo'd recordset's data
to the client without filtering it.

## 11. Views and actions (server side)

**Views (`addons/base/models/ir_ui_view.py`).** `ir.ui.view` stores the arch
XML.
- Inheritance: a view with `inherit_id` and `mode='extension'` patches its
  parent with `<xpath expr=… position="inside|after|before|replace|attributes|move">`
  specs (`apply_inheritance_specs` `:944`). `mode='primary'` creates a new
  view that starts from the parent's combined arch. `_get_combined_arch`
  (`:1047`) applies all active inheriting views (`_get_inheriting_views`
  `:724`) in priority order.
- Validation: on install, `_check_xml` (`:427`) validates against RNG schemas
  (`addons/base/rng/`) and `_validate_view` (`:1784`) checks that fields,
  buttons and methods exist and that `groups` are consistent.
- Delivery: the client calls `get_views([(id, type), …], options)`
  (`:2905`). For each view, `get_view` (`:3138`) → `_get_view_cache` (`:3091`,
  ormcached per user groups and language) → `_get_view` (`:2978`) →
  `_get_view_postprocessed` (`:3040`) → `_postprocess_view` (`:1430`). The
  post-processing removes nodes the user's groups don't allow, resolves
  `<field>` metadata, and collects the field list. The response includes the
  `fields_get` of every model touched (`models.py:3343`).
- Modifiers: since Odoo 17, `invisible`, `readonly`, `required` and
  `column_invisible` are plain Python expressions evaluated **on the client**
  (`invisible="state != 'done'"`). The old `attrs`/`states` attributes are
  gone.

**Actions.**
- `ir.actions.act_window`: `res_model`, `view_mode`, `domain`, `context`,
  `target` (`current`, `new`, `fullscreen`), `search_view_id`, `views`.
- `ir.actions.server`: Python code (`model`, `record(s)`, `env`, `action`
  in scope) or multi-step actions. Used as menu targets when the action must
  be computed at runtime (as in `action_open_expanded_access_tasks`).
- `ir.actions.report`: QWeb report (§12).
- `ir.actions.client`: `tag` resolved in the JS `actions` registry.
- `ir.actions.act_url`.
- `binding_model_id` + `binding_type` (`action` or `report`) places an action
  in a model's Action or Print menu.
- `env['ir.actions.act_window']._for_xml_id('module.xmlid')` returns an action
  dict that methods can modify before returning it to the client.

Menus (`ir.ui.menu`) point to actions. A menu is shown if the user has the
menu's `groups` (when set) **and** read access to the action's model.

## 12. QWeb and PDF reports

**QWeb engine** (`addons/base/models/ir_qweb.py`, `IrQweb` `:673`).
`_render(template, values)` (`:685`) compiles the template to Python source
(`_generate_code` `:1025`, cached per template via `_generate_code_cached`
`:991`) and runs it. Directives are compiled by `_compile_directive_<name>`:
`t-if/elif/else` (`:2131`), `t-foreach`/`t-as` (`:2245`), `t-set`/`t-value`
(`:2017`), `t-out` (`:2333`, auto-escaped; pass `Markup` for trusted HTML),
`t-esc` (`:2474`, alias), `t-att-*`/`t-attf-*` (`:1881`), `t-call`,
`t-groups` (`:2225`). Expressions run in a restricted evaluator
(`_compile_expr` `:1564`). The same engine renders website pages, emails
(via `mail.render.mixin`) and reports. Server-side QWeb and the client-side
OWL templates share the syntax but are separate engines.

**Reports** (`addons/base/models/ir_actions_report.py`, `IrActionsReport` `:157`):

```
print button → /report/pdf/<report_name>/<ids>
  → _render_qweb_pdf(report_ref, res_ids, data)          :1033
       ├─ _render_qweb_html → _render_template(template, {docs, doc_ids, doc_model, …})   :1113, :769
       ├─ split the HTML into header / body / footer
       └─ _run_wkhtmltopdf(bodies, header, footer, landscape, paperformat)               :514
  → optional attachment save (attachment / attachment_use fields)
```

- `report_type`: `qweb-pdf`, `qweb-html`, `qweb-text`.
- Templates usually `t-call="web.external_layout"` (company header and
  footer) or `web.basic_layout`, and wrap each doc in `web.html_container`.
- Paper format: `paperformat_id` on the report or company (`get_paperformat`
  `:288`).
- A custom `_get_report_values(docids, data)` on a model named
  `report.<module>.<template>` can supply extra values (`_get_rendering_context_model` `:1121`).
- `wkhtmltopdf` (0.12.x, patched Qt build) must be installed on the host;
  `web.report_assets_pdf` provides the CSS. Fonts (including Thai) come from
  the host's fontconfig, so a missing Thai font prints boxes.

## 13. Data files, XML IDs, upgrades

- `ir.model.data` maps `module.xml_id` to `(model, res_id)`. Records created
  by a module are owned by it and deleted when it is uninstalled.
  `noupdate="1"` (on `<data>`) protects records from being overwritten on
  upgrade; they are only created on install. Use `env.ref('module.xml_id')`.
- `tools/convert.py` loads XML. Tags: `<record>` (`_tag_record` `:336`) with
  `<field name eval|ref|search|type="xml|html|base64">`, `<template>` (`:469`,
  shorthand for a QWeb `ir.ui.view`), `<menuitem>` (`:275`), `<function>`
  (`:269`, calls a model method), `<delete>` (`:248`), `<asset>` (`:545`).
  CSV files load into the model named by the file
  (`ir.model.access.csv`).
- References to records of other modules must be fully qualified
  (`ref('project.group_project_user')`), and that module must be in `depends`.
- Upgrades: when the manifest `version` increases, scripts in
  `migrations/<version>/{pre,post,end}-*.py` run (`MigrationManager`,
  `modules/migration.py:58`) with `migrate(cr, version)`. `upgrade_code/`
  holds the scripts run by `odoo-bin upgrade_code` to rewrite custom
  source between versions (e.g. `18.1-00-sql-constraint.py` converts
  `_sql_constraints` to `models.Constraint`).
- `_auto_init` (`models.py:3170`, in `init_models`) creates or alters
  columns, adds constraints and indexes, and records everything in `ir.model.*`.
  It **does not drop** columns that are no longer used. `init()` (`:3250`)
  is the hook for creating SQL views or extra indexes.

## 14. Caching (`ormcache`)

`tools/cache.py`:
- `@ormcache('arg', 'self.env.uid', …)` (`:61`) memoises a method in a
  registry-level LRU. The key is built from the listed expressions, so
  anything that affects the result must be in it. Return values must be
  immutable or copied (a cached list mutated by a caller corrupts the cache).
- `@ormcache_context('arg', keys=('lang',))` (`:163`) adds context keys.
- Caches are named (`default`, `routing`, `templates`, `assets`, `groups`,
  `stable`). `registry.clear_cache('default')` clears locally and signals
  other workers (§23).
- `SIGUSR1` (threaded) logs hit/miss stats (`log_ormcache_stats` `:183`).
- Typical cached things: rule domains (§10), `ir.model.access` checks, view
  archs, `ir.config_parameter.get_param` (cached and cleared on `set_param`),
  `user.has_group`, translations.

The record cache (§6) is a separate, per-transaction cache. ormcache survives
across requests in the same worker.

## 15. Exceptions (`exceptions.py`)

| Exception | Line | Shown in the client as | Typical use |
|---|---|---|---|
| `UserError` | `:9` | warning dialog | business rule violated |
| `ValidationError` | `:119` | "Validation Error" dialog | `@api.constrains`, SQL constraint |
| `AccessError` | `:77` | "Access Error" dialog | ACL or rule failure, custom guards |
| `MissingError` | `:99` | "Missing Record" | record deleted or never existed |
| `AccessDenied` | `:39` | login failure | authentication |
| `RedirectWarning` | `:24` | dialog with a button to an action | "configure X first" |
| `LockError` | `:109` | warning | row lock not acquired |
| `ConcurrencyError` | `:128` | retried silently (§21) | serialization failure |

Raising any of them rolls back the whole request transaction. Messages
should be translated with `self.env._("...")` (Odoo 18+; `_()` from
`odoo.tools.translate` still works). Other exceptions surface as "Odoo Server
Error" with a traceback.

## 16. Cross-cutting services in `base` and `mail`

| Service | API | Notes |
|---|---|---|
| `ir.config_parameter` | `get_param(key, default)` / `set_param` (`ir_config_parameter.py:60/82`) | System parameters (string values). Read with `sudo()` because only admins have read access |
| `res.config.settings` | `config_parameter='key'` on a field | Settings screens; a transient model whose fields map to parameters, groups or modules |
| `ir.sequence` | `next_by_code(code)` | `standard` (PG sequence, may have gaps) or `no_gap` (row lock, serialises) |
| `ir.attachment` | `_storage()` (`ir_attachment.py:88`) | Filestore under `data_dir/filestore/<db>` by default (`ir_attachment.location`), deduplicated by checksum. The filestore must be backed up with the DB |
| `ir.default` | `_get_model_defaults` (`ir_default.py:162`) | user- and company-specific defaults ("Set Default" in debug) |
| `ir.cron` | §25 | scheduled jobs |
| `ir.autovacuum` | `@api.autovacuum` | daily cleanup; transient models vacuumed here |
| `mail.thread` | `_inherit = ['mail.thread']` | chatter, followers, `message_post` (`addons/mail/models/mail_thread.py:2182`), field `tracking=True` (`_message_track` `:644`, finalized in a precommit hook) |
| `mail.activity.mixin` | | scheduled activities |
| translations | `.po` files in `i18n/`, `translate=True` JSONB fields | `-u` reloads terms; `--i18n-overwrite` to force |

## 17. Testing (`tests/`)

- `TransactionCase` (`tests/common.py:990`): each test runs in a savepoint
  that is rolled back. `setUpClass` data is shared across the class.
- `SingleTransactionCase` (`:1171`): one transaction for the whole class.
- `HttpCase` (`:2196`): runs a real HTTP server and a headless Chrome
  (`ChromeBrowser` `:1247`). Use it for `start_tour(...)`, `url_open` and JS
  unit-test suites.
- Decorators: `@tagged('post_install', '-at_install', 'my_tag')` (`:2712`),
  `@users('login', …)` (`:2637`, runs the test as each user), `@warmup`
  (`:2668`, for query-count tests), `freeze_time` (`:2737`).
- Helpers: `new_test_user(env, login, groups=…)` (`:195`), `Form(record)`
  (`tests/form.py:27`, simulates the form view including onchanges and
  modifiers), `self.assertQueryCount(n)`, `RecordCapturer` (`:244`).
- Location: `<addon>/tests/test_*.py`, imported from `tests/__init__.py`.
  Run with `--test-enable --stop-after-init -u <module>` or
  `--test-tags /module:Class.method`. Tests are `at_install` by default;
  `post_install` runs after all modules are loaded.

---

# Part II: Server framework

## 18. Boot sequence

```
odoo-bin → odoo.cli.main()                       cli/command.py:87
  → Command "server" (default)                   cli/server.py  main(args)
      config.parse_config()                      tools/config.py
      check_root_user / check_postgres_user      refuses db_user=postgres, warns on root
      report_configuration()                     logs version, addons paths, db and replica
      db._create_empty_database(name)            auto-create if missing → config['init']['base']=True
      setup_pid_file()
      server.start(preload=db_names, stop=stop_after_init)   service/server.py:1575
```

`server.start()` then:
1. `load_server_wide_modules()` imports the modules in `--load` (defaults `base`, `web`) before any DB is opened, so their controllers are routable without a database. GC is disabled during the import.
2. Selects the server class:

| Condition | Server |
|---|---|
| `odoo.evented` (the `gevent` subcommand) | `GeventServer` |
| `--workers > 0` | `PreforkServer` |
| otherwise (`run_odoo.sh` as written) | `ThreadedServer` |

3. For `ThreadedServer` on 64-bit Linux, sets `MALLOC_ARENA_MAX=2` via `mallopt`, so per-thread glibc arenas don't inflate virtual memory and trip `limit_memory_soft`.
4. With `--dev=reload`, starts an inotify or watchdog file watcher.
5. `server.run(preload, stop)` calls `preload_registries(dbnames)` (`:1524`): for each DB, `Registry.new(db, update_module=..., install_modules=-i, upgrade_modules=-u)`, which triggers module loading. With `--test-enable` it also runs the post-install tests. Any exception is logged as `critical` and the return code is `-1`.
6. With `--stop-after-init` it stops here; otherwise it spawns cron and HTTP and waits.

**Phoenix reload.** `SIGHUP`, or a limit being reached, sets the global
`server_phoenix`. After stopping, `start()` calls `_reexec()`, which re-execs the
process with the same arguments (optionally injecting `-u` modules).

## 19. Server models

### 19.1 `ThreadedServer` (`:462`), used by this repo

- One process. HTTP is `ThreadedWSGIServerReloadable` (werkzeug's threaded server, one thread per request) on a daemon thread `odoo.service.httpd`.
- Cron runs as `max_cron_threads` (default 2) daemon threads running `cron_thread(n)`. The main thread loops on `process_limit()` and waits for signals.
- Signals: INT/TERM graceful stop (a second one forces `os._exit(0)`); HUP reload; XCPU exits immediately; QUIT dumps all thread stacks; USR1/USR2 log ormcache stats.
- **Limits are enforced by polling, not killing.** `process_limit()` compares process RSS with `limit_memory_soft` (2 GiB) and each HTTP or cron thread's `start_time` with `limit_time_real` (120 s; `limit_time_real_cron` for cron). Offending threads go into `limits_reached_threads`. The server waits until no other healthy request is running (or `SLEEP_INTERVAL`), dumps the offenders' stacks and sends itself `SIGHUP`. A runaway request therefore causes a full process restart; in-flight requests get about a second to finish.
- `set_limit_memory_hard()` sets `RLIMIT_AS` (2.5 GiB default) as the kernel-level cap.

**Cron thread design (`cron_thread`).**
- Opens a connection to the `postgres` DB and runs `LISTEN cron_trigger`.
- Loops on `select()` on the PG socket with timeout `SLEEP_INTERVAL + n`, then sleeps `n/100` s. Both are deliberate jitter to avoid a thundering herd when a `NOTIFY` wakes every worker.
- NOTIFY payloads are database names. Notified DBs are processed first. The full DB list is re-scanned at most once per `SLEEP_INTERVAL`.
- Disabled automatically if PG is in recovery mode.
- Recycles its connection after `limit_time_worker_cron` seconds if set.

### 19.2 `PreforkServer` (`:867`), a gunicorn-style master with N workers

```
 master (PreforkServer)                      owns the listening socket
  ├─ WorkerHTTP × workers                    each fork accept()s on the shared socket
  ├─ WorkerCron × max_cron_threads           one DB per loop iteration
  └─ gevent subprocess ("odoo gevent")       longpolling/websocket on gevent_port (8072)
```

**Master loop** (`run`), every `beat` = 4 s:
`process_signals → process_zombie → process_timeout → process_spawn → sleep`

- **Signals** are queued and a self-pipe wakes `select()` (Python would not otherwise interrupt a syscall). At most 5 are queued; extras are dropped except SIGCHLD. TTIN and TTOU add or remove a worker at runtime. HUP does a zero-downtime reload.
- **Zombie reaping** uses `waitpid(-1, WNOHANG)`. Exit status 3 raises a "critical worker error".
- **Watchdog.** Each worker writes `.` to its own pipe every loop pass. The master's `sleep()` selects on all worker pipes and updates `watchdog_time`. In `process_timeout`, a worker silent for `watchdog_timeout` (= `limit_time_real`; cron workers use the cron timeout) gets `SIGKILL`.
- **Spawn.** `process_spawn` refills the pools. Before forking it runs `registry.check_signaling()` once per loaded registry and then `sql_db.close_all()`, so children start with fresh, non-shared connections and an up-to-date registry.
- **Dispatching.** All HTTP workers `accept()` on the same socket; the kernel balances the load. Listen backlog is `8 × population`.

**Zero-downtime reload** (`fork_and_reload`, `stop`). On SIGHUP the master forks.
The parent clears `FD_CLOEXEC` on the listening socket, exports it in
`ODOO_HTTP_SOCKET_FD`, and `_reexec()`s into the new code. The child waits up to
60 s for the new master to send it `SIGHUP` (meaning the new server is ready),
and only then gracefully stops the old workers. The socket never closes. Systemd
socket activation (`LISTEN_FDS`, fd 3) is also supported.

**Worker lifecycle** (`Worker`, `:1215`).
- Each worker has a daemon "workthread" running `_runloop`: `check_limits → ping watchdog → sleep (select on socket/wakeup pipe) → process_work`.
- `check_limits` sets `alive=False` (clean exit after the current request) if the parent PID changed, `request_count ≥ limit_request` (65536), or RSS exceeds `limit_memory_soft`.
- It re-arms `RLIMIT_CPU` to `cpu_time_used + limit_time_cpu` each iteration, so the 60 s CPU limit applies per unit of work, not the worker's lifetime. The `SIGXCPU` handler raises an exception and does not kill the worker.
- **`WorkerHTTP.process_request`**: `accept()`, set a 2 s socket timeout (`ODOO_HTTP_SOCKET_TIMEOUT`, which protects against idle connections), `TCP_NODELAY`, then hand the socket to `BaseWSGIServerNoBind`. EPIPE is tolerated.
- **`WorkerCron`** runs `os.nice(10)`, closes the HTTP socket and keeps its own PG connection with `LISTEN`. `process_work` handles one database per call from a deque (notified DBs first), closing that DB's cursors when more than one DB is in rotation.

### 19.3 `GeventServer` (`:755`)

For long-lived connections (bus, websocket, longpolling).
- Port `gevent_port` (8072). `ProxyHandler` supports `Connection: Upgrade` / `Upgrade: websocket`.
- For upgrades it disables chunked I/O (gevent issue 1712) and injects the raw `socket` into `environ` for the websocket layer in the `bus` addon.
- A watchdog greenlet checks the parent PID and the memory limit (`limit_memory_soft_gevent`) every 4 s and sends itself `SIGTERM` on violation.
- Has its own DB pool size, `db_maxconn_gevent`.
- Behind nginx, `/websocket` goes to 8072 and the rest to 8069. This repo's `run_odoo.sh` runs threaded mode, so websocket traffic is served by the same threaded server.

## 20. WSGI entry and the `Application` object

`odoo.http.root = Application()` is the callable passed to every server.
`Application.__call__` (`http.py:2785`):
1. Resets per-thread diagnostics (`query_count`, `query_time`, `perf_t0`, `cursor_mode`, `dbname`, `uid`).
2. With `--proxy-mode` and an `X-Forwarded-Host` header, applies werkzeug `ProxyFix`.
3. Wraps the environ in `HTTPRequest`, builds a `Request`, pushes it on `_request_stack`, then:
   - path matches a static file (`/<module>/static/<file>`, resolved through the manifest) → `_serve_static`;
   - `request.db` set → `_serve_db` (on `RegistryError`: log out, drop the db, fall back to `_serve_nodb`);
   - otherwise `_serve_nodb`, which uses `nodb_routing_map`, built only from `server_wide_modules` controllers that are nodb-only.
4. Sessions use `FilesystemSessionStore` under `config.session_dir`, with `renew_missing=True`.

## 21. `_serve_db`: cursor and transaction strategy (`http.py:2240`)

```
registry = Registry(db);  cr = registry.cursor(readonly=True)     # read-only cursor (replica-capable)
registry.check_signaling(cr)                                      # reload registry/caches if another process changed them
env = Environment(cr, session.uid, session.context)
rule, args = env['ir.http']._match(path)                          # route match runs on the RO cursor

if route.readonly and cr.readonly:  serve on RO cursor within retrying()
      └ on ReadOnlySqlTransaction (a write was attempted) → warn, fall through to RW
else (RW route, or fallback):
      close RO cursor → new RW cursor (or rollback() to restart the transaction)
      env = env(cr=rw_cr);  retrying(serve_func, env)
```

- Thread `cursor_mode` is `ro`, `rw` or `ro->rw`, for diagnostics.
- If the first cursor is already RW, `cr.rollback()` starts a fresh transaction, avoiding repeatable-read serialization failures (the signaling check isn't redone inside `retrying`).
- `readonly` on `@route` may be a callable evaluated against the matched rule.

**`retrying` (`service/model.py:160`)** wraps every request and defines the
concurrency contract:
- Up to 5 tries (`MAX_TRIES_ON_CONCURRENCY_FAILURE`) on `OperationalError`, `ConcurrencyError` or serialization/deadlock errors.
- Between tries: roll back, `env.transaction.reset()`, `registry.reset_changes()`, reload the session.
- Uploaded files are rewound with `file.seek(0)`; a non-seekable upload raises `RuntimeError`, so streamed uploads can't be retried.
- Backoff is `uniform(0, 2**try)` seconds.
- On success it runs `env.cr.flush()` to push the ORM's write-behind to SQL before commit.
- `IntegrityError` becomes a `ValidationError` carrying the model's `_sql_error_to_message`.
- Consequence: controller code and `create/write` overrides can run up to 5 times. Side effects outside the DB (HTTP calls, immediate emails) must go in `cr.postcommit` hooks.

## 22. Routing and dispatch

**Route table.** `@http.route` (`:728`) attaches routing metadata to controller
methods, collected by `_generate_routing_rules`. The DB-aware map is
`ir.http.routing_map()`, cached with `@ormcache(..., cache='routing')`. Module
install or upgrade invalidates it through the signaling in §23.

**Dispatchers.** The `routing_type` of a route selects its dispatcher,
registered through `__init_subclass__` into `_dispatchers`:

| `type=` | Class | Body handling |
|---|---|---|
| `http` | `HttpDispatcher` | query and form params |
| `jsonrpc` | `JsonRPCDispatcher` | JSON-RPC 2.0 over HTTP; `params` must be an object, `method` is ignored, an optional `context` replaces the session context |
| `json2` | `Json2Dispatcher` | the new `/json/2` external API |

`is_compatible_with(request)` is checked on mimetype. Errors are formatted by
the dispatcher's own `handle_error`; JSON-RPC returns
`{"error": {code: 0|404|100, message, data: {debug...}}}`, where 100 means
session expired.

**Pipeline for a DB request** (overridable in `ir.http`, the intended extension point):

```
_match(path)                                  werkzeug rule + converters (model records resolved to browse())
Request._set_request_dispatcher(rule)
ir.http._authenticate(endpoint)
     └ session valid? security.check_session  → else logout(keep_db)
     └ getattr(cls, f"_auth_method_{auth}")   auth = user | public | none | bearer ...
ir.http._pre_dispatch(rule, args)
     ├ web.max_file_upload_size from ir.config_parameter (default 128 MiB; per-route max_content_length overrides)
     ├ dispatcher.pre_dispatch: CORS headers + OPTIONS preflight (204), save_session flag
     ├ fix context lang (get_lang)
     └ record-typed URL args: rebind to request env, check_access('read')
           AccessError/MissingError → NotFound for public users (no existence leak)
ir.http._dispatch(endpoint)                   captcha (non-safe methods) → endpoint(**request.params)
ir.http._post_dispatch(response)              save session, inject future_response, CSP
```

- `Dispatcher.post_dispatch` always sets `nosniff`. For `image/*` responses without their own policy it sets `Content-Security-Policy: default-src 'none'`.
- If no controller matches, `ir.http._serve_fallback` tries `ir.attachment._get_serve_attachment(path)`, which serves attachments with a public URL.
- RPC model calls go through `/web/dataset/call_kw/<model>/<method>`. The top-level RPC is inspectable via `request.params`, which `serichai_project_security` relies on for its `web_read` check.

## 23. Multi-process coherence (signaling)

Each worker has its own in-memory `Registry` and ormcache. Cross-process
consistency uses PostgreSQL sequences (`orm/registry.py:1064`):

| Event | Writer | Reader |
|---|---|---|
| Models, fields or views changed (install, upgrade, custom field) | `signal_changes()` inserts into `orm_signaling_registry` | `check_signaling()` compares `registry_sequence` to the DB; on mismatch does `Registry.new(db)`, a full reload |
| A named cache changed (`routing`, `default`, `assets`, `templates`, …) | inserts into `orm_signaling_<cache>` | on mismatch clears just those caches (without `clear_cache`, to avoid a signal loop) |

- `check_signaling` runs at the start of every request (`_serve_db`), before spawning workers, and per job in cron.
- A transaction that invalidates the registry marks `registry_invalidated`; signalling happens after commit. If the transaction fails, `reset_changes()` rebuilds the local registry (`_setup_models__`) or clears caches, so a rolled-back module change leaves no half-updated registry.
- Cost: one cheap sequence read per request, and staleness visible for at most one request.

Cron wakeups use `NOTIFY cron_trigger, '<db>'`; the `bus` addon uses its own table and `NOTIFY` for longpolling.

## 24. Database layer (`sql_db.py`)

- **Pool.** Two global `ConnectionPool`s: read-write, and read-only for replicas (`db_replica_host`/`db_replica_port`). Size is `db_maxconn` (64), or `db_maxconn_gevent` in gevent mode.
- `borrow()` first garbage-collects connections idle over 10 minutes (`MAX_IDLE_TIMEOUT`), closed, or flagged `leaked`. It then reuses a connection with a matching DSN and resets it. If the pool is full it evicts the oldest idle connection, and raises `PoolError('The Connection Pool Is Full')` if none is idle.
- Pools are process-local, hence `close_all()` before `fork`.
- **Cursor.** Wraps psycopg2 and counts queries and query time per thread (feeding the thread diagnostics). Provides `dictfetch*`, `split_for_in_conditions` (IN lists capped at 1000) and `now()`, a cached transaction timestamp reset on commit or rollback.
- **Commit ordering** (`commit()`, `:554`):
  1. `flush()`: loop up to 10 times over `transaction.flush()` (the ORM's pending writes) and `precommit` hooks. A precommit hook can itself trigger ORM changes, so it repeats.
  2. `_cnx.commit()`.
  3. `clear()`, drop the rollback hooks.
  4. `postcommit.run()`.
- **Rollback**: clear, drop `postcommit`, run `prerollback`, `ROLLBACK`, then `postrollback`.
- `cr.savepoint()` returns a `_FlushingSavepoint` by default, which flushes the ORM before taking the savepoint and handles the cache on rollback. Use `flush=False` only when there is nothing to flush.
- `registry.cursor()` attaches the `Transaction` (ORM cache holder) to the cursor. A bare `sql_db.db_connect(db).cursor()` has `transaction=None`, which is why cron opens its lock cursor that way.

## 25. Cron engine (`addons/base/models/ir_cron.py`)

```
_process_jobs(db)                     # called by cron thread / WorkerCron
  _check_version        base latest_version must equal BASE_VERSION, else skip DB (BadVersion)
  _get_all_ready_jobs   active AND (nextcall <= now OR id IN ir_cron_trigger.call_at <= now)
                        ORDER BY failure_count, priority, id      # healthy jobs first
  _check_modules_state  skip while any module is 'to install/upgrade/remove';
                        if the oldest ready job is older than MAX_FAIL_TIME, assume zombie
                        states and call reset_modules_state()
  loop job_ids:
     _acquire_one_job   SELECT … FOR NO KEY UPDATE SKIP LOCKED   # another worker holds it → skip
     registry.check_signaling()
     _process_job → commit        # commit releases the row lock
```

- **Concurrency control is a row lock**, not a flag. `SKIP LOCKED` makes N workers across N processes safe, and a crashed worker releases the lock automatically.
- `_process_job` builds an `Environment` as the cron's `user_id` and runs the server action through `_run_job`, which repeats up to 10 times while the progress API (`_commit_progress`) reports remaining work. Results:
  - `FULLY_DONE`: reschedule later by the interval.
  - `PARTIALLY_DONE`: reschedule ASAP, optionally `NOTIFY`.
  - `FAILED`: reschedule later and update `failure_count`.
- Three consecutive timeouts without completion (`CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3`) count as failed. A job is deactivated after `MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5` consecutive failures, subject to a time-span condition checked in `_update_failure_count`.
- `_trigger(at)` inserts `ir_cron_trigger` rows and sends `NOTIFY`, so code can wake a cron immediately.
- Jobs that process large sets should batch and commit progress. Otherwise `limit_time_real_cron` kills the worker and the timeout counter eventually deactivates the job.

## 26. Configuration cheat-sheet (defaults from `tools/config.py`)

| Option | Default | Mode | Effect |
|---|---|---|---|
| `--workers` | 0 | selects prefork | N HTTP workers (plus gevent subprocess) |
| `--max-cron-threads` | 2 | both | threads (threaded) or cron workers (prefork) |
| `--limit-memory-soft` | 2048 MiB | both | graceful recycle after the current request |
| `--limit-memory-hard` | 2560 MiB | both | `RLIMIT_AS`, hard failure |
| `--limit-time-cpu` | 60 s | prefork | per unit of work, via `RLIMIT_CPU` |
| `--limit-time-real` | 120 s | both | watchdog: thread restart (threaded) / SIGKILL (prefork) |
| `--limit-time-real-cron` | -1 | both | -1 means same as `limit-time-real` in prefork |
| `--limit-request` | 65536 | prefork | requests before the worker is recycled |
| `--db_maxconn` | 64 | both | connections per process |
| `--gevent-port` | 8072 | gevent | websocket/longpolling |
| `--load` | `base,web` | both | server-wide modules (loaded before any DB) |
| `--proxy-mode` | off (on in `run_odoo.sh`) | both | applies `ProxyFix` for X-Forwarded-* |

## 27. Implications for this repo

**Deployment and operations**

1. **Sizing.** The pool is per process. In prefork, total connections ≈ `(workers + cron + 1) × db_maxconn` at worst and must stay under PostgreSQL `max_connections`. A common starting point for worker count is `(CPU × 2) + 1`; budget memory as `workers × limit_memory_soft`.
2. **Threaded mode in production is a trade-off.** No per-request CPU limit; a leak or slow request can only be handled by whole-process restart. Prefork gives per-request SIGKILL, recycling and zero-downtime reload. Websockets need the gevent process (8072) behind the proxy, otherwise bus traffic ties up threads.
3. **Idempotency.** Requests can be retried up to 5 times and cron jobs after timeouts. Code that sends mail, calls APIs or writes files should use `cr.postcommit.add(...)` or the mail queue.
4. **Read-only routes.** Mark pure read endpoints `readonly=True` (and RPC methods `@api.readonly`). They avoid a RW cursor and can use a replica. A write attempt is not fatal (it retries on RW) but costs one wasted request.
5. **Schema or module changes with multiple workers.** Other workers reload the registry on their next request after signaling. Cron workers skip the database while modules are in `to install/upgrade` state, so cron pauses during a `-u` run (logged as `Skipping database … modules to install/upgrade/remove`).
6. After any change to fields, views, data files or security, run `-u <module>`. Python-only changes need a restart or `--dev=all`.
7. `serichai_inventory` is not in `run_odoo.sh`'s addons path and can't be installed until it is added.
8. **Reports need host fonts.** The Contract MO PDF prints Thai labels through `wkhtmltopdf`, which takes fonts from the host. Any new server needs a Thai font installed (e.g. `fonts-thai-tlwg`), or the labels print as boxes.

**`serichai_project_mo`**

9. The many2many `project_task_mrp_production_rel` is declared on both models with the column pair swapped (`project_task_id`/`mrp_production_id`). Both definitions must name the same table and columns, or the ORM creates a second table and the two sides stop agreeing. `mrp_production_count` has a correct `@api.depends('mrp_production_ids')` and is not stored, so it costs one query per batch of tasks.
10. `_get_report_task_properties` reads `task_properties` through `read()`. The access filtering in `serichai_project_security` (item 12) therefore also applies to the PDF, so a restricted user can't print a hidden property.

**`serichai_project_security`**

11. **Rule design.** `rule_task_stage_restricted` is a **global** rule (`groups` cleared), whose `domain_force` evaluates to `[(1, '=', 1)]` for everyone except the restricted role. Global rules are ANDed for all users, so a typo in that expression affects every user. It is also the only way to *narrow* access for one group, because group rules can only widen (they are ORed). `rule_task_write_pinned_project` is a group rule limited to `perm_write`.
12. **The rule matches stages by name.** The stage names are hard-coded in Thai. `project.task.type.name` is `translate=True`, and a domain on a translated field compares against the **current user's language** (§9). Renaming a stage, or a restricted user whose language has a different translation of it, silently hides those tasks. Matching on stage XML IDs or a boolean flag on the stage would be sturdier.
13. **`is_expanded_access_task` is a non-stored compute with a `search=` method** and no `@api.depends`, so the rule domain is turned into `project_id = <pinned id>` by `_search_is_expanded_access_task`. It follows the Odoo 19 convention (`in`/`not in` operators, `NotImplemented`, `Domain` objects). The pinned id comes from `ir.config_parameter.get_param`, which is ormcached in the `stable` cache. Changing it in Settings writes the parameter, which clears `stable` (`ir_config_parameter.py:107`). `_CACHES_BY_KEY` (`orm/registry.py:66`) cascades `stable` to `default`, where the per-user rule domains (`ir_rule.py:138`) are cached, so the new project takes effect on the next request in every worker (§23).
14. **`web_read` guard.** `web_read` calls `read()` internally (`addons/web/models/models.py:117`), and `web_search_read` / `web_read_group` call `web_read` (§7). The override therefore checks the **top-level** RPC (`request.params`) and only blocks direct form loads. This is a UI guard: the role still has `read` access to the listed tasks through `search_read`, exports and so on, which is by design (see spec 007).
15. **Property hiding is applied in `read()`.** It covers forms, lists and the report, since all go through `read`. It does not cover `search` or `_read_group` on property values. A restricted user who filters or groups by a hidden property in the UI could still infer its values. Worth checking if those properties are sensitive.
16. **RPC surface.** `action_open_expanded_access_tasks` is a public `@api.model` method, so any logged-in user can call it over RPC. That's harmless here (it only returns an action dict and the pinned project's display name, read with `sudo`). New helper methods that should not be callable from the client should be prefixed with `_` or marked `@api.private` (§5).

**Writing new backend code here**

17. Override `create` with `@api.model_create_multi` and a `vals_list`; call `super()` in every CRUD override; put invariants in computes or `@api.constrains`, not in `onchange`.
18. Use `models.Constraint` / `models.Index` instead of `_sql_constraints`, `aggregator=` instead of `group_operator=`, `_read_group` instead of `read_group`, `check_access` instead of `check_access_rights`/`check_access_rule`, and `self.env._()` for translatable messages.
19. Keep `sudo()` narrow and never return sudo'd data to the client unfiltered (§10).
20. There are no Python tests in the custom addons yet. `TransactionCase` with `new_test_user(groups='serichai_project_security.group_project_task_list_only')` and `@users` would cover the rules, the `web_read` guard and the property filtering cheaply (§17).
