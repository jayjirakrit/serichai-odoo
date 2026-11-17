# Design: Product Catalog (review aid, built state)

Snippets are taken from the real code, trimmed. Paths are under `serichai-odoo/serichai_product_catalog/`.
Updated 2026-11-18: the OWL layer was removed; this file describes only what exists.

## 1. Overview

One layer on `product.template`, all native Odoo 19 views: one action (kanban, list, form), one search view, one
top-level menu, plus one SCSS file and three computed fields. No JS, no OWL, no new model, group, ACL or `sudo()`.

```
Menu Catalog -> act_window(kanban | list | form, search view, domain active=True,
                           default filters Goods AND Can be Sold)
  standard control panel: search facets, view switcher, pager "1-N / N"
  card/row click -> form: sidebar (photo, name, price, badges) + tabs Specification | Sales | Purchase
  form header button -> action_open_standard_form -> standard product form
```

Why not a standalone client action or an OWL toolbar: loses breadcrumb/Back restore and arch-level group stripping, and
the standard control panel already covers search, switch and pager (R11, superseded).

## 2. File map

| File | Role |
|------|------|
| `__manifest__.py` | 19.0.1.2.0; depends `product`, `account`, `purchase`; data: view xml; assets: `catalog.scss` only |
| `models/product_template.py` | 3 computed fields + `action_open_standard_form` (4.5) |
| `views/product_template_views.xml` | search, kanban, list, form, action, menu (4.1-4.4) |
| `static/src/scss/catalog.scss` | grid, card, pastels, form layout, tiles, tech table, spec content (4.6-4.8) |
| `i18n/{serichai_product_catalog.pot,th.po}` | Thai labels |
| `tests/test_product_catalog.py` | 24 Python tests (section 8) |

Not created: models, security files, contracts, JS, templates, tours.

## 3. Dropped (OWL)

Removed at the user's request: `js_class` kanban/list views, shared `CatalogToolbar` (search box, category dropdown with
counts, Grid/List switch, custom counter/pager), hero and tiles field widgets, hoot tests, tour. Consequences: standard
control panel instead of the toolbar; no "N products" counter, no category dropdown with counts, no "selected = last
opened" marker; hero and tiles are plain XML fields + SCSS classes; Purchase UoM tile shows the product's own unit.

## 4. Key files

### 4.1 Search view (`product_catalog_view_search`)

One box over name, reference, variant reference and barcode; Goods and Can be Sold live in separate filter groups so
the default facets combine with AND.

```xml
<search string="Product">
    <field name="name" string="Product"
           filter_domain="['|', '|', '|', ('name', 'ilike', self), ('default_code', 'ilike', self), ('product_variant_ids.default_code', 'ilike', self), ('barcode', 'ilike', self)]"/>
    <field name="categ_id" operator="child_of"/>
    <field name="product_tag_ids" string="Tags"/>
    <separator/>
    <filter name="services" string="Services" domain="[('type', '=', 'service')]"/>
    <filter name="combo" string="Combo" domain="[('type', '=', 'combo')]"/>
    <separator/>
    <filter name="favorites" string="Favorites" domain="[('is_favorite', '=', True)]"/>
    <separator/>
    <filter name="goods" string="Goods" domain="[('type', '=', 'consu')]"/>
    <separator/>
    <filter name="filter_sale" string="Can be Sold" domain="[('sale_ok', '=', True)]"/>
    <separator/>
    <filter name="filter_purchase" string="Can be Purchased" domain="[('purchase_ok', '=', True)]"/>
    <group>
        <filter name="groupby_type" string="Product Type" context="{'group_by': 'type'}"/>
        <filter name="groupby_categ" string="Category" context="{'group_by': 'categ_id'}"/>
    </group>
</search>
```

No Archived filter. The action adds the explicit domain and defaults:

```xml
<field name="domain">[('active', '=', True)]</field>
<field name="context">{'search_default_goods': 1, 'search_default_filter_sale': 1}</field>
```

### 4.2 Kanban card (`product_catalog_view_kanban`)

```xml
<kanban create="0" delete="0" sample="1" class="o_serichai_product_catalog_kanban">
    <field name="currency_id"/> <field name="sale_ok"/> <field name="purchase_ok"/>
    <templates>
        <t t-name="card" class="o_serichai_product_catalog_card p-0">
            <field name="image_512" widget="image" alt="Product"
                   class="o_serichai_product_catalog_card_img"
                   options="{'img_class': 'w-100 object-fit-contain'}"/>
            <div class="px-3 pt-2">
                <div class="fw-bold text-truncate"><field name="name"/></div>
                <div class="text-muted small text-truncate" t-if="record.default_code.value">
                    <field name="default_code"/>
                </div>
            </div>
            <footer class="px-3 pb-2 pt-1 align-items-center">
                <field name="list_price" widget="monetary"
                       options="{'currency_field': 'currency_id'}"
                       class="o_serichai_product_catalog_price"/>
                <div class="ms-auto">
                    <span t-if="record.sale_ok.raw_value" class="badge rounded-pill text-bg-success">Sale</span>
                    <span t-if="record.purchase_ok.raw_value" class="badge rounded-pill text-bg-info">Purchase</span>
                </div>
            </footer>
        </t>
    </templates>
</kanban>
```

