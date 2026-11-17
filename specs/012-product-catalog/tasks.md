# Tasks: Product Catalog

**Input**: `specs/012-product-catalog/` (spec.md, plan.md, research.md, data-model.md, design.md, quickstart.md; no contracts/)
**Area**: single area `odoo` (root `serichai-odoo/`, fullstack). Addon root below is `ADDON = serichai-odoo/serichai_product_catalog`.
**Tests**: Included (constitution principle IV; design.md section 8 defines them).
**Gate**: `cd odoo && ../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d <db> --test-enable --stop-after-init --test-tags /serichai_product_catalog -u serichai_product_catalog`

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: parallelizable (different file, no dependency on an unfinished task)
- Tasks touching the same file are sequential. XML ids, class names and snippets come from design.md (section in brackets).

---

## Phase 1: Setup (rework the existing skeleton)

- [X] T001 Update `ADDON/__manifest__.py` per design.md [4.1]: version `19.0.1.0.0`, depends `product`, `account`, `purchase`, data `views/product_template_views.xml`, `web.assets_backend` entry for `static/src/scss/catalog.scss`
- [X] T002 [P] Create `ADDON/models/__init__.py` (imports `product_template`) and update `ADDON/__init__.py` to `from . import models`
- [X] T003 [P] Create `ADDON/tests/__init__.py` (imports `test_product_catalog`)
- [X] T004 Rename `ADDON/views/catalog_views.xml` to `ADDON/views/product_template_views.xml` (keep content for now) and rename XML ids to `product_catalog_view_search|kanban|list|form`, `product_catalog_action`, `product_catalog_menu` [2, 4.8]

## Phase 2: Foundational (blocks all stories)

- [X] T005 Create `ADDON/models/product_template.py`: `_inherit = 'product.template'`, `action_open_standard_form()` with `ensure_one()` returning an `ir.actions.act_window` on `product.product_template_only_form_view`/`product.template` with `res_id=self.id`, form mode [4.2]
- [X] T006 Define the action and top-level menu in `ADDON/views/product_template_views.xml`: `ir.actions.act_window` `product_catalog_action` on `product.template`, `view_mode` `kanban,list,form`, `view_ids` binding the catalog views, `search_view_id`, default `active` domain only; menu `product_catalog_menu` visible to `base.group_user` [4.8]
- [X] T007 Rework the base of `ADDON/static/src/scss/catalog.scss`: 4-space indent, lines at most 80 columns, no ID selectors, `o_serichai_product_catalog` prefix on every class, Bootstrap CSS variables only (`--bs-primary`, `--bs-primary-rgb`, `--bs-border-color`, `--bs-tertiary-bg`), no hex or rgb literals; remove the old `.o_catalog_spec` block [3, 4.9]

**Checkpoint**: the addon installs and the Catalog menu opens an (unstyled) action.

## Phase 3: User Story 1 - Browse and find products as a visual catalog (P1) MVP

**Goal**: card and list browsing, one search box (name, reference, barcode), category filter/group, counter and paging (FR-001..FR-006, FR-019..FR-021).
**Independent test**: install, open **Catalog** as an internal user, search by name/reference/barcode, filter by category, toggle list, see the empty state on no match.

- [X] T008 [P] [US1] Add test `test_search_by_name_reference_barcode` and `test_action_views_load_for_internal_user` in `ADDON/tests/test_product_catalog.py` using `web_search_read` with the catalog search view [8]
- [X] T009 [US1] Search view `product_catalog_view_search` in `ADDON/views/product_template_views.xml`: one `name` field with `filter_domain` over `name`, `default_code`, `barcode` (case-insensitive), `categ_id` field, group-by Category [4.3]
- [X] T010 [US1] Kanban view `product_catalog_view_kanban` in `ADDON/views/product_template_views.xml`: `image_512` card, name, reference, `list_price` with `monetary` widget, Sale/Purchase badges (`text-bg-success`, `text-bg-info`), placeholder when no picture [4.4]
- [X] T011 [US1] List view `product_catalog_view_list` in `ADDON/views/product_template_views.xml`: image (`image_128`), name, reference, category, price; `export_xlsx="0"` [4.5]
- [X] T012 [US1] Card and toolbar styling in `ADDON/static/src/scss/catalog.scss`: hover lift and border, badge spacing, responsive single column at phone width, no horizontal scroll [4.9]
- [X] T013 [US1] Empty-state help text on the action in `ADDON/views/product_template_views.xml` (no results / no products) [4.8]

