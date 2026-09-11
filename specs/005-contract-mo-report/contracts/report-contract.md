# Contract: `action_report_contract_mo` (Print-menu report on `project.task`)

This addon change has no HTTP/API surface. Its contract is the shape of the `ir.actions.report` record, the QWeb template's rendering behavior for each spec requirement, and where it is discoverable in the UI. Downstream work (tasks.md, tests, manual verification) should validate against the tables below.

## `ir.actions.report` record contract

| Field | Value | Contract |
|---|---|---|
| `name` | `Contract MO` | Label shown in the Print dropdown |
| `model` | `project.task` | — |
| `report_type` | `qweb-pdf` | Standard PDF report, like core's Production Order report |
| `report_name` | `serichai_project_mo.report_contract_mo` | Must exactly equal the `<template id="report_contract_mo">` xmlid, module-qualified |
| `report_file` | `serichai_project_mo.report_contract_mo` | Same value as `report_name`, per core convention (e.g. `mrp`'s `report_mrporder` action) |
| `print_report_name` | `'Contract MO - %s' % object.name` | Filename when downloaded |
| `binding_model_id` | `ref="model_project_task"` (research.md Decision 2) | Makes the report auto-appear in `project.task`'s Print dropdown (spec FR-002) |
| `binding_type` | `report` | Required for Print-menu auto-discovery, not just the Reporting menu |

## Rendering contract (`report_contract_mo` QWeb template)

| Input condition | Required output | Spec ref |
|---|---|---|
| Any `project.task` record | Renders without raising, wrapped in `web.html_container` → `web.internal_layout` (company header/footer/logo present) | FR-003 |
| `o.mrp_production_ids` has 1..N records (N ≤ template's blank-row constant) | Item table shows exactly `len(o.mrp_production_ids)` real rows under the Manufacturing Order / Product / Quantity columns (MO reference, product display name incl. variant, qty + UoM) followed by blank ruled rows padding out to the constant | FR-005, FR-006, FR-013 |
| `o.mrp_production_ids` has more records than the blank-row constant | Item table shows **all** linked MOs as real rows; zero padding rows; no row omitted | FR-007 |
| `o.mrp_production_ids` is empty | Item table shows zero real rows, full blank ruled grid; no error | FR-008 |
| `o.project_id` is unset (or its project defines no properties) | The properties block is omitted entirely; the boxed task name still prints | FR-008, FR-012 |
| A property exists in the project's `task_properties_definition` | It prints as `<label>: <value>`, value formatted per type; an unset value prints the label with a blank value | FR-012 |
| A value is stored on the task for a property that is no longer defined (or is hidden from the reader by `serichai_project_security`) | The property is skipped — neither its label, its internal name, nor its value appears | FR-012 |
| `o.description` is empty/falsy | Remarks section renders with an empty value, section label still present | FR-008 |
| `o.user_ids` is empty | "ผู้สั่งผลิต" signature line renders as a blank line (same as the "หัวหน้าแผนกเย็บ" line) | Assumptions |
| Any of the above | Each linked MO's reference appears in its row's Manufacturing Order column (the separate announcement-number header field of the 2026-09-10 design is removed) | FR-009 superseded by FR-013 |

## Discoverability contract (web client)

| Aspect | Contract |
|---|---|
| Where it appears | Print dropdown on the `project.task` form view (`project.view_task_form2` and any view inheriting it) — no changes to `views/project_task_views.xml` required |
| Access control | Follows `project.task`'s own existing read/print access — no new `ir.model.access.csv` or security XML introduced (FR-010) |
| Manifest | `report/project_task_report_views.xml` and `report/project_task_report_templates.xml` added to `__manifest__.py`'s `data` list, after the existing `views/*.xml` entries |
| Property helper | `project.task._get_report_task_properties()` / `._format_report_property_value()` in `models/project_task.py` — presentation-only helpers called from the template; no new field, no stored data, no security change |