The list view (`product_catalog_view_list`) is `create/delete/duplicate="0"`, `export_xlsx="0"`, `sample="1"`, with
thumbnail (`image_128`), name, reference, category and price. Neither view carries cost, margin or seller fields.

### 4.3 Form layout (`product_catalog_view_form`)

Two columns (sidebar + tabs), photo split by group, Specification split by group (same pattern as `description`).
`edit="true"` is needed for the managers' fields; every other field is readonly, so plain users get no editable control.

```xml
<div class="o_serichai_product_catalog_layout">
  <div class="o_serichai_product_catalog_side">
    <field name="image_1920" widget="image" class="o_serichai_product_catalog_hero_img"
           groups="product.group_product_manager"
           options="{'preview_image': 'image_1024', 'img_class': 'object-fit-contain'}"/>
    <field name="image_1024" widget="image" readonly="1" class="o_serichai_product_catalog_hero_img"
           groups="!product.group_product_manager" options="{'img_class': 'object-fit-contain'}"/>
    <h3 class="mt-3 mb-1"><field name="name" readonly="1"/></h3>
    <!-- reference . category, big price, badges Can be Sold / Can be Purchased -->
  </div>
  <div class="o_serichai_product_catalog_main">
    <notebook>
      <page name="specification" string="Specification"> ... </page>
      <page name="sales" string="Sales"> ... </page>
      <page name="purchase" string="Purchase" groups="purchase.group_purchase_user"> ... </page>
    </notebook>
  </div>
</div>
```

Specification page: editable node for managers, readonly copy plus friendly empty text for others:

```xml
<field name="description" widget="html" class="o_serichai_product_catalog_spec"
       groups="product.group_product_manager" placeholder="Write the product specification…"/>
<field name="description" widget="html" readonly="1" class="o_serichai_product_catalog_spec"
       groups="!product.group_product_manager" invisible="not description"/>
<div class="text-muted" invisible="description" groups="!product.group_product_manager">
    No specification yet.
</div>
```

Technical Data: label/value table, one separator per row (rows hidden when empty):

```xml
<separator string="Technical Data"/>
<table class="table table-sm o_serichai_product_catalog_tech">
    <tr invisible="not barcode"><th>Barcode</th><td><field name="barcode" readonly="1"/></td></tr>
    <tr><th>Unit of Measure</th><td><field name="uom_id" readonly="1" options="{'no_open': True}"/></td></tr>
    <tr invisible="not weight"><th>Weight</th>
        <td class="o_row"><field name="weight" readonly="1"/><field name="weight_uom_name"/></td></tr>
    <tr invisible="not volume"> ... Volume likewise ... </tr>
</table>
```

Sales tab: tiles in a Bootstrap row; Margin is a node with `groups="purchase.group_purchase_user"`:

```xml
<div class="col-6 col-lg-4" groups="purchase.group_purchase_user">
    <div class="o_serichai_product_catalog_tile">
        <span class="small text-muted d-block">Margin</span>
        <field name="catalog_margin" widget="monetary" readonly="1"
               options="{'currency_field': 'currency_id'}" class="fw-bold"/>
    </div>
</div>
```

Purchase tab (purchasing users only): tiles Cost, Cost incl. Tax, Unit of Measure; vendor tax pills; vendor price list:

```xml
<field name="seller_ids" readonly="1" class="o_serichai_product_catalog_vendors">
    <list>
        <field name="partner_id"/> <field name="min_qty"/> <field name="price"/>
        <field name="delay" string="Lead Time (days)"/>
    </list>
</field>
```

### 4.4 Action and menu

```xml
<field name="view_ids" eval="[(5, 0, 0),
    (0, 0, {'view_mode': 'kanban', 'view_id': ref('product_catalog_view_kanban')}),
    (0, 0, {'view_mode': 'list', 'view_id': ref('product_catalog_view_list')}),
    (0, 0, {'view_mode': 'form', 'view_id': ref('product_catalog_view_form')})]"/>
<menuitem id="product_catalog_menu" name="Catalog" sequence="25"
          web_icon="product,static/description/icon.png"
          action="product_catalog_action" groups="base.group_user"/>
```