**Checkpoint**: US1 works alone (clicking a card may open a plain form).

## Phase 4: User Story 2 - Full-screen product page (P1)

**Goal**: product opens full screen with hero, tiles and Specification / Sales / Purchase tabs; Back restores search state (FR-007..FR-011, FR-015, FR-016).
**Independent test**: click a card, see the hero, tiles and tabs (Specification first), breadcrumb **Catalog** returns with the search kept.

- [X] T014 [P] [US2] Add tests `test_form_view_has_spec_first_tab`, `test_open_standard_form_returns_record_action` in `ADDON/tests/test_product_catalog.py` [8]
- [X] T015 [US2] Form view `product_catalog_view_form` hero in `ADDON/views/product_template_views.xml`: `sheet` with `image_1024`, name, reference, category, badges, key-figure tiles (price, `tax_string`), technical data group (barcode, UoM, weight, volume, `attribute_line_ids` readonly list); every field `readonly="1"` except the Specification [4.6]
- [X] T016 [US2] Notebook in the same form: Specification (default) with read-only `description` (html widget), Sales page (`list_price`, `tax_string`, `taxes_id`, `description_sale`); omit margin [4.7] _(Superseded by T041/T040 for FR-031: margin and cost tiles now shown to purchasing users only; this task stays done.)_
- [X] T017 [US2] Header button "Open Standard Form" (`type="object"`, `action_open_standard_form`) shown to all internal users in `ADDON/views/product_template_views.xml` [4.6]
- [X] T018 [US2] Detail page styling in `ADDON/static/src/scss/catalog.scss`: hero image, key-figure tiles, active tab accent, spec table header tint, callout, overflow guard for wide tables; check the `.o_notebook .nav-link.active` and `--KanbanRecord-width` selectors in the browser [3, 4.9]

**Checkpoint**: US1 + US2 deliver the browsable catalog (MVP).

## Phase 5: User Story 3 - Maintain the specification (P2)

**Goal**: product managers edit and save the Specification; others cannot (FR-013, FR-014, FR-016).
**Independent test**: as a product manager edit and save the spec and see it in the standard form; as a plain user the field is read-only and a write raises `AccessError`.

- [X] T019 [P] [US3] Add tests `test_manager_can_write_description`, `test_plain_user_cannot_write_description`, `test_get_view_description_editable_per_role` in `ADDON/tests/test_product_catalog.py` [8]
- [X] T020 [US3] In the form of `ADDON/views/product_template_views.xml` add the editable `description` node with `groups="product.group_product_manager"` and keep the readonly copy for other users (opposite `groups`), `edit="true"` on the form [4.7, 7]
- [X] T021 [US3] Spec content styling (tables, callouts, links) in `ADDON/static/src/scss/catalog.scss` under the `o_serichai_product_catalog` prefix [4.9]

## Phase 6: User Story 4 - Purchasing-only cost and supplier data (P2)

**Goal**: Purchase page visible only to purchasing users (FR-011, FR-012).
**Independent test**: purchase user sees cost, taxes, supplier list; plain user has no Purchase page and no cost anywhere in the catalog.

- [X] T022 [P] [US4] Add tests `test_purchase_page_stripped_for_plain_user`, `test_purchase_page_present_for_purchase_user` (`get_view`) and `test_list_export_disabled` in `ADDON/tests/test_product_catalog.py` [8]
- [X] T023 [US4] Purchase page in the form notebook of `ADDON/views/product_template_views.xml` with `groups="purchase.group_purchase_user"`: `standard_price`, `supplier_taxes_id`, `seller_ids` embedded readonly list (supplier, minimum quantity, price, delay), `description_purchase` [4.7]

## Phase 7: User Story 5 - Polished look in the theme colors (P2)

**Goal**: all accents derive from the MuK theme palette; follows a color change in light and dark (FR-018, FR-019, SC-006).
**Independent test**: change the primary color in Settings and reload: price text, active tab, hover border, table header and callout follow.

