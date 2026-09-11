# Phase 0 Research: Contract MO Print Report for Project Task

No `[NEEDS CLARIFICATION]` markers remain in the Technical Context — the pattern this feature follows is already established twice in the vendored `odoo/` tree (core `mrp`'s own Production Order report, and `hr_timesheet`'s task-bound Timesheets report), so the open questions below were resolved by inspecting that vendored code directly rather than by guessing.

## Decision 1: Report registration mechanism

**Decision**: A plain `ir.actions.report` record with `binding_model_id` set to `project.task`'s model and `binding_type` set to `report`. No custom Print button, no JS, no view XML changes.

**Rationale**: This is exactly how every "appears in the Print dropdown" report in Odoo core works — confirmed by reading `odoo/addons/mrp/report/mrp_report_views_main.xml` (`action_report_production_order`, bound to `mrp.production`) and `odoo/addons/hr_timesheet/report/report_timesheet_templates.xml` (`timesheet_report_task`, bound to `project.task` from a *different* module than where `project.task` is defined — the same situation `serichai_project_mo` is in). Odoo's `ActionMenus` web-client component calls `ir.actions.report.get_bindings(model_name)` on every form load and lists one Print-menu entry per matching binding — no other registration step exists.

**Alternatives considered**: A manual `<button type="action" ...>` in `views/project_task_views.xml` invoking the report — rejected because spec FR-002 explicitly requires the standard Print-menu mechanism ("use Odoo layout and practice"), and it would duplicate what the binding already provides for free.

## Decision 2: Cross-module `binding_model_id` reference syntax

**Decision**: `<field name="binding_model_id" ref="model_project_task"/>` (unprefixed).

