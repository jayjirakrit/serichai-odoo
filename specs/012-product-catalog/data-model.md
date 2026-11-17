# Data Model: Product Catalog

No new model, field, table, group, ACL or record rule. The addon reads `product.template` and writes only
`description` and `image_1920` (via the existing ACL, managers only).

## Fields used (all existing)

| Field | Model (module) | Use in catalog | Visible to |
|-------|----------------|----------------|-----------|
| `name`, `default_code`, `barcode`, `categ_id`, `product_tag_ids`, `is_favorite`, `type`, `image_512/128/1024`, `list_price`, `currency_id`, `sale_ok`, `purchase_ok` | `product.template` (product) | search, cards, list, hero | internal users |
| `description` (Html, translate) | product | Specification, same field as standard form (FR-016) | read: internal; write: `product.group_product_manager` (ACL `access_product_template_manager`) |
| `taxes_id` | account | Sales tab pills (price incl. tax is computed, below) | internal |
| `description_sale` | product | Sales tab | internal |
| `barcode`, `uom_id`, `weight`/`weight_uom_name`, `volume`/`volume_uom_name` | product | technical data (attributes are not displayed) | internal |
| `standard_price`, `supplier_taxes_id`, `seller_ids` (`partner_id`, `min_qty`, `price`, `delay`), `description_purchase` | product/account | Purchase tab | `purchase.group_purchase_user` (view `groups`) |

## Access model

| Action | Rule |
|--------|------|
| List/read products | `access_product_template_user` (base.group_user, read) + `product_comp_rule` (company) |
| Write `description` or `image_1920` | `access_product_template_manager` only; others get `AccessError` |
| See Purchase page / cost / supplier prices | arch is filtered server-side by `groups="purchase.group_purchase_user"` |
| Archived products | excluded by default `active` domain |

## State / transitions

None. Search/filter/view state is held by the web client's action breadcrumbs.

## Residual exposure (not changed by this feature)

Core declares `standard_price` with `groups="base.group_user"` and grants `product.supplierinfo` read to all internal
users, so an internal user can still read cost by direct RPC or the standard product screen. The catalog never
renders it for them. Tightening this would change core behaviour (FR-017): open question 1.

# Built state: computed fields and photo rights

No stored model, table, group, ACL or rule. Three non-stored computed Monetary fields on `product.template`
(`currency_field='currency_id'`; not searchable, not groupable; no schema change). Computes depend on the company
(`@api.depends_context('company')`) because taxes and `standard_price` are company-dependent.

| Field | Formula | Read | Write |
|-------|---------|------|-------|
| `catalog_price_incl_tax` | company taxes of `taxes_id`, `compute_all(list_price)['total_included']` | internal users | nobody (computed, no inverse) |
| `catalog_cost_incl_tax` | company taxes of `supplier_taxes_id`, `compute_all(standard_price)['total_included']` | `purchase.group_purchase_user` only: field `groups`; arch nodes stripped; `read` raises `AccessError` for others | nobody |
| `catalog_margin` | `list_price - standard_price` | `purchase.group_purchase_user` only (same mechanism) | nobody |

Payload: the form `web_read` requests only fields in the served arch. For plain users the cost nodes and the Purchase
page are removed server-side. Kanban and list specs never include cost, supplier or margin fields.

Photo: `image_1920` (preview `image_1024`) is written through the standard `product.template` write ACL.

| Who | Photo / Specification in the form | Server |
|-----|-----------------------------------|--------|
| `product.group_product_manager` | editable `image_1920` and `description` | write allowed (`access_product_template_manager`) |
| other internal users | readonly `image_1024` and readonly `description` copy | write raises `AccessError` (forged RPC) |

Residual exposure unchanged (R6): core still lets internal users read `standard_price` and supplierinfo directly.
The new fields are stricter than their source and add no read path. Client state (facets, view type) lives in the
action breadcrumbs, nothing is persisted.