- [X] T024 [P] [US5] Add test `test_scss_has_no_hardcoded_colors` (scan `static/src/scss/catalog.scss` for `#hex`, `rgb(`, `hsl(`) in `ADDON/tests/test_product_catalog.py` [8]
- [X] T025 [US5] Review `ADDON/static/src/scss/catalog.scss` against design.md section 3: never use `.text-primary` (MuK maps it to the dark brand color); use `--bs-primary`, `--bs-primary-rgb`, `--bs-primary-text-emphasis`; confirm dark mode uses the same variables [3]

## Phase 8: Polish & cross-cutting

- [X] T026 [P] Create `ADDON/i18n/serichai_product_catalog.pot` and `ADDON/i18n/th.po` with Thai labels for every user-visible string (menu, search placeholders, tabs, badges, empty states, button) (FR-022) [4.10]
- [X] T027 [P] Add a `serichai_product_catalog` section to `/home/odoo/serichai-odoo/CLAUDE.md` and the constitution's Addons list in `/home/odoo/serichai-odoo/.specify/memory/constitution.md` (plan.md note)
- [ ] T028 Run the gate command on a throwaway DB (`-d serichai-test-012`, `-i serichai_product_catalog`): all tests pass, no missing-translation or view-validation warnings; then `-u` on `serichai-db` per quickstart.md
- [ ] T029 Walk the manual checklist in `specs/012-product-catalog/quickstart.md` (MuK theme, plain user / purchase user / product manager, theme color change, 400px width) and record results

## Phase 9: Convergence

- [X] T030 Add test `test_standard_product_views_untouched` in `serichai-odoo/serichai_product_catalog/tests/test_product_catalog.py`: assert `product.product_template_action` and the stock product form/list/kanban views are not modified by the addon (no `inherit_id` on stock views, standard menus unchanged) per FR-017 (missing)
- [X] T031 Add a one-off timing check for 5,000 products (script or test tagged `-standard`, in `serichai-odoo/serichai_product_catalog/tests/test_product_catalog.py`): name/reference/barcode search via the catalog filter returns under 2 s, first kanban page (limit 80) under 3 s per SC-008 (missing)

## Phase 10: OWL layer foundation (amended spec: US6, FR-023..034, SC-009..012)

**Purpose**: assets, computed fields and tests that block the OWL views. Paths follow design.md [Amended] (sections in brackets). Decisions: research R11-R18 (js_class extension, margin and cost tiles for purchasing users only, hoot + tour).

- [X] T032 Update `ADDON/__manifest__.py` [4.1]: version `19.0.1.1.0`; `web.assets_backend` adds `serichai_product_catalog/static/src/**/*.js` and `static/src/**/*.xml` next to the SCSS; `web.assets_unit_tests` adds `static/tests/**/*.test.js`; `web.assets_tests` adds `static/tests/tours/**/*` _(Amended: assets are now the SCSS only; version 19.0.1.2.0, see T049.)_
- [X] T033 [P] [US6] Add Python tests in `ADDON/tests/test_product_catalog.py` [8]: plain user `read(['catalog_margin'])` and `read(['catalog_cost_incl_tax'])` raise `AccessError`; purchase user gets `list_price - standard_price` and cost incl. purchase tax (100 + 7% = 107); `catalog_price_incl_tax` correct for 7% tax and equals list price with no tax; `get_view` for a plain user has no `standard_price`, `catalog_margin`, `catalog_cost_incl_tax`, `seller_ids`, purchase user has the margin/cost nodes, kanban and list never contain them; kanban `js_class="serichai_catalog_kanban"`, list `serichai_catalog_list` with `export_xlsx="0"`; `web_read` of the form spec as plain user returns no cost-derived value; a product without taxes, image, reference or category reads without error _(Amended: the `js_class` assertions and `test_js_classes_on_kanban_and_list` were removed with the OWL layer.)_
- [X] T034 [US6] Add the three non-stored computed fields to `ADDON/models/product_template.py` [4.2]: `catalog_price_incl_tax` (ungated), `catalog_cost_incl_tax` and `catalog_margin` with `groups='purchase.group_purchase_user'`; purchase unit of measure taken from the first vendor line's unit, else `uom_id` (no `uom_po_id` in Odoo 19); no `sudo()`

**Checkpoint**: T033 tests pass against the new fields; assets bundle loads with no JS yet.

## Phase 11: User Story 6 - Richer catalog interface matching the mock (P2)

