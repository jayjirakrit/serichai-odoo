# Feature Specification: Inventory Barcode Scanning (serichai_inventory_barcode)

**Feature Branch**: `003-inventory-barcode-scan`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "create spec inside serichai-odoo/specs for module serichai-odoo/serichai_inventory_barcode for spec documentation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scan to add a line (Priority: P1)

A warehouse operator processing a transfer (receipt, delivery, or internal transfer) needs to add a product to it quickly. Instead of searching for the product and typing a quantity by hand, the operator scans the product's barcode and a line for that product is created automatically.

**Why this priority**: This is the core value of the feature — replacing manual line entry with a scan. Without it, the module delivers nothing.

**Independent Test**: Open an editable transfer with no existing line for product X, scan product X's barcode, and confirm a new operation line for X appears with quantity 1 and is marked as picked.

**Acceptance Scenarios**:

1. **Given** an editable transfer with no line for product X, **When** the operator scans product X's barcode, **Then** a new operation line for X is created with quantity 1 and marked as picked.
2. **Given** the transfer has not yet been confirmed, **When** a product is scanned, **Then** the underlying operation is created and confirmed as needed so the new line is usable without further manual steps.

---

### User Story 2 - Scan to increment an existing line (Priority: P1)

An operator has already added a line for a product (via a previous scan or manual entry) and wants to record additional units of that same product by scanning again, rather than editing the quantity field by hand.

**Why this priority**: Equally core to the workflow — most real picking/receiving involves multiple units of the same product, so repeat-scan-to-increment is used as often as the initial add.

**Independent Test**: Scan product X's barcode twice on the same transfer and confirm the result is a single line with quantity 2, not two separate lines.

**Acceptance Scenarios**:

1. **Given** a transfer already has a picked line for product X with quantity 1, **When** the operator scans X's barcode again, **Then** the quantity on that same line increases to 2.
2. **Given** several scans of the same product happen in sequence, **When** each scan is processed, **Then** the quantity increases by exactly 1 per scan and no duplicate lines are created for that product on that transfer.

---

### User Story 3 - Clear feedback on an unrecognized barcode (Priority: P2)

An operator scans a barcode that does not match any product — for example a mis-scan, a non-product barcode, or the wrong item — and needs to know immediately that nothing happened, rather than silently getting no result.

**Why this priority**: Protects trust in the tool and prevents missed lines going unnoticed, but the flow is only reached after the primary add/increment behavior (US1/US2) already works.

**Independent Test**: Scan a barcode with no matching product and confirm an error notification appears while the transfer's lines remain unchanged.

**Acceptance Scenarios**:

1. **Given** a scanned barcode matches no product, **When** the scan is processed, **Then** the operator sees an error notification stating no product was found for that barcode, and no line is added or changed.

---

### User Story 4 - Guardrail for lot/serial tracked products (Priority: P2)

Some products require lot or serial number tracking, which cannot be safely inferred from a barcode scan alone. When an operator scans such a product, the system must stop them from creating an untraceable line and point them to manual entry instead.

**Why this priority**: Prevents data-integrity problems (inventory moved without a lot/serial reference). Secondary to the main add/increment flow since it only applies to the subset of products under lot/serial tracking, but mandatory wherever those products exist.

**Independent Test**: Scan a barcode for a lot/serial tracked product and confirm the system blocks the action with an explanatory message, without adding or incrementing any line.

**Acceptance Scenarios**:

1. **Given** the scanned product is tracked by lot or serial number, **When** the scan is processed, **Then** the operator sees a message explaining that scan-to-add is not supported for tracked products and that the line must be added manually to set the lot/serial, and no line is added or incremented.

---

### Edge Cases

- What happens when a transfer is already done or cancelled? Scanning MUST NOT be able to add or change lines on a transfer in a closed state.
- What happens when the same physical scan is registered twice in rapid succession (duplicate scan events)? Each distinct scan event should net exactly one increment; the system should not double-count a single physical scan.
- What happens when a scanned barcode is associated with more than one product? Barcode-to-product lookup assumes a unique match; ambiguous matches are out of scope for this feature.
- What happens when a line added by scanning is later removed manually and the same barcode is scanned again? A new line should be created, since no active line for that product remains.
- What happens when the operator has no barcode scanner connected? The scan-driven flow simply does not trigger; manual line entry remains available as the fallback at all times.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let an operator add a new operation line to an editable transfer by scanning a product's barcode.
- **FR-002**: A barcode scan that matches a product with no existing open line on the transfer MUST create a new line for that product with a quantity of 1, marked as picked.
- **FR-003**: A barcode scan that matches a product with an existing open (not done/cancelled) line on the transfer MUST increase that line's quantity by 1 rather than creating a duplicate line.
- **FR-004**: The system MUST use the transfer's default source and destination locations for lines created via scanning, without prompting the operator to choose a location.
- **FR-005**: A barcode scan that does not match any product MUST leave the transfer unchanged and MUST show the operator a visible error message identifying the unrecognized barcode.
- **FR-006**: A barcode scan that matches a product tracked by lot or serial number MUST be blocked from auto-creating or incrementing a line, and MUST show the operator a message directing them to add the line manually so they can set the lot/serial.
- **FR-007**: The system MUST NOT allow a barcode scan to add or modify lines on a transfer that is already done or cancelled.
- **FR-008**: After a successful scan, the operator MUST see confirmation of what was scanned (e.g., the product name) so they can verify the correct item was recognized.
- **FR-009**: The scan-to-add/increment capability MUST be available directly from the transfer's own screen, without requiring the operator to leave it or open a separate app.
- **FR-010**: Manual line entry MUST remain fully available at all times as an alternative to scanning (e.g., for tracked products or when no scanner is present).

### Key Entities

- **Transfer**: A warehouse operation (receipt, delivery, or internal transfer) that groups the operation lines an operator is picking, receiving, or moving.
- **Operation Line**: A single product entry on a transfer, with a quantity and a picked/not-picked status; scanning either creates one or increments its quantity.
- **Product**: The item being moved, identified for scanning purposes by its barcode; may or may not require lot/serial tracking.
- **Barcode**: The scannable identifier that resolves to exactly one product and drives the add-or-increment behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can add a new product line to a transfer with a single scan, without any manual search or typing.
- **SC-002**: An operator can record additional units of an already-added product using only repeated scans, with no manual quantity edits, for all untracked products.
- **SC-003**: 100% of scans for unrecognized barcodes produce a visible error message rather than a silent no-op.
- **SC-004**: 100% of scans against lot/serial-tracked products are blocked from auto-adding or incrementing a line.
- **SC-005**: Time to build out a transfer consisting entirely of untracked products is measurably reduced compared to entering every line manually, with no increase in incorrect-quantity errors.

## Assumptions

- The feature applies to any transfer type (receipts, deliveries, internal transfers), not just one specific type.
- Each product's barcode is unique (standard Odoo product-barcode assumption); duplicate/ambiguous barcodes are out of scope.
- Each scan represents exactly one unit in the product's default unit of measure; scanning a barcode that represents a bulk quantity (e.g., a case of 10) is out of scope.
- Operators already have a working barcode input device (physical scanner or scanner-emulating keyboard input); device setup/pairing is out of scope of this spec.
- Scanning is only meaningful while a transfer is in an editable state; once a transfer is done or cancelled, scanning has no effect.
