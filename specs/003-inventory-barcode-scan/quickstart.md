# Quickstart: Validating Inventory Barcode Scanning

Prerequisites: repo `.venv` activated, `serichai-db` reachable, `serichai_inventory_barcode` addon upgraded with this feature's fixes (manifest asset path, closed-transfer guard).

## 1. Install / upgrade the module

```bash
source .venv/bin/activate
cd odoo
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-db -u serichai_inventory_barcode --stop-after-init
```

Expect no errors; confirms the manifest fix (Decision 1) and model change (Decision 2) load cleanly, and that the `web.assets_backend` bundle resolves `barcode_scan_widget.js` without a missing-file error.

## 2. Run the automated test suite

```bash
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-db --test-enable --stop-after-init -u serichai_inventory_barcode
```

Expect the new `tests/test_barcode_scan.py` to pass — see `contracts/module-interface.md`'s
Verification contract for exactly what the tests assert (add, increment, unknown barcode,
tracked product, closed transfer).

## 3. Manual end-to-end check

1. Start the server normally: `./run_odoo.sh`
2. Log in as a user with warehouse/inventory access.
3. Open (or create) a draft transfer (Inventory → any operation type → New), and add an untracked test product's barcode to `product.barcode` if not already set (Inventory → Products).
4. On the transfer form, confirm the blue info banner ("Scan a product barcode anywhere on this page...") is visible and the transfer is not yet done/cancelled.
5. Using a connected barcode scanner (or Odoo's on-screen/keyboard-emulated barcode input, if configured for testing), scan the untracked product's barcode.
   - Expect: a new operation line appears with quantity 1, and a success notification shows the product's name (US1, FR-001/002/008).
6. Scan the same barcode again.
   - Expect: the same line's quantity increases to 2; no second line is created (US2, FR-003).
7. Scan a barcode that doesn't match any product.
   - Expect: a red/danger notification stating no product was found; the transfer's lines are unchanged (US3, FR-005).
8. Scan the barcode of a product configured with lot or serial tracking.
   - Expect: a danger notification explaining scan-to-add isn't supported for tracked products; no line is added or incremented (US4, FR-006).
9. Validate/confirm the transfer to `done` (or cancel it), then attempt another scan of the untracked product's barcode.
   - Expect: a danger notification (or no effect) and no change to any line (FR-007, new).
10. Confirm manual line entry (the standard operations table "Add a line") still works normally at every step above (FR-010).

## Expected outcome

Matches spec Success Criteria SC-001–SC-005: a single scan adds or increments a line with no manual search/typing, every unrecognized-barcode scan produces a visible error, every lot/serial-tracked-product scan is blocked from auto-adding a line, and manual entry remains available throughout.
