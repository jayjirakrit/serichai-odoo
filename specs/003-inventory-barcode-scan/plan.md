# Implementation Plan: Inventory Barcode Scanning (serichai_inventory_barcode)

**Branch**: `003-inventory-barcode-scan` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-inventory-barcode-scan/spec.md`

## Summary

Warehouse operators need to add and increment `stock.picking` operation lines by scanning a product barcode instead of manual entry, with clear errors for unrecognized barcodes and a hard block on auto-adding lines for lot/serial-tracked products. The addon already implements the server-side logic (`action_scan_barcode` on `stock.picking`) and a client-side widget wired to Odoo's `barcode` service, but research below found the module's asset registration points at the wrong addon path, so the widget's JS currently never loads — none of the four user stories function in the browser today even though the server method itself is correct. The plan is a targeted fix (manifest asset path) plus one closed gap (no state guard against scanning on done/cancelled transfers, required by FR-007) plus adding the test coverage this addon currently lacks — no new addon, no new models, no UI redesign.

## Technical Context

**Language/Version**: Python 3.12 (repo `.venv`), Odoo 19.0 ORM; JavaScript (OWL framework) for the backend widget

**Primary Dependencies**: Odoo `stock` addon (`stock.picking`/`stock.move`/`stock.move.line`), Odoo `barcodes` addon (provides the `barcode` client service and its `barcode_scanned` bus event); no new third-party dependencies

**Storage**: PostgreSQL via Odoo ORM; no new persisted models — this feature only creates/updates existing `stock.move`/`stock.move.line` records

**Testing**: Odoo `odoo.tests.common.TransactionCase`, run via `--test-enable --stop-after-init -u serichai_inventory_barcode`, following the pattern already established in `serichai_project_security/tests/test_access_restriction.py` (no test suite exists yet in this addon — to be added)

**Target Platform**: Server-side Odoo addon (Linux) plus backend web client (`stock.picking` form view)

**Project Type**: Odoo addon (single addon extension, no separate frontend/backend split)

**Performance Goals**: No dedicated targets; a scan triggers one product search plus one small ORM write, comparable in cost to manually adding a line — no batch/bulk-scan performance requirement in scope

**Constraints**: Must not modify vendored Odoo core under `odoo/`; must not modify the unrelated `serichai_inventory` addon; enforcement confined to `serichai_inventory_barcode`

**Scale/Scope**: Single Odoo instance (`serichai-db`), scoped to `stock.picking` transfers only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (`[PROJECT_NAME] Constitution` with bracketed placeholders) — no project-specific principles or gates have been ratified. This gate is **N/A / pass by default**. General repository conventions from `CLAUDE.md` (avoid modifying vendored `odoo/`, follow existing addon layout, avoid unrequested scope) are reflected in the Constraints above and the design below.

**Post-Phase-1 re-check**: No change — `research.md` and `data-model.md`/`contracts/` introduce no new dependencies, no core-file modifications, and no scope beyond the existing addon. Gate remains N/A / pass.

## Project Structure

### Documentation (this feature)

```text
specs/003-inventory-barcode-scan/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
serichai-odoo/serichai_inventory_barcode/     # existing addon (own nested git repo), fixed/extended in place
├── __manifest__.py                           # fix: assets path currently points at 'serichai_inventory/...' (wrong addon); must be 'serichai_inventory_barcode/...'
├── models/
│   ├── __init__.py                           # unchanged
│   └── stock_picking.py                      # extend: action_scan_barcode() gains a closed-transfer guard (FR-007); add/increment and error-message logic already present
├── views/
│   └── stock_picking_views.xml               # unchanged (widget + info banner already correctly placed on the picking form)
├── static/
│   └── src/js/
│       └── barcode_scan_widget.js            # unchanged (already correct; just unreachable until the manifest fix lands)
└── tests/                                    # NEW: no test suite exists in this addon today
    └── test_barcode_scan.py                  # NEW: TransactionCase tests, mirrors serichai_project_security's test style
```

**Structure Decision**: Everything stays inside the existing `serichai-odoo/serichai_inventory_barcode/` addon, following its current file layout (`models/`, `views/`, `static/src/js/`). No new addon and no new top-level directories — this is a fix-and-close-the-gap pass over an addon that is already ~95% built, not a fresh implementation.

## Complexity Tracking

*No constitution violations — table not applicable.*
