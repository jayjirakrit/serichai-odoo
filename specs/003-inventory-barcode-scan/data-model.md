# Phase 1 Data Model: Inventory Barcode Scanning (serichai_inventory_barcode)

This feature introduces **no new persisted models**. It only reads and writes existing `stock`-module entities. This document describes how those existing entities are used, not new schema.

## Existing entities referenced (unchanged definitions)

- **`stock.picking`** (core `stock` addon): the transfer being scanned against. Extended in this addon (already, pre-existing) with `action_scan_barcode(barcode)`. No new fields added.
- **`stock.move`**: created by `action_scan_barcode` when no open move exists yet for the scanned product on the picking (`product_uom_qty=0` initially, confirmed via `_action_confirm()` if the picking is past `draft`).
- **`stock.move.line`**: created (quantity `1`, `picked=True`) on first scan of a product, or incremented (`quantity += 1`) on subsequent scans of the same product while an open line exists.
- **`product.product`**: looked up by exact `barcode` field match. `tracking` (`'none' | 'lot' | 'serial'`) determines whether scan-to-add is permitted (FR-006).

## Read/write shape (for reference, not a stored entity)

Input to the flow: a scanned barcode string, delivered by the `barcode` service's `barcode_scanned` bus event and passed to `action_scan_barcode(barcode)` via ORM `call`.

Output of `action_scan_barcode`, returned to the widget for the success notification:

```python
{'product_name': product.display_name}
```

Error paths raise `UserError` (translated message shown as a notification client-side) rather than returning a value:

- No product matches the barcode → FR-005.
- Product is lot/serial tracked → FR-006.
- Picking is `done`/`cancel` → FR-007 (new, per Decision 2 in `research.md`).

## State transitions

No new state machine. The feature only affects **which existing `stock.move`/`stock.move.line` records exist and their `quantity`**, within the picking's own existing lifecycle (`draft → waiting/confirmed → assigned → done`, or `→ cancel`). FR-007 (new guard) restricts scan-driven writes to pickings **not** in `done` or `cancel`, matching the addon's existing "editable transfer" boundary already implied by the view's banner visibility condition.

## Validation rules (all already enforced by existing code, per `research.md`)

- Barcode MUST resolve to exactly one `product.product` via its `barcode` field, or the scan is rejected (FR-005).
- Product `tracking` MUST be `'none'` for scan-to-add/increment to proceed (FR-006).
- Picking `state` MUST NOT be `'done'` or `'cancel'` for scan-to-add/increment to proceed (FR-007, new).