**Rationale**: `hr_timesheet/report/report_timesheet_templates.xml`'s `timesheet_report_task` record — a report on `project.task` defined in a module that does not own `project.task` — uses this exact unprefixed form in this installed Odoo 19 tree, and it is a shipped, working core report. `serichai_project_mo` is in the identical position (depends on `project`, doesn't own `project.task`), so the same syntax applies. (The fully-qualified form `project.model_project_task` is also valid or more literally standard elsewhere in the tree, e.g. `project/views/project_task_views.xml`'s own internal bindings use `project.model_project_task`; following the same-situation precedent (`hr_timesheet`) over the same-module precedent (`project` referencing itself) is the more directly applicable one here.)

**Alternatives considered**: None — this is a syntax choice with one demonstrably-working precedent for this exact cross-module situation.

## Decision 3: Template base and layout primitives

**Decision**: `web.html_container` (outer PDF wrapper) → `t-foreach="docs" t-as="o"` (one page per printed task) → `web.internal_layout` (standard company header/footer chrome) → a `<div class="page">` body built from `<table class="table ...">` sections (header fields, item grid, remarks, signatures), using Bootstrap's `table-borderless` for label/value rows where no grid lines are wanted and `table-bordered` for the ruled item grid.

**Rationale**: This is the exact skeleton `mrp/report/mrp_production_templates.xml`'s `report_mrporder` uses (`web.html_container` → `web.internal_layout` → `div.page`), which is what makes the printed page automatically pick up the company's configured report layout/logo (spec FR-003, User Story 2) with zero extra code — `internal_layout` is where that chrome lives. Table-based layout (rather than Bootstrap `row`/`col` flex divs) is preferred for the header-field and signature sections specifically because wkhtmltopdf — Odoo's PDF rendering engine — has materially better, more predictable support for HTML tables than for flexbox/grid, and core's own header-heavy reports (invoice, sale order) already lean on `table-borderless` for this reason.

**Alternatives considered**: Bootstrap `row`/`col` divs throughout (matches `mrp_production_templates.xml`'s own product/qty section) — usable but less predictable for the label-heavy two-column header block and the two-column signature block this form needs; tables are more literal translation of a form that is itself visually a grid.

## Decision 4: Sourcing the item table [SUPERSEDED 2026-09-11, see Decision 7]

**Decision (2026-09-10, superseded)**: ~~Item table: `t-foreach="o.mrp_production_ids" t-as="mo"`, one row per linked MO, columns = row index, `mo.product_id.display_name` (carries the variant/size, e.g. "Fabric X [Size: M]"), `mo.product_qty` + `mo.product_uom_id.name`. Announcement-number field: `', '.join(o.mrp_production_ids.mapped('name'))` (per the resolved spec clarification), rendered blank when `mrp_production_ids` is empty.~~ Replaced by Decision 7 below: the mockup `project_mo_report-sample.png` drops the separate announcement-number header field and adds a "Manufacturing Order" column to the item table instead, so each row already carries its MO's reference.

**Rationale**: `mrp_production_ids` is the module's existing, only link between a task and its Manufacturing Orders (`models/project_task.py`); `product_id`, `product_qty`, `product_uom_id` are confirmed standard fields on `mrp.production` (`odoo/addons/mrp/models/mrp_production.py`). This requires no new field on either model.

**Alternatives considered**: A backing `report.serichai_project_mo.report_contract_mo` `AbstractModel` with a `_get_report_values()` method to pre-aggregate rows — rejected as unneeded complexity; core's own Production Order report has no backing model either (confirmed in `mrp_production_templates.xml`) because, like this report, its content is simple field/relation access with no cross-record aggregation.

## Decision 5: Blank-row padding for the fixed-size grid

**Decision**: After the real `t-foreach` over `o.mrp_production_ids`, a second `t-foreach="range(max(0, N - len(o.mrp_production_ids)))"` emits empty `<tr>` rows with `&#160;` cell content, where `N` (~15–20, spec Assumptions) is a template constant, not a stored setting.

**Rationale**: Matches the paper form's fixed ruled grid (most rows blank, ready to hand-write) per spec FR-006/User Story 3. `max(0, ...)` guarantees no negative `range()` when a task already has more linked MOs than `N` (spec FR-007/Edge Cases) — real rows are never dropped; padding simply stops.

**Alternatives considered**: A CSS min-height on the table — rejected; wkhtmltopdf does not reliably grow bordered table rows to fill a CSS min-height the way real `<tr>` rows do, and the paper form's grid is literally row-based, not a single tall cell.

## Decision 6: Rendering the `description` field as remarks

**Decision**: `<span t-field="o.description"/>` with no `t-options`. `project.task.description` is an `Html` field (confirmed in `odoo/addons/project/models/project_task.py`); a plain `t-field` on an `Html` field renders its sanitized HTML content directly, which is the correct/only way to render rich text in QWeb — no `widget: 'text'` conversion is applicable (that widget is for `Text`/`Char` fields, not `Html`).

**Rationale**: Avoids a subtly wrong widget option that would either no-op or error; reusing the existing `description` field (rather than adding a new plain-text "remarks" field) keeps this feature additive-only per spec Assumptions ("this feature only adds the printable report").

**Alternatives considered**: A new plain-text `remarks` field on `project.task` — rejected as unnecessary scope growth; `description` already serves this purpose in the task form today and nothing in the spec asks for a second, parallel notes field.

## Decision 7: Header revision to match `project_mo_report-sample.png` (2026-09-11)

**Decision**: Replace the 2026-09-10 header (job/date/project/announcement-number table) with: (a) `o.name` in a bordered box, (b) `o.task_properties` rendered as label/value pairs via a new presentation-only model method `project.task._get_report_task_properties()`, and (c) a boxed "Manufacturing Order" heading above the item table, whose columns become Manufacturing Order (`mo.name`) / Product (`mo.product_id.display_name`) / Quantity (`mo.product_qty` + UoM) — folding the old announcement-number field into the table itself instead of a separate join.

**Rationale**: `project.task.task_properties` (Odoo core `fields.Properties`, `odoo/orm/fields_properties.py`) is a JSON-backed pseudo-field whose *definition* (label, type, still-exists-or-not) lives on the linked `project.project.task_properties_definition`, not on the task row itself. Reading it through `self.read(['task_properties'])` — rather than `o.task_properties` directly in the template — routes through the ORM's own `Properties.convert_to_read_multi` / `_dict_to_list`, which already does exactly the "does this property still exist" check the user asked for: a stored value with no matching definition entry is silently dropped before it ever reaches the caller (confirmed in `_dict_to_list`, `odoo/orm/fields_properties.py:620`). Going through `read()` (a Python method) rather than direct QWeb field access also means `serichai_project_security`'s own `project.task.read()` override — which filters `task_properties` by a separate visibility-rule model — still applies to what prints, with no template-side duplication of that logic.

**Alternatives considered**:
- Iterating `project_id.task_properties_definition` directly and looking up each name in `o.task_properties` — rejected: reimplements the existence/visibility filtering the ORM's `read()` already does for free, and risks drifting from `serichai_project_security`'s access rule if that model's logic ever changes.
- Using the `Property` mapping object (`o.task_properties['some_key']`) — rejected for iteration: `Property.__iter__` filters to existing keys but exposes no `string`/type metadata per item as cleanly as the `read()` list-of-dicts form (`{'name', 'string', 'type', 'value', ...}`), which the report needs for the label.
- A `t-field="o.task_properties"` widget-rendered block — rejected: no built-in QWeb report widget renders the Properties field as label/value text; the web client's own rendering is a form-view JS widget, not something `t-field` reproduces in a PDF report.

**Value formatting**: `_format_report_property_value()` special-cases each `ALLOWED_TYPES` entry (`odoo/orm/fields_properties.py:32`) using the same helpers core reports already use for the same job — `odoo.tools.format_date`/`format_datetime` (language/timezone-aware), `formatLang` (float/monetary), `html2plaintext` (html), and manual joins for `many2one`/`many2many`/`tags`/`selection` (whose `read()` values already carry a display name or label). An unset property renders its label with a blank value, matching the paper form's blank fields; `separator` properties (UI grouping only, no value) are skipped.
