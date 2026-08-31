# Phase 0 Research: Inventory Barcode Scanning (serichai_inventory_barcode)

All Technical Context items were resolvable by reading the existing `serichai_inventory_barcode` addon and the spec — no items are left as `NEEDS CLARIFICATION`. This document records the key technical findings, including a bug that currently prevents the feature from working at all in the browser, and the decisions made to close it and the one requirement gap (FR-007) the current code doesn't yet enforce.

## Decision 1: Fix the asset registration path (blocking bug)

**Decision**: Change `__manifest__.py`'s `assets['web.assets_backend']` entry from `'serichai_inventory/static/src/js/barcode_scan_widget.js'` to `'serichai_inventory_barcode/static/src/js/barcode_scan_widget.js'`.

**Rationale**: Odoo resolves asset bundle paths as `<addon_technical_name>/<path within that addon>`. The manifest currently points at `serichai_inventory` — a different, unrelated skeleton addon (per `CLAUDE.md`: "minimal skeleton — models package is empty, one view file") that (a) has no `static/src/js/barcode_scan_widget.js` file at all, confirmed by search, and (b) isn't even on this deployment's addons path (`run_odoo.sh`'s `ADDITIONAL_ADDONS` is `muk_web_theme,serichai-odoo` — `serichai_inventory` is excluded, matching `CLAUDE.md`'s note that it "would need to be added manually if it's meant to be installed"). The actual widget file lives at `serichai_inventory_barcode/static/src/js/barcode_scan_widget.js`. With the current (wrong) path, Odoo's asset bundler cannot resolve the JS file, so `StockPickingBarcodeScanner` never registers and the `barcode_scanned` bus listener never attaches — meaning User Stories 1–4 do not function today despite the server-side `action_scan_barcode` method and the view's `<widget>` tag both being correct and already in place.

**Alternatives considered**:
- *Leave as-is and file a separate bug report instead of fixing it here*: rejected — the spec's acceptance scenarios (US1–US4) are unverifiable end-to-end without this fix, and the fix is a one-line path correction with no design risk.
- *Move the JS file into `serichai_inventory` instead of fixing the manifest*: rejected — would spread one addon's frontend code across two addons' directories for no benefit, and `serichai_inventory` isn't even on the addons path.

## Decision 2: Add a closed-transfer guard to `action_scan_barcode` (FR-007)

**Decision**: At the top of `action_scan_barcode` in `models/stock_picking.py`, raise a `UserError` if `self.state in ('done', 'cancel')`, before any product lookup or line creation/increment logic runs.

**Rationale**: The view's informational banner already hides itself when `state in ('cancel', 'done')` (`invisible="state in ('cancel', 'done')"` in `stock_picking_views.xml`), but the `<widget name="stock_picking_barcode_scanner"/>` tag is a sibling of that banner and is **not** covered by the same `invisible` condition — it stays mounted and listening for scans regardless of picking state. The underlying `action_scan_barcode` method has no state check either. That combination means a scan on an already-done or cancelled transfer would currently attempt to create/confirm a new `stock.move` or mutate a `stock.move.line` on a closed transfer, which the spec's edge cases and FR-007 explicitly rule out. A server-side guard is required regardless of any view-level fix, since view `invisible` never blocks direct RPC calls to the method (standard Odoo security practice: never rely on view-only enforcement) — so the fix is added in the model, not the view.

**Alternatives considered**:
- *Only fix the view (wrap the widget tag itself in the same `invisible` condition)*: rejected as insufficient on its own — it improves the UI but leaves `action_scan_barcode` callable directly with no protection; the plan applies the view tweak in addition to (not instead of) the model-level guard, as defense in depth, but the model-level guard is the one that satisfies FR-007.
- *Silently no-op instead of raising*: rejected — inconsistent with the existing error-notification pattern already used for unrecognized barcodes (FR-005) and tracked products (FR-006); a silent no-op would look like a missed scan rather than a deliberate block.

## Decision 3: Keep existing add-or-increment matching logic unchanged

**Decision**: No change to the core matching logic already in `action_scan_barcode`: look up the product by exact barcode match, then find an open (`state not in ('done', 'cancel')`) move on the picking for that product; increment its move line if one exists, otherwise create a new move (+ line).

**Rationale**: This already directly implements FR-001–FR-004 as written and matches US1/US2's acceptance scenarios exactly (new line at qty 1 on first scan; same line incremented on repeat scans; no duplicate lines). Nothing here needs to change.

**Alternatives considered**: None — this logic was verified correct by inspection against the spec, no alternative approaches were evaluated since there's no problem to solve here.

## Decision 4: Keep existing unrecognized-barcode and lot/serial guards unchanged

**Decision**: No change to the existing `UserError` raised when `product.product.search([('barcode', '=', barcode)])` finds nothing (FR-005), or when the matched product has `tracking != 'none'` (FR-006). Both are already caught client-side in `barcode_scan_widget.js`'s `onBarcodeScanned` and surfaced via `this.notification.add(..., {type: "danger"})`.

**Rationale**: Directly satisfies FR-005, FR-006, and FR-008 (confirmation feedback on success — the widget's success-path notification already includes `result.product_name`). No gap found.

**Alternatives considered**: None needed.

## Decision 5: Testing approach

**Decision**: Add `tests/test_barcode_scan.py` using `odoo.tests.common.TransactionCase`, run via `--test-enable --stop-after-init -u serichai_inventory_barcode`, covering: new-line-on-first-scan, increment-on-repeat-scan, unrecognized-barcode error, lot/serial-tracked-product error, and closed-transfer error (once Decision 2 lands). No test infrastructure currently exists in this addon (unlike `serichai_project_security`, which already has `tests/test_access_restriction.py`).

**Rationale**: The addon has zero automated coverage today; the spec's five FR-agnostic behaviors (add, increment, unknown barcode, tracked product, closed transfer) are exactly the natural test boundaries, and mirroring the existing `serichai_project_security` test style keeps conventions consistent across this repo's addons per `CLAUDE.md`.

**Alternatives considered**: JS/QUnit tests for the widget itself — rejected as out of scope; the widget is a thin bus-event-to-RPC-call wrapper with no branching logic of its own, so server-side coverage of `action_scan_barcode` covers all the behavior that matters.