**Goal**: one in-page toolbar (search, category dropdown, highlighted Grid/List switch, counter and pager), polished cards and rows, hero, key-figure tiles, pills, vendor and technical tables (FR-023..034, SC-009..012).
**Independent test**: open Catalog as plain user and as purchasing user, compare with `product_catalog_mock.html` using the FR-023..033 checklist; search, pick a category, switch to list, open a product, go back and see search, category, view and selected row restored.

- [X] T035 [P] [US6] Write hoot tests `ADDON/static/tests/catalog_toolbar.test.js` [8]: counter shows "1 product" / "N products" / "0 products" from `model.root.count`; typing adds a `name` facet and picking a category adds a `categ_id` facet, each reloads; switch buttons mark the active view and call `switchView`; hero omits missing reference/category; tiles omit margin when `catalog_margin` is absent and price incl. tax when there is no tax _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T036 [P] [US6] Create the shared toolbar component `ADDON/static/src/views/catalog_toolbar.js` and `ADDON/static/src/views/catalog_toolbar.xml` [4.3]: text input driving the existing `name` search item, category `<select>` loaded by one `formattedReadGroup` on `categ_id` as the caller, Bootstrap `btn-group` Grid/List switch calling `action.switchView`, core `Pager` and counter with two literal `_t` strings (singular/plural); classes only, no inline colors _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T037 [US6] Create `ADDON/static/src/views/catalog_kanban.js` and `ADDON/static/src/views/catalog_kanban.xml` [4.4]: subclass of the core kanban controller registered as `serichai_catalog_kanban`, inject `CatalogToolbar` via `t-inherit` of `web.KanbanView`, set `display.controlPanel = false`, keep last opened record id in local state for the `o_selected` card on return (merge with parent `getLocalState`); depends on T036 _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T038 [US6] Create `ADDON/static/src/views/catalog_list.js` [4.4]: list view registered as `serichai_catalog_list` with the same toolbar and selected-row state, `t-inherit` of `web.ListView`; depends on T036, same file pattern as T037 _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T039 [P] [US6] Create the hero field widget `ADDON/static/src/fields/catalog_hero_field.js` and `ADDON/static/src/fields/catalog_hero_field.xml` [4.6]: large picture or neutral placeholder, name, `reference · category` line with missing parts omitted, Sale/Purchase pills; register in the `fields` registry _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T040 [P] [US6] Create the key-figure tiles widget `ADDON/static/src/fields/catalog_tiles_field.js` and `ADDON/static/src/fields/catalog_tiles_field.xml` [4.7]: Sales tiles (price, price incl. tax, margin only when `catalog_margin` is present) and Purchase tiles (cost, cost incl. tax, purchase unit of measure); tile omitted when its value is absent; register in the `fields` registry _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T041 [US6] Rework `ADDON/views/product_template_views.xml` [4.5-4.8]: `js_class` on kanban and list; hero and tiles widgets in the form hero and in the Sales and Purchase pages; tax and attribute values as restyled `many2many_tags` pills; vendor pricelist as readonly list with right-aligned numbers and lead time in days; technical data as a label/value table; keep Specification first with its empty message; no cost, margin or seller field in kanban or list; margin and cost tile fields inside purchasing-group nodes only; depends on T034, T039, T040 _(Amended: hero, tiles, pills, tables and attribute lines are native XML; see T050, T055, T056.)_
- [X] T042 [US6] Extend `ADDON/static/src/scss/catalog.scss` [3, 4.9]: toolbar, active switch button, card tinted picture area and selected state, list row hover tint, tiles, pills, vendor and technical tables, responsive wrap at 360, 768 and 1280 px; only `--bs-*` variables (no hex, `rgb(`, `hsl(`, no `.text-primary`), 80 columns, prefix `o_serichai_product_catalog`; keep `test_scss_has_no_hardcoded_colors` green _(Amended: SCSS reworked, see T052-T056.)_
- [X] T043 [P] [US6] Create the tour `ADDON/static/tests/tours/catalog_tour.js` and the Python runner `ADDON/tests/test_catalog_tour.py` (HttpCase `TestCatalogTour`, tagged `post_install`, `-at_install`) and import it in `ADDON/tests/__init__.py` [8]: search "CH-01", pick a category, switch to list, open the product, return by breadcrumb, assert search text, category and view restored and the row has `o_selected` _(Superseded 2026-11-18: removed with the OWL layer, see Phase 14 T049.)_
- [X] T044 [P] [US6] Update `ADDON/i18n/serichai_product_catalog.pot` and `ADDON/i18n/th.po` [4.10]: Thai for every new `_t()` and QWeb literal string (toolbar placeholder, "product"/"products" counter, All categories, Grid, List, tile labels, empty states) (FR-022) _(Amended: OWL strings pruned from `th.po`, new XML strings added, see T058.)_

