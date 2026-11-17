# Quickstart: Product Catalog

No JavaScript exists in this addon: there is no hoot suite and no tour. The automated gate is Python only; the visual
behaviour is checked by hand (nothing visual was verified headlessly).

## Automated gate (throwaway DB recommended)

```bash
cd /home/odoo/serichai-odoo/odoo
../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-test-012 \
  -i serichai_product_catalog --test-enable --stop-after-init --test-tags /serichai_product_catalog
# existing DB: use -u serichai_product_catalog instead of -i
```
Expect 24 tests, 0 failed, no warnings (view validation, `th.po`). `muk_web_colors` is not needed.

Opt-in timing (5,000 products; category change and name/reference/barcode search, server side, must be < 1 s):

```bash
CATALOG_PERF=1 ../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-test-012 -u serichai_product_catalog --test-enable --stop-after-init \
  --test-tags /serichai_product_catalog:TestProductCatalog.test_perf_5000_products
```

## Manual browser checklist (MuK theme, `tools/run/run_odoo.sh`; compare with both mocks)

1. As a plain internal user the **Catalog** menu appears; the default facets are Goods and Can be Sold.
2. Grid: 4 cards per row at >= 992 px, 3 at 768-991, 2 at 576-767, 1 below 576. Cards: rounded, primary-tinted border,
   white body, fixed-height picture, name, reference, price, Sale/Purchase pills. No picture shows the placeholder.
3. Pastels cycle per card position (lavender, mint, light blue, pink, cream). Hover lifts the card with a soft shadow.
4. Search: one box matches name, reference, variant reference, barcode (case-insensitive, partial). Try Category,
   Tags, Services/Combo/Favorites, Can be Purchased, group by Product Type and Category; no Archived filter exists.
   Remove the default facets and check the archived products never appear.
5. Switch to list (thumbnail, name, reference, category, price, hover tint, no Export). Pager reads "1-N / N".
6. Open a card: two-column page (max 1400 px). Sidebar: photo box 300 px, name, "reference . category", large price,
   badges. Tabs: Specification first, Sales, Purchase (purchasing users only). Breadcrumb "Catalog" and browser Back
   restore search, filters and view.
7. Specification: managers edit rich text (table, callout, link) with Save/Discard; plain users see a readonly copy or
   "No specification yet". Technical Data table: one separator per row, label and value vertically centered
   (barcode, unit of measure, weight, volume); attributes are not displayed.
8. Photo: as a product manager upload, replace and delete from the sidebar; as a plain user there is no upload control.
9. Sales tiles: Sales Price, Price incl. Tax, Margin (Margin only for purchasing users), customer tax pills. Purchase
   tab (purchasing users): Cost, Cost incl. Tax, Unit of Measure, vendor tax pills, vendor list with Lead Time (days).
10. As a plain user, network tab on the catalog and a product page: no `standard_price`, `catalog_margin`,
    `catalog_cost_incl_tax` or `seller_ids`.
11. Settings > General > Colors, change Primary, reload: borders, price, active tab, tiles, callouts follow. Toggle dark
    mode: pastels, cards and tables stay legible.
12. Widths 360, 768, 1280 px: no horizontal scrollbar; below 900 px the sidebar stacks above the tabs (not sticky).
13. Switch language to Thai: menu, filters, tabs, tiles are translated.
