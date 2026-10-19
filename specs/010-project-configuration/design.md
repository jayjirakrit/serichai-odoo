# Design: High-Value-First Task Sorting

Review aid for the human architect. Not production code; full tests excluded.
Spec: [spec.md](./spec.md) | Plan: [plan.md](./plan.md) | Findings: [research.md](./research.md)


## Approach

1. `serichai_project_config` depends only on `project`. `serichai_project_access` (009) is
   not modified, and there is no contract between them.
2. One **stored** flag, `is_high_value`, computed as superuser from the property labelled
   "มูลค่าโครงการ" and the threshold. Every user gets the same sort.
3. One **non-stored** display field, `project_value`, computed with the current user's rights from
   what `read(['task_properties'])` returns to that user. When a module hides the property in
   `read()` (009 does), or the user cannot read the task, the result is 0 and no error is raised.
4. Two view extensions set `default_order="priority desc, is_high_value desc, state, date_deadline asc, id desc"`
   on the internal list base and kanban, and add the column and a "High Value" filter for everyone.
   The model `_order` is untouched.
5. The flag is recomputed instantly when the task's properties or project change. A threshold or
   definition change takes effect on Recalculate, and the Settings block says so. Install fills the
   flag in batches.

## Decisions

| # | Decision | Why |
|---|---|---|
| 1 | Flag stored and sudo; amount non-stored, read through the user's own `read()` | same order for all; the amount only shows what the user may read, with no 009 code (research V5) |
| 2 | No dependency, hook or contract with 009 | user decision, Gate 2 round 5; FR-001 |
| 3 | Match the label with `.strip()`; first match wins; parse by property `type` | FR-002, edge cases; `Property.get` returns ids/labels/`False` (V3) |
| 4 | `priority desc` first; no `nulls last` | the star supersedes the sort; the client parser drops `nulls`; PostgreSQL ASC is already NULLS LAST (V4) |
| 5 | Inherit `project_task_view_tree_base` and `view_task_kanban`, never `_main_base` | the portal list inherits `_main_base` (V5) |
| 6 | Flag depends on `task_properties` and `project_id` only; no recompute in `set_values` | instant only for a task's own value; Recalculate otherwise (V6) |
| 7 | Threshold has its own `get_values`/`set_values`, not `config_parameter=` | `config_parameter` stores 0 as unset; FR-014 allows 0 (V7) |
| 8 | `pre_init_hook` creates the column; `post_init_hook` fills it in batches | FR-017; otherwise the ORM computes every row at once (V7) |
| 9 | Column and filter shown to everyone; `is_high_value` readable by all | hidden users see 0 in the column, and the flag reveals only the position (accepted) |

## Flow

```text
Task property edit / project move (task_properties is recomputed from project_id)
    --> _compute_is_high_value (sudo, field access) --> is_high_value (stored; unchanged values not written)
Definition or threshold change --> nothing until Settings > Recalculate --> _recompute_high_value
Open a task list or board --> ORDER BY priority DESC, is_high_value DESC, state ASC, date_deadline ASC, id DESC
List row / export --> _compute_project_value (current user) --> self.read(['task_properties'])
    --> 009 (if installed) strips hidden properties there --> label not found --> 0
Install --> pre_init_hook (column) --> post_init_hook --> _recompute_high_value
```

## Requirement groups -> key files

| Requirements | Key files |
|---|---|
| FR-001 | `__manifest__.py` |
| FR-002..FR-007 value and flag | `models/project_task.py` |
| FR-008..FR-013 sort, column, filter | `views/project_task_views.xml` |
| FR-014..FR-016 admin | `models/res_config_settings.py`, `views/res_config_settings_views.xml` |
| FR-017 install | `hooks.py` |
| FR-018..FR-020 | `models/project_task.py` (`_compute_project_value`); 009 unchanged |

## Key snippets

### `models/project_task.py` - parsing, shared by both computes

```python
PROJECT_VALUE_LABEL = 'มูลค่าโครงการ'
THRESHOLD_PARAM = 'serichai_project_config.high_budget_threshold'
DEFAULT_THRESHOLD = 50_000_000.0
_AMOUNT_RE = re.compile(r'[-+]?\d+(\.\d+)?')


def parse_amount(prop_type, raw):
    """Amount held by one property value; 0.0 for non-amount types or unreadable text."""
    if prop_type in ('integer', 'float', 'monetary') and not isinstance(raw, bool):
        value = float(raw or 0)
    elif prop_type in ('char', 'text') and isinstance(raw, str):
        text = re.sub(r'[\s,]', '', raw)
        value = float(text) if _AMOUNT_RE.fullmatch(text) else 0.0
    else:
        return 0.0                        # empty, relational, selection, tags, date...
    return value if math.isfinite(value) else 0.0


def is_value_property(prop):
    return (prop.get('string') or '').strip() == PROJECT_VALUE_LABEL
```

