# Feature Specification: Product Catalog

**Feature Branch**: `012-product-catalog`

**Created**: 2026-11-17

**Status**: Implemented (browser verification pending)

**Updated**: 2026-11-18 - aligned with what was delivered: the interface uses the application's standard search bar, filters, view switcher and pager instead of a custom toolbar; product page follows the newer mock-up (two columns); product managers can edit the product photo as well as the Specification; search, filters, group-bys and default filters specified. Changed items are marked **[Amended]**, removed ones **[Dropped: reason]**.

**Input**: User description: "Build the Product Catalog described in the lean plan, with a better design, following the visual mock-up for cosmetics, but using the colors of the company's web theme."

**Amendment input (2026-11-17)**: "Make the catalog look better, like the product catalog mock-up: the current screens feel plain; build a richer interface, still in the company theme colors."

**Amendment input (2026-11-18)**: Keep the interface as simple as possible (reuse the application's standard search, filter and paging controls), follow the newer mock-up for the product page, let product managers also change the product photo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and find products as a visual catalog (Priority: P1) **[Amended]**

Any internal employee opens a new "Catalog" entry in the main menu and sees products as attractive cards: product picture, name, internal reference, sales price, and small badges showing whether the product can be sold and/or purchased. By default the catalog shows goods that can be sold. They can switch to a compact list (picture, name, reference, category, price), search by name, internal reference or barcode in one search box, and narrow or group the results with the standard filters (product type, category, tags, can be sold, can be purchased, favorites). The standard pager shows which products of how many are displayed.

**Why this priority**: Finding a product quickly is the core reason for the catalog; it is useful on its own even before any detail page exists.

**Independent Test**: Open the Catalog as a plain internal user, search for a product by its name, then by its reference, then by its barcode, filter by a category, and switch between cards and list.

**Acceptance Scenarios**:

1. **Given** products exist, **When** an internal user opens Catalog, **Then** goods that can be sold appear as cards showing picture, name, reference, price and Sale/Purchase badges.
2. **Given** the card view, **When** the user switches to the list view, **Then** the same products appear as rows with picture, name, reference, category and price, and the current search and filters stay applied.
3. **Given** a product named "Chair", reference "CH-01", barcode "885000111", **When** the user types any one of these three values (or part of the name/reference) in the search box, **Then** that product is listed.
4. **Given** several categories, **When** the user searches by category (or groups by category), **Then** only products of that category (and its sub-categories) are listed, or the results are grouped by category, and the pager shows the matching number.
5. **Given** a search that matches nothing, **When** results are shown, **Then** the user sees a clear "no products found" message instead of an empty screen.
6. **Given** a product without a picture, **When** it is shown, **Then** a neutral placeholder is shown so cards stay aligned.
7. **Given** the default filters, **When** the user removes them, **Then** services, combos and products that cannot be sold also become searchable, but archived products never appear.

---

### User Story 2 - Open a product on a full-screen detail page (Priority: P1) **[Amended]**

From a card or a list row, the user clicks a product and it opens full screen on a two-column page: on the left a fixed side block with the picture, name, "reference - category" line, large price and the badges "Can be Sold" / "Can be Purchased"; on the right, tabs for Specification (shown first), Sales and Purchase, and a technical data section (barcode, unit of measure, weight, volume). Going back returns to the catalog with the same search, filters and view the user had before.

**Why this priority**: Reading a product's specification is the second half of the feature's purpose; together with Story 1 it forms the MVP.

**Independent Test**: Search for a product, open it, read all tabs, go back, and confirm the previous search and view are still applied.

**Acceptance Scenarios**:

1. **Given** the catalog results, **When** the user clicks a product, **Then** its page opens full screen with the Specification tab shown first.
2. **Given** the detail page, **When** the user opens the Sales tab, **Then** they see sales price, price including tax, applicable sales taxes, and the sales description.
3. **Given** the detail page, **When** the user returns via the breadcrumb or the browser Back, **Then** the catalog shows the same search text, filters and card/list choice as before.
4. **Given** a product with a rich specification (colored text, lists, tables, links, images), **When** it is displayed, **Then** the formatting is preserved and tables are clearly bordered and readable.
5. **Given** a product with no specification yet, **When** the Specification tab is shown, **Then** a friendly empty message is displayed.
6. **Given** the user needs to change data other than the specification and photo, **When** they use the "Open in standard product form" shortcut, **Then** the regular product screen for that product opens.

---

### User Story 3 - Maintain the specification and the product photo (Priority: P2) **[Amended]**

Product managers (employees who can already edit products) can edit a product's Specification directly on the detail page using a rich-text editor (colors, lists, tables, links), and can upload, replace or delete the product photo from the same page, then save or discard. Everyone else sees both read-only.

**Why this priority**: Keeps specifications and pictures current at the place they are read, but the catalog is valuable for reading even without it.

**Independent Test**: As a product manager edit and save a specification and replace the photo, then see both afterwards; as a plain internal user confirm neither can be changed.

**Acceptance Scenarios**:

1. **Given** a product manager, **When** they edit the specification and save, **Then** the new content is shown on the page and in the standard product screen.
2. **Given** a product manager, **When** they discard changes, **Then** the previous specification and photo are kept.
3. **Given** a product manager, **When** they upload or replace the photo and save, **Then** the new photo appears on the page, on the catalog card and list thumbnail, and in the standard product screen; **When** they delete it, **Then** the placeholder is shown.
4. **Given** a plain internal user, **When** they view a product, **Then** the specification and the photo cannot be edited, and no other product data on the page is editable by anyone.
5. **Given** a plain internal user, **When** they attempt to change the specification or the photo by any means, **Then** the change is refused.

---

### User Story 4 - Cost and supplier information for purchasing staff only (Priority: P2) **[Amended]**

Users with purchasing rights see an additional Purchase tab with cost, cost including tax, the product's unit of measure, purchase taxes, supplier price list (supplier, minimum quantity, price, lead time) and purchase description; they also see the margin on the Sales tab. Other users do not see the tab, the margin, or any cost information at all.

**Why this priority**: Protects confidential cost and supplier terms while still serving buyers.

**Independent Test**: Compare the same product page as a purchasing user and as a plain internal user.

**Acceptance Scenarios**:

1. **Given** a purchasing user, **When** they open a product, **Then** a Purchase tab shows cost, cost including tax, unit of measure, purchase taxes, supplier price list and purchase description, and the Sales tab also shows the margin.
2. **Given** a plain internal user, **When** they open the same product, **Then** no Purchase tab, no margin, no cost and no supplier price is visible anywhere in the catalog (cards, list or detail).

---

### User Story 5 - Polished look that follows the company theme (Priority: P2)

The catalog looks polished and modern. The detailed layout is defined in User Story 6 and the requirements FR-026 to FR-033 and FR-040; this story covers the theme-driven colors and responsiveness. All accent colors (menu highlight, price text, badges, selected tab, callout accents, table headers) come from the company web theme, so changing the theme colors changes the catalog's appearance with no further work.

**Why this priority**: The user explicitly asked for a better design in the theme's colors; it does not change what data is available.

**Independent Test**: View the catalog with the current theme, change the theme's main color, reload, and confirm all accents change; compare layout with the mock.

**Acceptance Scenarios**:

1. **Given** the theme's current colors, **When** the catalog is displayed, **Then** accents are in the theme palette and no color from the mock-up (such as its purple) appears unless the theme itself uses it.
2. **Given** the theme's main color is changed by an administrator, **When** the catalog is reloaded, **Then** its accents show the new color.
3. **Given** the detail page, **When** compared to the mock, **Then** every element listed in FR-030 to FR-033 is present (checked item by item in the sign-off review, SC-007).
4. **Given** a narrow screen (width 768 px or 360 px), **When** the catalog or a product page is opened, **Then** content reflows with no horizontal scrollbar and no overlapping elements.
5. **Given** the theme supports a dark variant, **When** it is active, **Then** all catalog text remains readable and accents follow the dark palette.

---

### User Story 6 - Richer catalog interface matching the mock (Priority: P2) **[Amended]**

Users find plain screens unattractive. They want a richer, cohesive look like the visual mock-up while keeping the familiar standard controls: the application's usual search bar with filters, view switcher and pager at the top; rounded cards with soft pastel picture areas in a four-per-row grid; and a product page with a side block, key-figure tiles per tab, tax pills and clean tables. The same data, access rights and navigation apply as before; only the presentation changes, and all accents still come from the company theme.

**Why this priority**: The user asked for a better look; the catalog works without it, so it follows the P1 stories.

**Independent Test**: Open the catalog and a product page as a purchasing user and as a plain internal user, and check each element against the newer mock-up and against FR-023 to FR-034 and FR-040.

**Acceptance Scenarios**:

1. **Given** the catalog is opened on a wide screen, **When** cards are shown, **Then** they appear four per row, each with rounded corners, a tinted picture area and a themed border; on narrower screens the row holds three, two, then one card.
2. **Given** the card view, **When** the user hovers over a card, **Then** it visibly lifts and gains a soft shadow; **When** a card has keyboard focus, **Then** a themed focus ring is shown.
3. **Given** consecutive cards, **When** they are shown, **Then** their picture areas alternate through a set of soft pastel colors (lavender, mint, light blue, pink, cream), which adapt to the theme and its dark variant.
4. **Given** a product without a picture, **When** it appears as a card or list row, **Then** a placeholder fills the tinted picture area or thumbnail.
5. **Given** the list view, **When** it is shown, **Then** each row has a thumbnail, name, reference, category and price, and the row under the pointer is tinted.
6. **Given** a purchasing user on the Purchase tab, **When** the product has supplier prices, **Then** key-figure tiles show cost, cost including tax and the product's own unit of measure, and the supplier table shows right-aligned numbers and lead time in days.
7. **Given** a plain internal user, **When** they use the interface anywhere (cards, list, page, exports), **Then** no cost, margin or supplier information appears.
8. **Given** a product with technical data, **When** the page is shown, **Then** it appears as a label/value table with a separator line between rows and label and value aligned on the same line.
9. **Given** the user opens a product and goes back, **When** the catalog reappears, **Then** search, filters and card/list choice are as before.
10. **Given** a screen narrower than the page's two-column breakpoint (about 900 px), **When** the product page opens, **Then** the side block is shown above the tabs instead of beside them.

---

### Edge Cases

- Product name, reference or specification is very long: card text is shortened with an ellipsis (full text on the detail page); the specification wraps without breaking the layout.
- Product has no category, no barcode, no reference or no price: the missing item is simply left out or shown as empty, never as an error; with no category the page shows the reference alone in the "reference - category" line.
- Archived products are never shown, whatever filters the user chooses.
- Product that is neither sellable nor purchasable: no Sale/Purchase badge is shown for it.
- A product the user may not see (restricted by existing access) is never listed.
- Margin and cost including tax are shown only to purchasing users; for them, a tile whose data is unavailable is omitted.
- A specification containing wide tables or large images stays within the page width.
- A user who loses edit rights while the page is open cannot save changes to the specification or photo; they are told the save is not permitted.
- Thousands of products: browsing stays paged and responsive.
- Product with no applicable tax or no supplier price: the tax pills or vendor table are replaced by a short "none" message rather than left blank.
- Product attributes (for example size) are not displayed on the product page; an earlier idea of showing them as name plus value pills was dropped on 2026-11-18 at the owner's request.
- The user removes both default filters: all non-archived products (goods, services, combos, sellable or not) become available.
- Photo removed by a product manager: the placeholder is shown everywhere the photo appeared.
- Pastel colors follow card position, not the product: the same product may change color when the results change.
- **[Dropped: custom counter]** The singular/plural "N products" counter no longer exists; the standard pager shows the range and total, and the empty message applies for zero results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a "Catalog" entry in the main menu, available to every internal user.
- **FR-002**: The catalog MUST list products as cards showing picture, name, internal reference, sales price, and badges for "can be sold" and "can be purchased".
- **FR-003**: Users MUST be able to switch between a card view and a list view (picture, name, reference, category, price) using the application's standard view switcher, while keeping their current search and filters.
- **FR-004**: The system MUST provide a single search box that finds products by name, internal reference, variant reference or barcode, matching partial text and ignoring letter case.
- **FR-005 [Amended]**: Users MUST be able to search by product category (including its sub-categories) and group the catalog by category, through the standard search bar.
- **FR-006 [Amended]**: The catalog MUST let users page through results with the application's standard pager, which shows the range displayed and the total number of matching products.
- **FR-007**: Clicking a product MUST open it full screen, and returning MUST restore the previous search, filters and view.
- **FR-008 [Amended]**: The product page MUST show a large picture, name, reference, category, sell/purchase badges and the sales price prominently in a side block, with the margin shown only to purchasing users.
- **FR-009**: The product page MUST organize content in tabs: Specification (shown first), Sales, and Purchase (purchasing users only), together with a technical data section (barcode, unit of measure, weight, volume).
- **FR-010**: The Sales tab MUST show sales price, price including tax, sales taxes and sales description.
- **FR-011 [Amended]**: The Purchase tab MUST show cost, cost including tax, the product's own unit of measure, purchase taxes, supplier price list (supplier, minimum quantity, price, lead time) and purchase description, and MUST be visible only to users with purchasing rights.
- **FR-012 [Amended]**: Cost, cost including tax, margin and supplier information MUST NOT be visible to, or obtainable through the catalog by, users without purchasing rights, including cards, list and exports of the catalog view.
- **FR-013**: The Specification MUST support rich formatting (colors, headings, lists, tables, links, images), displayed faithfully, with tables clearly bordered.
- **FR-014 [Amended]**: Users who can already edit products (product managers) MUST be able to edit and save the Specification and upload, replace or delete the product photo from the product page; all other users MUST see both read-only, and the refusal MUST be enforced by the system, not only by hiding controls.
- **FR-015 [Amended]**: Apart from the Specification and the product photo, product data MUST NOT be editable from the catalog; a shortcut MUST open the regular product screen for deeper changes.
- **FR-016 [Amended]**: The specification and photo edited in the catalog MUST be the same ones shown in the regular product screen (one source, no copy).
- **FR-017**: The catalog MUST NOT alter the existing product, sales, purchase or inventory screens or their menus.
- **FR-018**: All accent colors, highlights, borders and badges (menu highlight, price text, badges, active tab, callout accents, table headers, hover and focus tints, pastel picture areas) MUST derive from the web theme's palette; no color from the mock-up (such as its purple) may be fixed, so that theme color changes apply automatically (including the dark variant if the theme supports it).
- **FR-019**: Cards, key-figure tiles and tabs MUST follow the mock's structure (as detailed in FR-026 to FR-033) and give visible feedback on hover and on focus or active state.
- **FR-020**: Empty states MUST show a friendly message or placeholder: "no products found" for empty results, "no specification yet" on the Specification tab, a placeholder image for a missing picture, and "none" messages for missing taxes or supplier prices.
- **FR-021**: The catalog list and product pages MUST be usable at widths from 360 px to desktop without a horizontal scrollbar or overlapping elements.
- **FR-022**: All labels MUST be available in English and Thai, including the new search and filter labels.
- **FR-023 [Amended]**: The catalog MUST use the application's standard control area at the top: the standard search bar with filter and group-by facets (FR-035 to FR-038), the standard card/list view switcher (FR-003) and the standard pager (FR-006); no separate custom toolbar is provided.
- **FR-024 [Amended]**: Changing the search, a filter, a grouping or the view MUST update the results without leaving the page.
- **FR-025 [Dropped: custom "N products" counter and category dropdown with counts]**: replaced by the standard pager (FR-006) and the category search and grouping (FR-005); the user decided to reuse standard controls.
- **FR-026 [Amended]**: Each card MUST show: a picture area tinted with a soft pastel color (with a placeholder when there is no picture), the name shortened with an ellipsis when too long, the internal reference, the sales price in the theme accent color, and "Sale" and "Purchase" pill badges only where applicable. Pastel colors alternate through five tints (lavender, mint, light blue, pink, cream) by card position.
- **FR-027 [Amended]**: Cards MUST have rounded corners and a themed border, MUST lift slightly with a soft shadow on hover, and MUST show a themed ring when selected by keyboard focus. (The earlier "last opened card" marker is not provided.)
- **FR-028**: Each list row MUST show a picture thumbnail (placeholder if none), name, reference, category and price, and MUST be tinted when hovered.
- **FR-029 [Amended]**: Clicking a card or row MUST open the full-screen product page (FR-007); the search, filters and card/list state MUST be restored when the user returns by breadcrumb or browser Back.
- **FR-030 [Amended]**: The product page MUST be laid out in two columns on screens of about 900 px or wider: a side block that stays in view while scrolling, holding the picture (in a tinted box), the name, a "reference - category" line, the large price and the "Can be Sold" / "Can be Purchased" badges; and a main area with the tabs. On narrower screens the side block MUST appear above the tabs and no longer stay in view.
- **FR-031 [Amended]**: Each tab MUST open with key-figure tiles: Sales shows sales price, price including tax and, for purchasing users only, margin; Purchase, for purchasing users only, shows cost, cost including tax and the product's own unit of measure.
- **FR-032**: Sales and purchase taxes MUST appear as pills; the supplier price table MUST show supplier, minimum quantity and price as right-aligned numbers, and lead time in days.
- **FR-033 [Amended]**: Technical data MUST appear as a label/value table with a separator line between rows and label and value vertically aligned, listing barcode, unit of measure, weight and volume (a row is left out when it has no value; attributes are not displayed, see edge cases). The Specification tab MUST be first and active by default, with a friendly message when empty, bordered tables and highlighted callouts inside the specification; the active tab MUST be clearly marked in the theme accent color.
- **FR-034 [Amended]**: The richer interface MUST NOT change data or access: cost, margin and supplier data stay hidden from users without purchasing rights in cards, list, page and exports (FR-012); the Specification and photo stay editable only by product managers, enforced by the system (FR-014); and the existing menus and screens stay unchanged (FR-017).
- **FR-035**: The search box MUST offer these search fields: product (name, internal reference, variant reference and barcode in one), category, and tags.
- **FR-036**: The catalog MUST offer these filters: product type (Goods, Services, Combo), Favorites, Can be Sold, and Can be Purchased. Filters of different kinds combine with AND.
- **FR-037**: The catalog MUST offer grouping by product type and by category.
- **FR-038**: When the catalog is opened, the filters "Goods" and "Can be Sold" MUST be applied by default; the user MUST be able to remove either of them.
- **FR-039**: Archived products MUST NEVER be listed in the catalog, and no filter to show them is provided.
- **FR-040**: On screens of about 992 px or wider, the card view MUST show four cards per row; between 768 and 991 px three; between 576 and 767 px two; below 576 px one.

### Key Entities

- **Product**: An existing sellable/purchasable item with name, internal reference, barcode, category, tags, picture, prices, taxes, unit of measure, weight, volume and descriptions. The catalog reads existing products; it creates none.
- **Specification**: The rich-text description of a product, already stored with the product; edited from the catalog or the regular product screen.
- **Product Photo**: The product's picture, shown on cards, list rows and the page; changeable by product managers.
- **Product Category**: Grouping used for searching and grouping.
- **Supplier Price**: A supplier's price, minimum quantity and lead time for a product; visible to purchasing users only.
- **Catalog Viewer / Product Manager / Purchasing User**: Roles, respectively any internal user, anyone already able to edit products, and anyone with purchasing rights.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user finds a known product by name, reference or barcode and sees its specification in under 30 seconds, without training.
- **SC-002**: 100% of tested searches by the exact name, reference or barcode of an existing product return that product.
- **SC-003**: After opening a product and going back, the previous search, filters and view are restored in 100% of tested cases.
- **SC-004**: Users without purchasing rights see zero cost, margin or supplier values across all catalog screens in access testing.
- **SC-005 [Amended]**: Users without product-edit rights succeed in changing a specification or a product photo in 0% of attempts; product managers succeed in 100%.
- **SC-006**: After changing the theme's main color, 100% of catalog accents (badges, price text, active tab, callouts, pastel areas, focus and hover states) show the new color with no manual change in the catalog.
- **SC-007 [Amended]**: In a review against the newer mock-up using the checklist of FR-026 to FR-033 and FR-040 (cards, list, grid, key figures, tabs, badges, pills, tables, two-column page), 100% of listed elements are present and stakeholders sign off the look.
- **SC-008**: With 5,000 products, results of a search appear within 2 seconds and the first page of cards within 3 seconds.
- **SC-009 [Amended]**: In a comparison of the product page and catalog against the newer mock-up, a reviewer finds 100% of the elements of FR-026 to FR-033 and FR-040 present, and no mock-only element (custom editor, side panel, category dropdown with counts) required.
- **SC-010 [Amended]**: Changing the search, a filter, a grouping or the view updates the results in under 1 second with 5,000 products.
- **SC-011 [Amended]**: In access testing, users without purchasing rights see zero cost, margin or supplier values on cards, list, page and exports, and users without product-edit rights succeed in changing a specification or photo in 0% of attempts.
- **SC-012**: At widths of 360 px, 768 px and 1280 px, 100% of tested catalog and product pages show no horizontal scrollbar and no overlapping elements.

## Assumptions

- All non-archived products of the existing product database are in scope; no separate catalog data is created or imported.
- "Internal users" means employees with a regular login; portal/customer and public access are out of scope.
- The existing rights decide who can edit products and who counts as a purchasing user; no new role is created.
- Specification is the existing product description and photo is the existing product picture; no migration is needed.
- Margin and cost including tax are shown to purchasing users when the data exists in the company's setup; otherwise the tile is omitted.
- Price including tax uses the company's existing tax configuration.
- The mock's data-entry features (its custom editor, side-by-side panel, category dropdown with counts, custom counter, "last opened" marker) are not reproduced; standard controls and the full-screen page replace them.
- Product variants are not shown as separate cards, and their attributes are not displayed on the product page.
- The purchase tile "unit of measure" is the product's own unit; the supplier's unit is not shown separately.
- The company web theme is the MuK web theme; "follow the theme" includes its color customization.
- Thai is the second language, per project convention.
- Pastel picture-area colors are decorative, follow card position, and carry no meaning.
- The "N products" wording, tint, lift, shadow and pill are visual styles judged in the sign-off review, with all colors taken from the theme.
- Out of scope: cart or ordering, exporting a PDF catalog, editing anything except the specification and photo, and public (website) catalog.

## Implementation status

| User story | Status |
|---|---|
| US1 Browse and find products | Done (search, filters, grouping, default filters and automated checks passed); card/list look Done-pending-browser-check |
| US2 Full-screen product page | Done-pending-browser-check |
| US3 Maintain specification and photo | Done (access rules automatically tested); photo upload screen Done-pending-browser-check |
| US4 Purchasing-only information | Done (access rules automatically tested) |
| US5 Theme-following look | Done-pending-browser-check (theme recoloring and dark variant not yet viewed) |
| US6 Richer interface | Done-pending-browser-check |

Automated checks: 24 tests passed. With 5,000 products, searches and category changes completed in about 0.02 seconds on the server (supports SC-010 and SC-008; display time in the browser not measured).

## Known gaps

- Nothing visual has been checked in a browser yet: four-per-row grid, pastel colors, hover shadow, product page layout, photo upload, widths 360/768/1280 (SC-012), mock sign-off (SC-007, SC-009), theme recoloring (SC-006) and dark variant.
- Cost and supplier data is still readable by internal users through technical access outside the catalog screens; the catalog itself hides it (FR-012 is met for catalog screens only).
- Pastel colors depend on card position, not on the product or its category.
- The product count display is the application's standard pager, not a custom counter (accepted by decision, FR-025 dropped).
