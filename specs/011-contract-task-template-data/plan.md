# Plan: Contract Task Template Data

Addon: `serichai_project_config` (adds `product` to `depends`, needed by the product SKU property).

- `data/project_contract_template.xml`: `noupdate` block with stage `project_stage_upcoming_bid`, project `project_serichai_contract` (`task_properties_definition` as an `eval` list, hex names kept from the source record) and template task `task_template_contract` (`is_template=True`, default values for the two selections).
- `hooks.py`: `_adopt_existing_records`, called from `pre_init_hook`. For each shipped xml id with no `ir.model.data` row, it searches by name and registers the match with `noupdate=True`.
- `tests/test_template_adoption.py`: adoption and idempotence.

Design notes: the definition lives on the project, not the task, and is not copied by "Create from template". Hence the project is shipped together with the template. Odoo re-writes `noupdate` records on first install, so the definition is replaced by the shipped one (see spec "Known limits").

## Verification

1. Fresh DB install: no errors, 3 records created.
2. Simulated live DB (hand-made records, then install): one project, stage and template, template id kept, "HAND-MADE" value kept.
3. `--test-enable --test-tags /serichai_project_config`: 0 failures.
