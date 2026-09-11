# Quickstart: Validate the Contract MO Report

Prerequisites: `serichai-db` reachable, `.venv` present at repo root, `serichai_project_mo` already installed (it already is, in any environment that has the existing smart button/MO tab).

## 1. Upgrade the module

From `odoo/` with `.venv` activated:

```bash
source ../.venv/bin/activate
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory \
    -d serichai-db -u serichai_project_mo --stop-after-init
```

Expect no traceback and a log line loading `report/project_task_report_views.xml` and `report/project_task_report_templates.xml`.

## 2. Start the server and open a task

```bash
./run_odoo.sh
```

Open any `project.task` form (Project app).

## 3. User Story 1 — content is present and correct

1. Link 2–3 Manufacturing Orders of different sizes to the task (existing "Manufacturing Orders" tab / smart button).
2. Open the task's **Print** dropdown → click **Contract MO**.
3. Confirm the PDF shows: the task name in a bordered box at the top, the task's properties as label/value pairs beneath it (only those still defined on the project, unset ones showing a blank value), a boxed "Manufacturing Order" heading, one table row per linked MO under the Manufacturing Order / Product / Quantity columns, and any task description text in the remarks (หมายเหตุ) section.
4. Cross-check against `contract_mo_sample.jpg` for section placement/labeling — see [contracts/report-contract.md](./contracts/report-contract.md) for the exact field mapping.

## 4. User Story 2 — standard Print-menu discovery

1. Open a *different* task that has never had this report printed before.
2. Confirm "Contract MO" appears in the Print dropdown automatically, with no per-task setup.
3. Confirm the PDF's header/footer/logo matches the company's configured report layout (Settings → General Settings → Companies → Document Layout) — same chrome as printing, e.g., a Sales Order.

## 5. User Story 3 — incomplete data renders cleanly

1. Create a bare task: no linked Manufacturing Orders, no project, no description.
2. Print **Contract MO** — confirm it renders without error, with no properties block, a full blank ruled item table and blank remarks/second-signature fields.
3. Link more Manufacturing Orders to a task than the template's blank-row constant (~15–20; see [data-model.md](./data-model.md)) and reprint — confirm every linked MO still appears as a row (table grows, nothing dropped).

## 6. Automated check (optional, matches repo testing convention)

```bash
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory \
    -d serichai-db --test-enable --stop-after-init -u serichai_project_mo
```

A test asserting `env['ir.actions.report']._render_qweb_pdf('serichai_project_mo.report_contract_mo', [task.id])` (or `_render_qweb_html`) does not raise, across the four data-completeness cases in step 5 and the report-contract.md rendering table, satisfies spec SC-004.