`parse_amount` takes the property's `type` and raw value. Both computes feed it: the flag from
field access, the display amount from `read()` dicts, which carry `string`/`type`/`value` (research V3).

### `models/project_task.py` - the two fields

```python
class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_high_value = fields.Boolean(
        string='High Value', compute='_compute_is_high_value', store=True,
        help="Project value above the high-value threshold (Settings > Project).")
    project_value = fields.Float(string='Project Value', compute='_compute_project_value')

    @api.depends('task_properties', 'project_id')
    def _compute_is_high_value(self):                  # stored: runs as superuser
        threshold = self._get_high_value_threshold()
        for task in self:
            value = 0.0
            try:
                prop = next(filter(is_value_property,
                                   task.project_id.task_properties_definition or []), None)
                if prop:
                    value = parse_amount(prop.get('type'), task.task_properties.get(prop['name']))
            except (ValueError, TypeError, KeyError, AttributeError):
                _logger.debug("Unreadable project value on task %s, using 0", task.id, exc_info=True)
            task.is_high_value = value > threshold

    @api.depends_context('uid')
    @api.depends('task_properties', 'project_id')
    def _compute_project_value(self):                  # non-stored: current user's rights
        self.project_value = 0.0
        saved = self.filtered(lambda t: isinstance(t.id, int))
        try:
            rows = saved.read(['task_properties']) if saved else []
        except AccessError:     # a task this user may not read: show 0, never fail the list
            return
        for row in rows:
            try:
                prop = next(filter(is_value_property, row['task_properties'] or []), None)
                if prop:
                    self.browse(row['id']).project_value = parse_amount(
                        prop.get('type'), prop.get('value'))
            except (ValueError, TypeError, KeyError, AttributeError):
                _logger.debug("Unreadable project value on task %s", row.get('id'), exc_info=True)
```

Why `read()` and not field access (research V5):
- 009 hides properties only in the dicts `read()` returns (`project.task.read`, `project.project.read`).
  Field access goes through `fetch()` SQL and would return the real amount.
- Reading through `read()` honours any module that filters properties there, without naming it.
- `AccessError` is added to the caught exceptions because `read()` checks the user's access. A task
  the user cannot read must give 0 rather than break a list or export (FR-007).
- New (unsaved) records give 0; the column is not shown on forms.
- One `read()` call per compute batch, so a list of 80 rows costs one call.

### `models/project_task.py` - threshold and recalculation

```python
    @api.model
    def _get_high_value_threshold(self):
        # sudo: ir.config_parameter is admin-only; only a number leaves this method.
        raw = self.env['ir.config_parameter'].sudo().get_param(THRESHOLD_PARAM)
        try:
            value = float(raw) if raw else DEFAULT_THRESHOLD   # unset; "0.0" is a real value
        except (TypeError, ValueError):
            return DEFAULT_THRESHOLD
        return value if math.isfinite(value) and value >= 0 else DEFAULT_THRESHOLD

    @api.model
    def _recompute_high_value(self, batch_size=1000):
        """Re-evaluate every task, archived included, in portions (FR-015, FR-017)."""
        # sudo: an admin-triggered maintenance pass over all tasks, whatever record rules say.
        tasks = self.sudo().with_context(active_test=False)
        ids = tasks.search([], order='id').ids
        for start in range(0, len(ids), batch_size):
            batch = tasks.browse(ids[start:start + batch_size])
            self.env.add_to_compute(self._fields['is_high_value'], batch)
            batch.flush_recordset(['is_high_value'])
            batch.invalidate_recordset()
```

- Any `task_properties` edit recomputes the flag, because Odoo cannot depend on a single property
  key. That is cheap, and `Field.write` drops unchanged values, so no guard is needed.
- `project_id` is redundant, since `task_properties` is computed from it, but it is kept so the move
  rule (FR-006) is explicit (V6).
- Limitation: after a definition change, `project_value` (live) can differ from the flag until
  Recalculate.

### `views/project_task_views.xml`

```xml
<record id="project_task_view_tree_base" model="ir.ui.view">
    <field name="name">project.task.view.list.base.inherit.high.value</field>
    <field name="model">project.task</field>
    <field name="inherit_id" ref="project.project_task_view_tree_base"/>
    <field name="arch" type="xml">
        <list position="attributes">
            <attribute name="default_order">priority desc, is_high_value desc, state, date_deadline asc, id desc</attribute>
        </list>
        <field name="date_deadline" position="after">
            <field name="project_value" optional="show"/>
        </field>
    </field>
</record>

<record id="view_task_search_form" model="ir.ui.view">
    <field name="name">project.task.search.form.inherit.high.value</field>
    <field name="model">project.task</field>
    <field name="inherit_id" ref="project.view_task_search_form"/>
    <field name="arch" type="xml">
        <filter name="open_tasks" position="before">
            <filter string="High Value" name="high_value" domain="[('is_high_value', '=', True)]"/>
            <separator/>
        </filter>
    </field>
</record>
```