### 4.5 `models/product_template.py`

Three non-stored computed fields; the two cost-derived ones carry the purchasing group. One method.

```python
catalog_price_incl_tax = fields.Monetary(
    compute='_compute_catalog_price_incl_tax', currency_field='currency_id')
catalog_cost_incl_tax = fields.Monetary(
    compute='_compute_catalog_cost_incl_tax', currency_field='currency_id',
    groups='purchase.group_purchase_user')
catalog_margin = fields.Monetary(
    compute='_compute_catalog_margin', currency_field='currency_id',
    groups='purchase.group_purchase_user')

@api.depends('list_price', 'taxes_id')
@api.depends_context('company')
def _compute_catalog_price_incl_tax(self):
    for tmpl in self:
        taxes = tmpl.taxes_id._filter_taxes_by_company(self.env.company)
        tmpl.catalog_price_incl_tax = taxes.compute_all(
            tmpl.list_price, tmpl.currency_id, 1, product=tmpl,
        )['total_included']

def action_open_standard_form(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window', 'res_model': 'product.template',
        'res_id': self.id, 'view_mode': 'form',
        'views': [(self.env.ref('product.product_template_only_form_view').id, 'form')],
    }
```

`catalog_cost_incl_tax` is the same with `supplier_taxes_id`/`standard_price`; `catalog_margin` is
`list_price - standard_price`.

### 4.6 SCSS: grid, card, pastels

Variables have no `bs-` prefix (R19). The grid rule targets the renderer inside the view root and beats `d-flex`.

```scss
.o_serichai_product_catalog_kanban {
    .o_kanban_record:nth-child(5n + 1) .o_serichai_product_catalog_card_img {
        background: var(--primary-bg-subtle);
    }
    .o_kanban_record:nth-child(5n + 2) .o_serichai_product_catalog_card_img {
        background: var(--success-bg-subtle);
    }
    // 5n+3 --info-bg-subtle, 5n (5th) --warning-bg-subtle
    .o_kanban_record:nth-child(5n + 4) .o_serichai_product_catalog_card_img {
        background: color-mix(in srgb, var(--pink) 15%, var(--body-bg));
    }
    .o_kanban_renderer.o_kanban_ungrouped {
        display: grid !important;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .75rem;
        @media (max-width: 991.98px) { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        @media (max-width: 767.98px) { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        @media (max-width: 575.98px) { grid-template-columns: minmax(0, 1fr); }
    }
}
.o_serichai_product_catalog_kanban
.o_kanban_record.o_serichai_product_catalog_card:not(.o_kanban_ghost) {
    border: 1px solid rgba(var(--primary-rgb), .35);
    border-radius: 1rem;
    background: var(--white);
    &:hover { transform: translateY(-2px); box-shadow: 0 .5rem 1rem rgba(var(--body-color-rgb), .15); }
    &.o_record_selected, &:focus-visible { border-color: var(--primary); box-shadow: 0 0 0 2px var(--primary); }
    @media (prefers-reduced-motion: reduce) { transition: none; &:hover { transform: none; } }
}
```

### 4.7 SCSS: form layout and technical table

```scss
.o_serichai_product_catalog_form {
    .o_form_sheet { max-width: 1400px; }
    .o_serichai_product_catalog_layout {
        display: grid;
        grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
        gap: .5rem 1.5rem;
    }
    .o_serichai_product_catalog_side { position: sticky; top: 0; }
    .o_serichai_product_catalog_hero_img {
        height: 300px; background: rgba(var(--primary-rgb), .1);
    }
    .o_serichai_product_catalog_tech {
        th, td {
            padding: .6rem .5rem; vertical-align: middle; border: 0;
            border-bottom: 1px solid var(--border-color);
        }
        th { width: 10rem; color: var(--secondary-color); font-weight: 500; }
    }
}
@media (max-width: 899.98px) {   // sidebar stacks above the tabs
    .o_serichai_product_catalog_form .o_serichai_product_catalog_layout { grid-template-columns: minmax(0, 1fr); }
    .o_serichai_product_catalog_form .o_serichai_product_catalog_side { position: static; }
}
```

### 4.8 SCSS: pills

Tax pills are `many2many_tags` restyled. Attribute lines were built and then dropped (not displayed; no SCSS for them).

```scss
.o_field_many2many_tags .badge {
    border-radius: 50rem;
    background: rgba(var(--primary-rgb), .12) !important;
    color: var(--primary-text-emphasis) !important;
}
```

### 4.9 `i18n/th.po`

Literal strings only (view `string=`, text nodes, menu and action names); new items such as the filters and tab labels
have Thai entries.

## 5. Theme approach

