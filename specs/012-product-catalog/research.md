# Research: Product Catalog

All items verified in the local source (`odoo/addons`, `muk_web_theme`). No NEEDS CLARIFICATION remain.

## R1. Theme color chain (FR-018, SC-006) [CORRECTED by R19-R22: variable names have no `bs-` prefix]
- Decision: color every accent with Bootstrap CSS variables, never hex.
- Evidence: `muk_web_colors/static/src/scss/colors.scss` sets `$o-brand-primary: $mk-color-primary` (#5D8DA8) plus
  `$o-success/$o-info/$o-warning/$o-danger`, and `colors_light.scss` / `colors_dark.scss` do the same for dark; the
  Settings screen rewrites those SCSS assets (`color_assets_editor.py`) and the bundle is rebuilt.
  `web/static/src/scss/bootstrap_overridden.scss:31` `$primary: $o-brand-primary`, `:35-36` `$success/$info`. Bootstrap
  compiles them to `--bs-primary`, `--bs-primary-rgb`, `--bs-primary-bg-subtle`, `--bs-primary-text-emphasis`,
  `--bs-border-color`, `--bs-tertiary-bg`, `--bs-secondary-color`, `--bs-body-bg` (all present in
  `lib/bootstrap/dist/css/bootstrap.css`, and redefined for `data-bs-theme=dark`).
- Gotcha: MuK sets `$o-theme-text-colors: ("primary": $mk-color-brand ...)` so `.text-primary` is the dark brand
  (#243742), not `--bs-primary`. Use explicit `var(--bs-primary)` / `var(--bs-primary-text-emphasis)` in SCSS.
  `text-bg-success`/`text-bg-info` (badges) follow `$o-success`/`$o-info`, so they are theme-driven too.
- Mock's `#714b67` purple, `#e8dff5` pastel backgrounds and emoji images are mock data only; replaced by variables.
- Alternative rejected: SCSS `$o-brand-primary` at build time (only works in the primary-variables bundle; CSS vars are enough and keep
  the file in `web.assets_backend`).

## R2. Kanban syntax (Odoo 19)
- `kanban` uses `<templates><t t-name="card">` (see `product/views/product_template_views.xml:125`); `main`, `aside`, `footer`
  are valid children. Root `class` is forwarded to the renderer, so `<kanban class="o_serichai_product_catalog_kanban">` allows
  scoping. `--KanbanRecord-width` (`views/kanban/kanban_controller.scss:98`, default 320px) controls card width; override to ~12rem for a
  dense grid. Mobile: records are full width automatically (`media-breakpoint-down(md)`).
- Empty image: `image` widget falls back to `/web/static/img/placeholder.png` (`fields/image/image_field.js:25`) so cards stay aligned (spec US1-6). `sample="1"` keeps a demo layout on an empty database.
- Pager, counter and view switcher are native from `view_mode="kanban,list,form"`; default kanban limit is 80.

## R3. Editing rights and the html widget (FR-014)
- ACL: `product/security/ir.model.access.csv` line 3 gives `base.group_user` read only; line 19 gives write to
  `product.group_product_manager` only (stock/purchase/mrp/pos add read-only rows). The spec says "already able to edit products", i.e. this ACL, so
  `product.group_product_manager` is the exact group to gate the editable field on (any group implying it is covered).
- `form_controller.js` has no ACL-driven readonly: a form with an editable field stays editable for a user without write right and
  fails only on save. So the lean plan's "readonly automatically" is false. Decision: two `description` nodes with mutually exclusive `groups`
  (`product.group_product_manager` editable, `!product.group_product_manager` with `readonly="1"`); the server drops the non-matching node
  when processing the arch (`groups` on a field), and the ACL refuses a forged write. A user losing rights mid-session gets Odoo's AccessError dialog on Save (edge case).
- Widget: `widget="html"` is `html_editor/static/src/fields/html_field.js` (toolbar: colors, lists, tables via powerbox, links). Read-only render uses the same component, so formatting is preserved. Save/Discard come from the form control panel.

## R4. Search (FR-004/005)
- `<field name="name" filter_domain="['|','|',('name','ilike',self),('default_code','ilike',self),('barcode','ilike',self)]"/>` works on
  `product.template`: `default_code` and `barcode` are non-stored computed fields with `search=` methods (`product_template.py:156-157`). `ilike` is case-insensitive and partial. `name` has a trigram index (`:85`) for SC-008.
- `<field name="categ_id" operator="child_of"/>` filters by category incl. children; group-by via `<filter context="{'group_by': 'categ_id'}">`.
- Searchpanel (sidebar) rejected: takes width on tablet/phone and adds a second filter UI to the mock's single toolbar select.
- Archived products: default `active` filter; no filter shown.

## R5. Tax and margin (FR-008, FR-010)
- `tax_string` exists on `product.template` (`account/models/product.py:46`, computed non-stored from `taxes_id` for the current company): returns `(= 107.00 Incl. Taxes)` or `" "` when no tax. Use in a tile and Sales tab, `invisible="not taxes_id"`.
- Margin: `product_margin` adds `total_margin/expected_margin` to `product.product` only, invoice/date based; `sale_margin` is on sale lines. There is no template margin field.
  Computing `list_price - standard_price` would need new Python plus cost exposure to non-purchase users. Decision: omit the tile (spec: only when margin data exists).

## R6. Cost confidentiality (FR-011/012, SC-004)
- `standard_price` has `groups="base.group_user"` (`product_template.py:107`); `product.supplierinfo` read is `base.group_user` (csv line 4).
  View `groups` on the page removes the node and its fields from the served arch for others, so no catalog screen contains cost/supplier data. Direct RPC by an
  internal user remains possible (core behaviour, FR-017). Kanban/list never include these fields.
- "Exports of the catalog view": `<list export_xlsx="0">` (`list_arch_parser.js:191`) removes the Export action; kanban has none.

## R7. Button to the standard form (FR-015)
- `type="action"` with `%(product.product_template_action)d` opens the product list, not this record. Odoo's action service ignores `res_id` unless the
  action dict has it, and `ir.actions.act_window` records have a static `res_id`. Decision: `action_open_standard_form()` returns
  `{'type': 'ir.actions.act_window', 'res_model': 'product.template', 'res_id': self.id, 'view_mode': 'form', 'views': [(False, 'form')]}`; the default form view
  (`product.product_template_only_form_view`) is used. Shown to all internal users (they have read; standard form is readonly for them by ACL on save).

## R8. Back/breadcrumb state (FR-007, SC-003)
- Standard act_window breadcrumbs store the controller `state` (search model, view type, group by, offset), restored by "Catalog" breadcrumb and browser Back. No code. Verify manually (quickstart step 3).
- `view_ids` on the action: `(5,0,0)` then one entry each for kanban/list/form (pattern already in the skeleton) plus `search_view_id`.

## R9. Responsive (FR-021)
- Form sheet reflows via Bootstrap grid classes (`row`, `col-6`, `d-flex flex-column flex-md-row`); tables inside the spec get `overflow-x: auto` wrapper
  by styling `.o_field_html table` as `display: block; max-width: 100%; overflow-x: auto` (avoids page-level horizontal scroll, edge case "wide tables").
  Images `max-width: 100%`.

## R10. Manifest and i18n
- Version should be `19.0.1.0.0` (skeleton has `1.0.0`; sibling addons use their own scheme but Odoo requires the series prefix for non-core). `assets: web.assets_backend` is correct for backend SCSS.
- Thai: view `string=` and menu/action names are exported automatically; ship `i18n/th.po` (+ `.pot`); the menu `name`, tiles, empty messages, tab names must be literal strings.

# Amendment (User Story 6, FR-023..034): OWL decisions SUPERSEDED

The OWL layer was built and then removed at the user's request ("minimize owl component and remove if possible").
The addon is native views + XML + one SCSS file + 3 computed fields. R11, R12, R14, R15 (OWL part), R16 (OWL part),
R17 (OWL part) and R18 (JS parts) no longer apply; R13 still applies.

## R11. js_class extension vs standalone client action [SUPERSEDED]
- Was: `js_class` kanban/list views with a shared OWL toolbar replacing the control panel.
- Why superseded: the toolbar (search box, category dropdown with counts, Grid/List switch, custom counter/pager) cost
  ~250 lines of JS plus hoot tests and a tour, and depended on semi-internal view templates. The standard control panel
  gives search facets, view switcher and pager ("1-51 / 51") with no code. Dropped as a consequence: the category
  dropdown with counts (Category stays a search field and a group-by), the "N products" singular/plural counter, and
  the "selected = last opened" card/row marker.
- Still true: a standalone client action stays rejected (loses breadcrumb restore and arch-level group stripping).

## R12. Toolbar behavior on the standard search model [SUPERSEDED]
- Replaced by the search view itself: one `name` item with `filter_domain` over name, internal reference, variant
  reference and barcode (case-insensitive, partial); `categ_id` with `child_of`; tags; filters and group-bys (design 4.1).

## R13. Cost-derived tiles confidentiality [STILL VALID]
- `catalog_margin` and `catalog_cost_incl_tax`: non-stored Monetary fields with `groups='purchase.group_purchase_user'`.
  The arch nodes are stripped for other users and `read` raises `AccessError`, so nothing cost-derived is in any payload
  for non-purchasing users. `catalog_price_incl_tax` is ungated (same information as `tax_string`).
- R6 not worsened: core still lets internal users read `standard_price` by RPC; these fields add no read path.
- Purchase tile "Unit of Measure" shows the product's own `uom_id`. The earlier idea "first vendor line's unit" was a
  client-side OWL computation and was dropped with OWL.

## R14. Grid/List persistence across the form round-trip [SUPERSEDED]
- Native: both views belong to one action and share its search model; breadcrumb or Back restores view type and query
  (R8). The "selected = last opened" marker needed `getLocalState` in OWL and was dropped. SCSS still styles
  `.o_record_selected` / `:focus-visible` on cards (core keyboard focus).

## R15. OWL components vs native XML [SUPERSEDED]
- Hero, tiles, pills, tech table and vendor table are plain XML fields plus SCSS classes (`o_serichai_product_catalog_*`),
  vendor table = native readonly list inside the form (lead time titled "Lead Time (days)").

## R16. Colors, light/dark, motion [PARTLY SUPERSEDED]
- Rule kept, variable names corrected (R19). `prefers-reduced-motion` disables the card lift. The Python lint test covers
  `catalog.scss` only (no JS/XML templates exist).

## R17. i18n of OWL templates [SUPERSEDED]
- No OWL templates. Thai labels come from view `string=`, literal text and menu/action names in `i18n/th.po` (+ `.pot`).

## R18. Test approach and gates [SUPERSEDED]
- Python `TransactionCase` only (24 tests); no hoot, no tour. Opt-in timing test with `CATALOG_PERF=1`. See quickstart.

# New findings from the build

## R19. Bootstrap variables have no `bs-` prefix in this Odoo 19 build
- `--bs-primary` etc. are undefined; a declaration using an undefined variable is silently dropped (this broke borders
  and accents during the build). Use `--primary`, `--primary-rgb`, `--primary-text-emphasis`, `--primary-bg-subtle`,
  `--success-bg-subtle`, `--info-bg-subtle`, `--warning-bg-subtle`, `--pink`, `--border-color`, `--border-radius`,
  `--body-bg`, `--body-color-rgb`, `--secondary-color`, `--white`.
- `test_scss_has_no_hardcoded_colors` now also fails on `--bs-`, hex, `rgb(`/`hsl(` literals and `.text-primary`.

## R20. MuK overrides `$o-community-color`
- MuK sets it to a dark navy, so it cannot give "Odoo purple". A fixed purple card border was tried and removed;
  the border is a 35% tint of the theme primary: `rgba(var(--primary-rgb), .35)`.

## R21. Core kanban specificity and `d-flex`
- Core sets `border-color`/`background` on `.o_kanban_record:not(.o_kanban_ghost)`, so the card rule repeats the root
  class, `.o_kanban_record.o_serichai_product_catalog_card:not(.o_kanban_ghost)`, to win.
- The arch `class` lands on the view root, not on the renderer, so the grid rule targets
  `.o_serichai_product_catalog_kanban .o_kanban_renderer.o_kanban_ungrouped`. The renderer has `d-flex` (`!important`),
  hence `display: grid !important`. Ghost cards are hidden.

## R22. Pastels, color-mix, position-based cycling
- Pastels use theme subtle colors: lavender `--primary-bg-subtle`, mint `--success-bg-subtle`, light blue
  `--info-bg-subtle`, cream `--warning-bg-subtle`, pink `color-mix(in srgb, var(--pink) 15%, var(--body-bg))`
  (allowed by the lint; follows light/dark).
- `:nth-child(5n + k)` cycles by card position, not per product: the same product can change color after a search or
  page change. Accepted (decorative).

## R23. Action domain and default filters
- Action `domain` `[('active','=',True)]` is explicit and ANDs with the search facets. `context` sets
  `search_default_goods` and `search_default_filter_sale`; they sit in different filter groups (separated by
  `<separator/>`), so they combine with AND (Goods AND Can be Sold). Filters in the same group would be OR. No Archived
  filter is offered.

## R24. Attribute pills without the "Attribute:" prefix
- `many2many_tags` of attribute values shows "Attribute: value" in Odoo 19 unless the context `show_attribute=False` is
  passed. A one-line-per-attribute readonly nested kanban was built and later REMOVED at the owner's request
  (2026-11-18): attributes are not displayed on the product page, and the unused SCSS rules were deleted.

## R25. Photo editing, preview and group split
- Managers edit `image_1920` with `options="{'preview_image': 'image_1024'}"` (upload/replace/delete from the page).
  Others get `image_1024` readonly in a node with `groups="!product.group_product_manager"`. Same exclusive-groups
  pattern as `description` (R3). Server: ACL `access_product_template_manager` refuses other writes
  (`test_manager_can_update_photo_plain_user_cannot`). This extends FR-015 from "only Specification editable" to
  "Specification and photo".