**Checkpoint**: US6 works for both roles; native Back restore and existing tests still green.

## Phase 12: Amended polish

- [X] T045 [P] Update the `serichai_product_catalog` section of `/home/odoo/serichai-odoo/CLAUDE.md` and the Addons list in `/home/odoo/serichai-odoo/.specify/memory/constitution.md`: OWL `js_class` views, computed catalog fields, test commands _(Amended: CLAUDE.md and the constitution now describe a no-JS addon.)_
- [ ] T046 Run the amended gate from quickstart.md on a throwaway DB (`-d serichai-test-012`, `-i serichai_product_catalog`, `--test-tags /serichai_product_catalog`) including the tour, then the hoot suite with headless Chrome; fix hoot filter syntax if needed; supersedes T028
- [ ] T047 Walk manual checks 8-12 in `specs/012-product-catalog/quickstart.md`: mock comparison against FR-023..033 (SC-009), result update under 1 s at 5,000 products (SC-010), role access test with zero leaks (SC-011), no horizontal scrollbar at 360, 768 and 1280 px (SC-012), theme recolor and dark mode; supersedes T029

---

## Dependencies and order

- Phase 1 then Phase 2, then US1 (T008..T013), then US2 (T014..T018), then US3/US4/US5 (all edit the same form XML and SCSS, so run in order US3, US4, US5 or serialize per file), then Phase 8.
- US2 builds on the views from US1. US3 and US4 extend the form from US2. US5 reviews the SCSS built through earlier phases.
- Every XML task edits `ADDON/views/product_template_views.xml`; every test task edits `ADDON/tests/test_product_catalog.py`; SCSS tasks edit `ADDON/static/src/scss/catalog.scss`, so only tasks in different files carry [P].

## Parallel examples

- Setup: T002 and T003 together.
- Per story: the test task ([P]) alongside the first XML task of that story (different files).
- Polish: T026 and T027 together.

## Implementation strategy

- **MVP**: Phases 1-4 (US1 + US2): a browsable catalog with a full-screen page.
- Then US3 (spec editing), US4 (purchase data), US5 (theme review), then translations, docs and the full gate.
- Open questions accepted at GATE 2: core RPC exposure of cost/supplier data stays; margin tile omitted; product menu icon reused; "Open Standard Form" shown to all internal users.

## Amended dependencies (US6)

- Phases 1-9 are done. T032 and T033 can start together, T034 follows T033 (tests first).
- T036 before T037/T038; T039 and T040 in parallel with them; T041 after T034, T039, T040; T042 after T041; T043 and T044 after T041.
- Same-file rule: `product_template_views.xml` (T041), `test_product_catalog.py` (T033), `catalog.scss` (T042), `__manifest__.py` (T032) are single tasks, so no conflicts.
- MVP of the amendment: T032-T042 (toolbar, cards, page widgets); T043-T047 verify and document.
- Decisions from GATE 2 (defaults accepted): margin and cost-incl-tax tiles for purchasing users only (supersedes "margin tile omitted" above), core RPC exposure unchanged, product menu icon reused, native Sale/Purchase filter dropdown dropped, selected = last opened product.

## Phase 13: Convergence

- [X] T048 Extend the opt-in timing test `test_perf_5000_products` in `serichai-odoo/serichai_product_catalog/tests/test_product_catalog.py` (or add a hoot/tour timing step in `serichai-odoo/serichai_product_catalog/static/tests/tours/catalog_tour.js`) to assert that a category change and a search change with 5,000 products return results in under 1 second, per SC-010 (missing)

## Phase 14: Rework after review - drop OWL, native views, UI polish (2026-11-17..18)

Built from direct user requests after the OWL implementation; recorded here so tasks match the code. Paths under `ADDON = serichai-odoo/serichai_product_catalog`.