Only CSS variables (no `bs-` prefix) and `color-mix()`; no hex/rgb/hsl literals, no `.text-primary` (MuK maps it to the
brand color); `$o-community-color` is overridden by MuK so it is not used. MuK colors reach `--primary*`, so a Settings
color change recolors the catalog in light and dark. Sale/Purchase pills use `text-bg-success` / `text-bg-info`.

## 6. Requirement groups to key files

| Requirement group | Key files |
|-------------------|-----------|
| Browse and search (US1, FR-004..007) | 4.1, 4.2, 4.4 |
| Product page, Specification, Technical Data (US2, FR-008..016) | 4.3 |
| Cost confidentiality (US3, FR-011/012) | 4.3 (groups), 4.5 |
| Standard form shortcut (FR-015) | 4.3 header, 4.5 |
| Theme and responsive (US5, FR-018..021) | 4.6-4.8 |
| Richer interface (US6, FR-023..034, amended: no toolbar) | 4.2, 4.3, 4.5, 4.6, 4.7 |

## 7. Access and security approach

- Read: `access_product_template_user` plus company rule; the catalog is browse-only (`create/delete/duplicate="0"`).
- Write: `description` and `image_1920` only through the existing manager ACL; the editable nodes exist only for
  `product.group_product_manager`, the readonly copy only for the others.
- Cost: Purchase page, `catalog_margin`, `catalog_cost_incl_tax` removed from the arch for non-purchasing users; `read`
  of the two fields raises `AccessError`. No `sudo()`.
- Residual (R6, unchanged): core lets internal users read `standard_price`/supplierinfo by RPC.

## 8. Test approach

Python `TransactionCase`, `@tagged('post_install', '-at_install')`, 24 tests; users: plain, purchase, manager.
No hoot, no tour. Key examples:

```python
def test_manager_can_update_photo_plain_user_cannot(self):
    photo = image_to_base64(Image.new('RGB', (4, 4), 'red'), 'PNG')
    self.product.with_user(self.manager_user).write({'image_1920': photo})
    with self.assertRaises(AccessError):
        self.product.with_user(self.plain_user).write({'image_1920': photo})

def test_cost_fields_denied_for_plain_user(self):
    product = self.product.with_user(self.plain_user)
    for name in ('catalog_margin', 'catalog_cost_incl_tax'):
        with self.assertRaises(AccessError, msg=name):
            product.read([name])

def test_scss_has_no_hardcoded_colors(self):
    ...
    self.assertFalse(re.findall(r'#[0-9a-fA-F]{3,8}\b', text))
    self.assertNotIn('.text-primary', text)
    self.assertNotIn('--bs-', text)
```

Specs must assert:
- Search term matches name, reference and barcode, case-insensitive; archived products are excluded.
- Form arch per role: photo and description editable only for managers; Purchase page and cost nodes only for purchasing users.
- Computed values for a taxed product: margin 50.0, cost incl. tax 107.0, price incl. tax 160.5; no-tax product returns list price.
- Kanban/list arch never contain `standard_price`, `seller_ids`, margin or cost fields; list has `export_xlsx="0"`.
- Own views are primary and the standard product views and action are untouched; non-managers have no editable field.
- SCSS lint: no hex, `rgb(`, `hsl(`, `--bs-`, `.text-primary`.
- Opt-in `CATALOG_PERF=1`: 5,000 products, category change and searches < 1 s server side (measured 0.013-0.016 s).

Not covered by any automated test (manual, quickstart): grid columns, pastels, hover, form layout, photo upload UI,
responsive widths, theme recolor, dark mode.

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Core kanban CSS (`d-flex !important`, `:not(.o_kanban_ghost)` selector) changes in a later Odoo 19 build | Selectors documented in R21; manual grid check after upgrades |
| Wrong variable name silently drops a declaration | Lint rejects `--bs-`; check borders/accents visually |
| Pastels cycle by position, so a product changes color after search/paging | Accepted, decorative (R22) |
| `edit="true"` on the form root cannot be restricted by group | All non-manager fields readonly; test asserts no editable field |
| Core exposes cost/supplier data over RPC to internal users | Unchanged residual (R6), not worsened |
| Visual items unverified headlessly | Manual checklist in quickstart; sign-off still pending |

## 10. Open questions for the architect

1. Resolved 2026-11-18: attribute lines are NOT displayed (the owner chose to leave them out); the view, SCSS, spec and
   tasks agree.
2. Resolved 2026-11-18: `spec.md` and `tasks.md` adopted the amended FR-015 scope (Specification and photo) and the dropped
   toolbar items (category dropdown with counts, product counter, selected-card marker).
3. Visual sign-off (SC-007, SC-009, SC-012) needs a human browser pass; no headless Chrome is available.
