# Data Model: serichai_project_configuration

The module `serichai_project_configuration` depends on `project` only and adds no model.
`serichai_project_access` (spec 009) is not modified.

## project.task (inherited)

| Field | Type | Notes |
|---|---|---|
| `is_high_value` | Boolean, computed, **stored**, readonly | String "High Value". True when project value > threshold (FR-005). Depends on `task_properties` and `project_id`; the ORM skips unchanged values. Computed as superuser from field access, so it is the same for everyone. Column `bool`, created by `pre_init_hook` |
| `project_value` | Float, computed, **not stored**, `depends_context('uid')` | String "Project Value". Computed with the current user's rights from `read(['task_properties'])`. 0.0 when that result lacks the property (a module hid it), when the user cannot read the task (`AccessError`), or for unsaved records. Cannot be searched, grouped or sorted |

Amount rules (`parse_amount(type, raw)` and `is_value_property(prop)`, shared by both computes):

1. **Property**: the first property whose `string.strip()` is `มูลค่าโครงการ`. The flag looks in the
   project's definitions; the column looks in the user's `read()` result.
2. **Value**: counted only for these types. Anything else, or any error, gives 0.0.
   - `integer`/`float`/`monetary`: a finite number, not a `bool`.
   - `char`/`text`: whitespace and `,` are removed, then the text must match `[-+]?\d+(\.\d+)?`.
3. **Sign and currency**: negative values are kept as entered; there is no currency conversion.

Threshold and definition changes take effect on Recalculate. Until then, `project_value` (live) can
differ from the flag. The view order is `priority desc, is_high_value desc, state, date_deadline asc, id desc`.
The model `_order` is unchanged.

## Configuration

| Key | Where | Value |
|---|---|---|
| `serichai_project_configuration.high_budget_threshold` | `ir.config_parameter` | A float as text, e.g. `"50000000.0"` or `"0.0"`. Unset, empty, non-numeric, negative or non-finite gives 50,000,000. `"0.0"` means 0 |
| `res.config.settings.serichai_high_value_threshold` | Float without `config_parameter`; own `get_values`/`set_values` | Settings > Project > "Task Sorting", `base.group_system` only. Always written as `repr(value)`, so 0 is kept. Saving does not recompute; a hint points to Recalculate |

## Lifecycle

| Event | Effect |
|---|---|
| Install | `pre_init_hook` creates the column, so the ORM computes nothing. `post_init_hook` then recalculates every task (archived included) in batches of 1000 |
| Task create, property value edit or project change | That task's flag is recomputed |
| Property definition saved on a project | Nothing until "Recalculate high-value flag", or until the task is edited |
| Threshold saved (Settings or System Parameters) | Nothing until "Recalculate high-value flag", or until the task is edited |
| Uninstall | Odoo removes the column and views; the core order returns. The parameter row stays (not module data, harmless) |
