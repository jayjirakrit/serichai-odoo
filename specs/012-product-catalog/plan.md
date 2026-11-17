# Implementation Plan: Product Catalog

**Branch**: `012-product-catalog` | **Date**: 2026-11-17 (updated 2026-11-18, built state) | **Spec**: [spec.md](./spec.md)

**Input**: `specs/012-product-catalog/spec.md`; lean plan `PLAN_product_catalog.md`; cosmetics from `product_catalog_mock.html` and the newer `product_catalog_mock (1).html`. Findings in [research.md](./research.md); code review aid in [design.md](./design.md).

## Summary

[Updated: built state] New addon `serichai_product_catalog` (version 19.0.1.2.0) presents `product.template` as a
catalog using only native Odoo 19 views (search, kanban, list, form) behind one `ir.actions.act_window` and one
top-level menu. **There is no JavaScript and no OWL**: an OWL layer (js_class views, toolbar, hero/tiles widgets, hoot
tests, tour) was built and then removed at the user's request. The standard control panel gives search facets, view
switcher and pager; the full-screen product page is the form view, so breadcrumb and browser Back restore search,
filter and view natively. The Specification is the existing `product.template.description` (Html), edited with the
standard `html` widget; the product photo (`image_1920`) is editable by the same managers.

What carries the look (all XML + one SCSS file, `web.assets_backend`):
- Kanban: explicit CSS grid (4/3/2/1 columns), rounded bordered cards, hover lift + shadow, picture area with a pastel
  that cycles by card position, name, reference, price, Sale/Purchase pills.
- Form (follows the newer mock): sticky sidebar (photo, name, reference . category, price, badges) beside tabs
  Specification, Sales, Purchase; tiles, tax pills, technical data table, vendor price list.
- Three non-stored computed fields feed the tiles; the two cost-derived ones are restricted to
  `purchase.group_purchase_user` (R13).
- SCSS uses only Odoo 19 Bootstrap CSS variables, **without** the `bs-` prefix (`--primary`, `--border-color`, ...), plus
  `color-mix()`; no hex/rgb/hsl literals, so a MuK color change recolors the catalog (R1, R21, R22).
- One tiny Python method, `action_open_standard_form`, because a pure-XML "open this record in the standard form"
  button is impossible (R7).
- Server-side enforcement: editable Specification and photo fields are in the view only for
  `product.group_product_manager` (others get a readonly copy); the ACL on `product.template` write refuses any other
  write. The Purchase page and cost-derived nodes are stripped from the arch for users outside
  `purchase.group_purchase_user`.

## Technical Context

**Language/Version**: Odoo 19.0, Python 3.12 (one action method, three computed fields), XML views, SCSS. No JS/OWL.

**Primary Dependencies**: `product`, `account` (`taxes_id`, tax computation), `purchase` (group, `supplier_taxes_id`). MuK `muk_web_colors` is a runtime theme, not a dependency.

**Storage**: PostgreSQL, existing `product_template`; no schema change (computed fields are not stored).

**Testing**: `TransactionCase` (`@tagged('post_install', '-at_install')`) in `tests/`: 24 tests, 0 failed on throwaway DB `serichai-test-012`; opt-in 5,000-product timing with `CATALOG_PERF=1`. No tour, no hoot. Gates: quickstart.

**Target Platform**: Odoo web client, desktop, tablet, phone (responsive).

**Project Type**: Odoo addon (single area `odoo`).

**Performance Goals**: server side measured on 5,000 products: category change and name/reference/barcode search 0.013-0.016 s (< 1 s, SC-010); first kanban page (80) under 3 s; images `image_512`/`image_128`. Client rendering not measured.

**Constraints**: no cost/margin in any payload for non-purchasing users; no edits to `odoo/` or `muk_web_theme/`; no hard-coded colors; existing product/sales/purchase/inventory screens untouched; labels English + Thai.

**Scale/Scope**: 1 menu, 1 action, 4 views (search, kanban, list, form), 1 model method + 3 computed fields, 1 SCSS file, 1 po file, 24 Python tests.

## Constitution Check

Re-evaluated against the no-JS built state (constitution already updated to it).

| Principle / standard | Result |
|----------------------|--------|
| I Extend, never fork | Pass: new views on `product.template`, `_inherit` for the model; core and MuK untouched; standard product form reached by `action_open_standard_form`. |
| II Odoo conventions | Pass: XML ids `product_catalog_view_<type>`, `product_catalog_action`, `product_catalog_menu`; `views/product_template_views.xml`; `models/product_template.py`; `action_` method with `ensure_one()`; SCSS classes `o_serichai_product_catalog_*`. |
| III Security by default | Pass: cost-derived computed fields carry `groups=purchase.group_purchase_user` (arch nodes stripped, `read` raises `AccessError`); no `sudo()`, no SQL, no new model/ACL/group/rule; writes ride the existing `product.template` ACL (manager only); editable description and photo rendered only for managers AND refused by ACL for others. Known residual: core lets internal users read `standard_price`/supplierinfo over RPC (R6, unchanged). |
| IV Tests | Pass: positive and negative access tests, arch-per-role, computed values, SCSS lint, browse-only, standard views untouched (design.md section 8). |
| JS/OWL standard | N/A: the addon has no JS. |
| V Spec first | Pass: requirement groups map to key files (design.md section 6). Visual items not verifiable headless are listed as manual checks (quickstart). |
| SCSS standard | Pass: 4-space, <= 80 columns, no ID selectors, `o_serichai_product_catalog` prefix, CSS variables only; `test_scss_has_no_hardcoded_colors` fails on hex, `rgb(`, `hsl(`, `--bs-`, `.text-primary`. |
| M2M both-sides rule | N/A. |

Gate: see quickstart (Python tests only). No violations.

## Project Structure

### Documentation (this feature)

```text
specs/012-product-catalog/
├── plan.md  research.md  data-model.md  quickstart.md  design.md
├── spec.md  tasks.md  quality-report.md      # owned by other steps
└── (no contracts/: one area, no cross-area interface)
```

### Source Code (actual)

```text
serichai-odoo/serichai_product_catalog/
├── __init__.py                          # imports models
├── __manifest__.py                      # 19.0.1.2.0; data: view xml; assets: scss only
├── models/{__init__,product_template}.py # 3 computed fields + action_open_standard_form
├── views/product_template_views.xml     # search, kanban, list, form, action, menu
├── static/src/scss/catalog.scss         # the only static asset
├── i18n/{serichai_product_catalog.pot,th.po}
└── tests/{__init__,test_product_catalog}.py
```

**Structure Decision**: single addon, single area `odoo`. `static/src` holds only `scss/catalog.scss`; the former
`static/src/views`, `static/src/fields`, `static/tests` and the tour do not exist.

## API Contracts

None. The only new callable is the in-process `product.template.action_open_standard_form()`.

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| One Python method although the lean plan was "no Python" | FR-015 needs a button opening the current record in the standard form | `type="action"` on an `act_window` cannot carry `res_id` from XML |
| 3 computed fields although "no new field" | Tiles for price incl. tax, cost incl. tax and margin (FR-031) | Parsing `tax_string` client side is brittle; cost-derived values must be group-restricted server side (R13) |
| Duplicate `description` nodes (editable for managers, readonly otherwise); same pattern for the photo (`image_1920` vs readonly `image_1024`) | The web client does not make fields readonly from model ACL (R3); UI must match the server refusal | A single field + `readonly` expression cannot test groups |

The previous rows for the OWL layer were dropped with the layer (R11-R18 superseded).