Differs from the list record: `view_task_kanban` (inherits `project.view_task_kanban`) only sets
the same `default_order` through `<kanban position="attributes">`.

These extensions reach All Tasks, My Tasks, project tasks, milestone and template views. They also
reach 009's `serichai_access_task_list` / `_kanban`, which are primary children of the core views
and need no dependency. The portal, To-do and mobile subtask views, and the model `_order`, are
untouched (V5).

### `models/res_config_settings.py`

```python
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # No config_parameter=: it would store 0 as "unset" (research V7).
    serichai_high_value_threshold = fields.Float(
        string='High-Value Threshold',
        help="Tasks whose project value is above this amount are listed first. 0 makes every "
             "positive value high-value. After changing it, click 'Recalculate high-value flag'.")

    @api.model
    def get_values(self):
        res = super().get_values()
        res['serichai_high_value_threshold'] = self.env['project.task']._get_high_value_threshold()
        return res

    def set_values(self):
        super().set_values()
        # sudo: settings are admin-only (ACL); repr keeps 0 as "0.0", not unset.
        self.env['ir.config_parameter'].sudo().set_param(
            THRESHOLD_PARAM, repr(self.serichai_high_value_threshold))

    def action_serichai_recompute_high_value(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):          # FR-016, besides the ACL
            raise AccessError(self.env._("Only administrators can recalculate the flag."))
        self.env['project.task']._recompute_high_value()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'type': 'success', 'message': self.env._("High-value flag recalculated.")}}
```

Settings view, record `res_config_settings_view_form`:
- It inherits `project.res_config_settings_view_form` and adds
  `<block title="Task Sorting" groups="base.group_system">` after `//block[@id='tasks_management']`.
- The block holds one `<setting>` with the field and a `btn-link` button
  `action_serichai_recompute_high_value`.
- Under the button, a muted hint reads: "Run after changing the threshold or a project's
  'มูลค่าโครงการ' property; edited tasks update on their own."
- A negative threshold is stored, and the reader then falls back to 50M (FR-014).

### `hooks.py`

```python
from odoo.tools.sql import column_exists, create_column


def pre_init_hook(env):
    """Create the column first so the ORM does not compute every task in one go (FR-017)."""
    if not column_exists(env.cr, 'project_task', 'is_high_value'):
        create_column(env.cr, 'project_task', 'is_high_value', 'bool')


def post_init_hook(env):
    env['project.task']._recompute_high_value()
```

Manifest: `depends: ['project']`, the two view files, both hooks, version `1.0.0`, `AGPL-3`.

## Specs must assert

All in `tests/test_budget_sort.py`. No 009 is needed; spec 009 tests are unchanged.
- **Values.** 60M is high-value; 40M and exactly 50M are not. `parse_amount('char', "60,000,000")`
  returns 60000000.0. `"abc"`, `"nan"` and `""` give 0.0, and a task with `"abc"` saves without
  error. Many2one and selection properties give 0.
- **Missing property or project.** Not high-value. The same label in two projects (one with extra
  spaces) is read in both.
- **Project move.** Moving to a project without the property drops the flag at once.
- **Definition change.** Deleting or renaming the definition leaves the flag unchanged; after
  `_recompute_high_value()` it is 0. Editing a task's value updates its flag at once.
- **Order**, from the `default_order` of `view_task_tree2` and `view_task_kanban` via `get_view`:
  - starred tasks first (priority `'3'` > `'2'` > `'1'` > `'0'`), then high-value, then state (open before done/cancelled), then deadline
    with empty deadlines last;
  - with no property anywhere: `priority desc, state, date_deadline asc, id desc`;
  - the portal sharing list and `_order` are unchanged.
- **Threshold.** Unset, `'abc'` or `'-5'` gives 50M, and saving 0 reads back 0. Saving 30M leaves a
  40M flag unchanged until the Recalculate action. A non-admin gets AccessError on the action.
- **Install.** `post_init_hook` works with no property anywhere.
- **Amount visibility.** `project_value` equals the amount for a project user. When `read` strips
  the property (patched `project.task.read`) or raises `AccessError` (patched), it is 0 with no
  exception. `is_high_value` and the list order are the same for both users.

## Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | A future access module that hides properties somewhere other than `read()` (e.g. only in views) would not zero the amount | Documented assumption (V5); 009 filters in `read()` today |
| R2 | Admins forget Recalculate after a threshold or definition change | Settings hint; quickstart |
| R3 | Hidden users see a column full of 0 and the High Value filter | Accepted (Gate 2 round 5); the flag reveals only the position |
| R4 | One `read()` per list load for the column | Fine; one call per batch of rows |

## Open questions

None.
