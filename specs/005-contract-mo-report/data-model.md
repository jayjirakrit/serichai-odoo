# Phase 1 Data Model: Contract MO Print Report for Project Task

This feature adds **no new persisted models or fields**. It defines one report artifact (an `ir.actions.report` + QWeb template pair) that composes fields already present on `project.task` and its already-linked `mrp.production` records. This document describes that composition — the "shape" the report reads — rather than a schema change.

## Report artifact: Contract MO (`serichai_project_mo.report_contract_mo`)

Not a database entity — a print-time view over one `project.task` record and its `mrp_production_ids`.

| Report section | Source | Notes |
|---|---|---|
| Company header/footer/logo | `web.internal_layout` (core) | Whatever the printing company's report layout is configured to in Settings; identical mechanism to every other Odoo PDF report (spec FR-003) |
| Document title | Static template text ("Contract MO", labeled to match paper form's "ใบสั่งผลิตตัวอย่าง") | — |
| Job name (boxed) | `o.name` (`project.task.name`) | Existing required field; bordered box at the top of the page (spec FR-011) |
| Contract header fields (เลขที่สัญญา, จำนวน, ระยะส่ง, วันที่ลงนาม, วันหมดสัญญา, …) | `o._get_report_task_properties()` over `o.task_properties` | Label/value pairs, one per property that still exists in the project's `task_properties_definition`; block omitted when the task has none (spec FR-012) |
| "Manufacturing Order" section heading (boxed) | Static template text | Bordered box above the item table (spec FR-004) |
| Item table row (× `len(o.mrp_production_ids)`) | one `mrp.production` per row: `mo.name`, `mo.product_id.display_name`, `mo.product_qty` + `mo.product_uom_id.name` | spec FR-005, FR-013 |
| Item table blank padding rows | template constant `N` (~15–20) minus real row count, floored at 0 | spec FR-006/FR-007 — see research.md Decision 5 |
| Remarks / หมายเหตุ | `o.description` (Html field, rendered as-is) | spec FR-004; blank when task has no description (spec User Story 3) |
| Signature block 1 label | Static text "หัวหน้าแผนกเย็บ" | Always blank line — no equivalent role/field exists on `project.task` |
| Signature block 2 label + name | Static text "ผู้สั่งผลิต" + `', '.join(o.user_ids.mapped('name'))` if `o.user_ids` else blank line | spec Assumptions |

## Property rendering helper (`project.task._get_report_task_properties`)

The only Python this feature adds. It is a read-only presentation helper on `project.task` — no new field, no new model.

| Step | Behavior |
|---|---|
| Source | `self.read(['task_properties'])[0]['task_properties']` — the ORM merges the values stored on the task with the definition held by `project_id.task_properties_definition`, so **only properties that still exist in that definition come back**; orphaned stored values are dropped by the ORM itself (`Properties._dict_to_list`) |
| Visibility | Because the helper goes through `read()`, `serichai_project_security`'s `project.task.read()` override still applies — properties the printing user may not see are filtered out before they reach the template |
| Skipped entries | `separator` properties (UI-only, no value) and any entry without a label |
| Output | `[{'string': <label>, 'value': <printable text>}, …]` |
| Value formatting (`_format_report_property_value`) | unset → `''` (label still prints); `boolean` → `✓`; `many2one` → display name; `many2many` → comma-joined display names; `selection` → option label; `tags` → comma-joined tag labels; `date`/`datetime` → `format_date`/`format_datetime` (user language/timezone); `float`/`monetary` → `formatLang`; `html` → `html2plaintext`; otherwise `str(value)` (so integer `0` prints as `0`, not blank) |

## Relationships used (all pre-existing, unchanged by this feature)

- `project.task.mrp_production_ids` ↔ `mrp.production.project_task_ids` — many2many via `project_task_mrp_production_rel` (`project_task_id`, `mrp_production_id`), defined identically on both sides in `models/project_task.py` and `models/mrp_production.py`. This feature only *reads* the relation; it does not modify either side.

## Validation / rendering rules derived from spec Functional Requirements

- FR-008: the template guards every optional section (`task_properties`, `mrp_production_ids`, `description`, `user_ids`) with `t-if`/conditional joins so an empty value renders as an empty section, never a QWeb error.
- FR-012: property existence is enforced by the ORM read itself, not by the template — a stored value with no matching definition never reaches the template, so no orphan label or raw property name can print.
- FR-007: item-table row generation is a plain `t-foreach` over the full `mrp_production_ids` recordset — it is never truncated to `N`, so it always represents 100% of linked MOs regardless of how many there are.
