# Contract: `serichai_inventory_barcode` Module Interface

This module has no HTTP/API surface of its own beyond the standard Odoo ORM/RPC method it adds.
Its "contract" is the method signature and behavior of `stock.picking.action_scan_barcode`, the
client asset that must be reachable for that method to be called from the UI, and the view
changes it makes to the `stock.picking` form. Downstream work (tasks.md, tests, manual
verification) should validate against this table rather than against implementation prose.

## Method contract: `stock.picking.action_scan_barcode(self, barcode)`

| Aspect | Contract |
|---|---|
| Caller | `self.ensure_one()` — must be called on a single `stock.picking` record |
| Input | `barcode`: `str`, the raw scanned barcode value |
| Success return | `{'product_name': <str>}` — the display name of the matched product, used for the UI success notification (FR-008) |
| Error: no match | Raises `UserError` if no `product.product` has `barcode == barcode` (FR-005) |
| Error: tracked product | Raises `UserError` if the matched product's `tracking != 'none'` (FR-006) |
| Error: closed transfer | Raises `UserError` if `self.state in ('done', 'cancel')` (FR-007 — **new**, added by this feature; not present before) |
| Side effect: new product | Creates a `stock.move` (confirmed if picking state is past `draft`) and a `stock.move.line` with `quantity=1`, `picked=True` (FR-001, FR-002) |
| Side effect: repeat scan | Increments the existing open move line's `quantity` by 1; does not create a duplicate line (FR-003) |
| Location handling | New moves/lines always use the picking's own `location_id`/`location_dest_id` — never prompts for a location (FR-004) |

## Asset contract: `web.assets_backend` bundle entry

| Aspect | Contract (after fix) |
|---|---|
| Manifest key | `assets['web.assets_backend']` |
| Path | `serichai_inventory_barcode/static/src/js/barcode_scan_widget.js` (corrected from the current, broken `serichai_inventory/...` path — see `research.md` Decision 1) |
| Registers | `view_widgets` registry entry `"stock_picking_barcode_scanner"`, backing the `<widget name="stock_picking_barcode_scanner"/>` tag used in `views/stock_picking_views.xml` |
| Behavior | Listens on the `barcode` service's `barcode_scanned` bus event while mounted on a `stock.picking` form record; on each event, calls `action_scan_barcode` via ORM `call` and reloads the record; shows a success or danger notification based on the result |

## View contract: `stock.picking` form

| Aspect | Contract |
|---|---|
| Inherited view | `stock.view_picking_form` |
| Insertion point | Before the `move_ids` field inside the `operations` page |
| Adds | An informational banner (hidden when `state in ('cancel', 'done')`) and the `stock_picking_barcode_scanner` widget |
| Manual entry | Untouched — the standard move/move-line editor remains fully available regardless of scan usage (FR-010) |

## Explicitly out of scope for this feature (do not implement without a new spec/plan change)

- Any change to `product.product`/barcode uniqueness handling — ambiguous/duplicate barcodes remain out of scope per the spec's Assumptions.
- Any bulk/multi-unit scanning (e.g., a barcode representing a case of N units) — out of scope per the spec's Assumptions.
- Any change to the unrelated `serichai_inventory` addon — this feature only fixes the asset *path string* in `serichai_inventory_barcode`'s own manifest, it does not touch `serichai_inventory` itself.
- Any device/scanner pairing or configuration UI — out of scope per the spec's Assumptions.

## Verification contract (how to check compliance)

For a test picking in a non-`done`/`cancel` state, with an untracked test product `P1` (barcode `B1`) and a lot-tracked test product `P2` (barcode `B2`):

1. `picking.action_scan_barcode('B1')` on a picking with no existing line for `P1` MUST create exactly one `stock.move.line` for `P1` with `quantity == 1` and `picked is True`, and MUST return `{'product_name': P1.display_name}`.
2. A second `picking.action_scan_barcode('B1')` call MUST leave the line count for `P1` unchanged and increase that line's `quantity` to `2`.
3. `picking.action_scan_barcode('does-not-exist')` MUST raise `UserError` and MUST NOT change any move or move line on the picking.
4. `picking.action_scan_barcode('B2')` MUST raise `UserError` and MUST NOT create or increment any line for `P2`.
5. Setting the picking to `state = 'done'` (or `'cancel'`) and then calling `picking.action_scan_barcode('B1')` MUST raise `UserError` and MUST NOT change any move or move line (new behavior from Decision 2 — will fail until that fix lands).
6. With the manifest fix from Decision 1 applied, loading the `stock.picking` form in a browser MUST successfully load `barcode_scan_widget.js` as part of the `web.assets_backend` bundle (no 404/bundle-resolution error), and a simulated `barcode_scanned` bus event MUST trigger a call to `action_scan_barcode`.