- [X] T049 Remove the OWL layer: delete `ADDON/static/src/views/`, `ADDON/static/src/fields/`, `ADDON/static/tests/` and `ADDON/tests/test_catalog_tour.py`; `ADDON/__manifest__.py` assets = `catalog.scss` only, version `19.0.1.2.0`; remove `test_js_classes_on_kanban_and_list` from `ADDON/tests/test_product_catalog.py` (supersedes the JS parts of T035-T044)
- [X] T050 [US6] Native product page in `ADDON/views/product_template_views.xml`: hero, key-figure tiles (Sales: price, price incl. tax, margin for purchasing users; Purchase: cost, cost incl. tax, unit of measure), pills and tables as plain XML fields; native control panel and standard pager restored
- [X] T051 [US1] Search view `product_catalog_view_search` like the standard product search in `ADDON/views/product_template_views.xml`: name/reference/variant reference/barcode box, category (child_of), tags, filters Goods/Services/Combo/Favorites/Can be Sold/Can be Purchased, group by Product Type and Category, no Archived filter; action context defaults Goods AND Can be Sold (separate filter groups) and action domain `[('active', '=', True)]`; Thai labels in `ADDON/i18n/th.po`
- [X] T052 [US1] [US5] Kanban grid in `ADDON/static/src/scss/catalog.scss`: 4 cards per row (3 below 992 px, 2 below 768 px, 1 below 576 px) targeting `.o_kanban_renderer.o_kanban_ungrouped` with `display: grid !important`; card radius 1rem, theme-tint border, white body, hover lift and soft shadow, picture area 11rem
- [X] T053 [US5] Pastel picture areas cycling over five cards in `ADDON/static/src/scss/catalog.scss`: lavender, mint, light blue, pink (color-mix of `--pink`), cream
- [X] T054 [US5] Fix theme variables in `ADDON/static/src/scss/catalog.scss`: Odoo 19 has no `bs-` prefix (`--primary`, `--primary-rgb`, `--border-color`, ...); card selector specificity raised over core `.o_kanban_record:not(.o_kanban_ghost)`; `test_scss_has_no_hardcoded_colors` in `ADDON/tests/test_product_catalog.py` also rejects `--bs-`
- [X] T055 [US6] Technical Data table with a separator line per row and aligned label/value, in `ADDON/views/product_template_views.xml` and `ADDON/static/src/scss/catalog.scss` (attribute lines were built, then DROPPED at the owner's request on 2026-11-18; no attribute row and no attribute SCSS remain)
- [X] T056 [US6] Product page layout from `product_catalog_mock (1).html`: two columns (sticky sidebar with 300 px tinted picture, name, reference . category, large price, "Can be Sold / Can be Purchased" badges; tabs on the right), max width 1400 px, stacked below 900 px, in `ADDON/views/product_template_views.xml` and `ADDON/static/src/scss/catalog.scss`
- [X] T057 [US3] Editable product photo for product managers (`image_1920`, preview `image_1024`, `groups="product.group_product_manager"`) with a readonly `image_1024` copy for others in `ADDON/views/product_template_views.xml`; tests `test_manager_can_update_photo_plain_user_cannot` and `test_get_view_photo_editable_per_role` in `ADDON/tests/test_product_catalog.py` (extends FR-015 from Specification to Specification and photo)
- [X] T058 i18n and docs: `ADDON/i18n/serichai_product_catalog.pot` and `ADDON/i18n/th.po` re-exported and pruned, `/home/odoo/serichai-odoo/CLAUDE.md` and `/home/odoo/serichai-odoo/.specify/memory/constitution.md` describe the no-JS addon
- [ ] T059 Browser verification (needs a person or headless Chrome; supersedes T028, T029, T046 and T047): grid 4/3/2/1, pastels, hover shadow, form layout against the newer mock, attribute lines, technical-data separators, photo upload as manager vs plain user, default filters, theme recolor and dark mode, widths 360/768/1280, mock sign-off (SC-007, SC-009, SC-012), client-side search timing (SC-010)
- [ ] T060 Refresh `specs/012-product-catalog/quality-report.md` for the no-OWL rework (run the quality review again after T059 findings are fixed)

---

## Status note (2026-11-18)

Phases 1-9 and 10-14 (except T028, T029, T046, T047, T059, T060) are done. Python gate: 24 tests, 0 failed on the throwaway DB. Open items all need a browser. T028/T029/T046/T047 are superseded by T059.
