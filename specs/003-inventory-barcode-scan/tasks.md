---

description: "Task list for Inventory Barcode Scanning (serichai_inventory_barcode)"
---

# Tasks: Inventory Barcode Scanning (serichai_inventory_barcode)

**Input**: Design documents from `serichai-odoo/specs/003-inventory-barcode-scan/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/module-interface.md, quickstart.md (all present)

**Tests**: Included — `research.md` Decision 5 and `plan.md`'s Testing section explicitly call for a new `tests/test_barcode_scan.py` suite; this addon currently has zero automated coverage.

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent implementation and testing of each story. All test tasks land in the same file (`tests/test_barcode_scan.py`, per Decision 5 in research.md), so they are sequenced rather than marked `[P]` against each other.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4); tasks outside the four spec'd user stories (Setup, Foundational, the FR-007 guard, Polish) carry no story label
- File paths are relative to the repository working directory (`/home/odoo/serichai-odoo`)

## Path Conventions

Single existing Odoo addon, fixed/extended in place — no new addon, no new top-level directories (per plan.md's Structure Decision):

```text
serichai-odoo/serichai_inventory_barcode/
├── __manifest__.py
├── models/stock_picking.py
├── views/stock_picking_views.xml
├── static/src/js/barcode_scan_widget.js
└── tests/                      # NEW
    ├── __init__.py              # NEW
    └── test_barcode_scan.py     # NEW
```

---

## Phase 1: Setup

**Purpose**: Stand up the test package this addon currently lacks

- [X] T001 Create `serichai-odoo/serichai_inventory_barcode/tests/__init__.py` containing `from . import test_barcode_scan`, establishing the new `tests/` package for this addon

**Checkpoint**: Test package scaffold exists; ready for the Foundational base test class and the manifest fix

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the blocking bug that currently prevents all four user stories from working in the browser (research.md Decision 1), and stand up the shared test fixtures every story's test depends on

**⚠️ CRITICAL**: No user story test can be written until T003 lands; no user story is manually verifiable in the browser until T002 lands

- [X] T002 [P] Fix the broken asset path in `serichai-odoo/serichai_inventory_barcode/__manifest__.py`: change the `assets['web.assets_backend']` entry from `'serichai_inventory/static/src/js/barcode_scan_widget.js'` to `'serichai_inventory_barcode/static/src/js/barcode_scan_widget.js'` (research.md Decision 1 — the widget currently points at an unrelated, uninstalled addon and never loads)
- [X] T003 [P] Create the base `TransactionCase` test class and shared `setUp` fixtures in `serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py`: an untracked test product `P1` with barcode `B1`, a lot-tracked test product `P2` with barcode `B2`, and a test `stock.picking` in a non-`done`/`cancel` state (mirrors the style of `serichai-odoo/serichai_project_security/tests/test_access_restriction.py` per research.md Decision 5)

**Checkpoint**: Manifest fix in place (widget loads in browser) and shared test fixtures exist — user story implementation/testing can now begin

---

## Phase 3: User Story 1 - Scan to add a line (Priority: P1) 🎯 MVP

**Goal**: A scan of an untracked product with no existing open line on the transfer creates a new line at quantity 1, marked as picked (FR-001, FR-002, FR-004)

**Independent Test**: Open an editable transfer with no line for product X, scan product X's barcode, and confirm a new operation line for X appears with quantity 1 and is marked as picked

### Tests for User Story 1

- [X] T004 [US1] Add `test_scan_creates_new_line` to `serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py`: call `picking.action_scan_barcode('B1')` on a picking with no existing line for `P1`, assert exactly one `stock.move.line` is created for `P1` with `quantity == 1` and `picked is True`, using the picking's own `location_id`/`location_dest_id`, and assert the return value is `{'product_name': P1.display_name}` (contract #1 in `contracts/module-interface.md`)

### Implementation for User Story 1

No code change required — `action_scan_barcode`'s add-line logic in `serichai-odoo/serichai_inventory_barcode/models/stock_picking.py` already implements FR-001/002/004 correctly (research.md Decision 3); T002's manifest fix is what makes this story reachable from the browser.

**Checkpoint**: User Story 1 is fully testable independently (run T004 against T002+T003)

---

## Phase 4: User Story 2 - Scan to increment an existing line (Priority: P1)

**Goal**: A repeat scan of the same untracked product increments the existing open line's quantity instead of creating a duplicate (FR-003)

**Independent Test**: Scan product X's barcode twice on the same transfer and confirm the result is a single line with quantity 2, not two separate lines

### Tests for User Story 2

- [X] T005 [US2] Add `test_scan_increments_existing_line` to `serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py`: call `picking.action_scan_barcode('B1')` twice in sequence, assert the line count for `P1` is unchanged after the second call and that line's `quantity` increases to `2` (contract #2 in `contracts/module-interface.md`)

### Implementation for User Story 2

No code change required — the open-move lookup and increment branch in `action_scan_barcode` already implements FR-003 correctly (research.md Decision 3).

**Checkpoint**: User Stories 1 AND 2 both independently testable

---

## Phase 5: User Story 3 - Clear feedback on an unrecognized barcode (Priority: P2)

**Goal**: A scan of a barcode matching no product leaves the transfer unchanged and raises a visible error (FR-005)

**Independent Test**: Scan a barcode with no matching product and confirm an error notification appears while the transfer's lines remain unchanged

### Tests for User Story 3

- [X] T006 [US3] Add `test_scan_unrecognized_barcode_raises` to `serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py`: call `picking.action_scan_barcode('does-not-exist')`, assert it raises `UserError`, and assert no move or move line on the picking changed (contract #3 in `contracts/module-interface.md`)

### Implementation for User Story 3

No code change required — the `UserError` raised when `product.product.search` finds no match already implements FR-005 (research.md Decision 4); the widget's danger notification on this error is already wired client-side.

**Checkpoint**: User Stories 1–3 all independently testable

---

## Phase 6: User Story 4 - Guardrail for lot/serial tracked products (Priority: P2)

**Goal**: A scan of a lot/serial-tracked product is blocked from auto-creating or incrementing a line, with a message directing the operator to manual entry (FR-006)

**Independent Test**: Scan a barcode for a lot/serial tracked product and confirm the system blocks the action with an explanatory message, without adding or incrementing any line

### Tests for User Story 4

- [X] T007 [US4] Add `test_scan_tracked_product_blocked` to `serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py`: call `picking.action_scan_barcode('B2')` (the lot-tracked `P2`), assert it raises `UserError`, and assert no line for `P2` was created or incremented (contract #4 in `contracts/module-interface.md`)

### Implementation for User Story 4

No code change required — the `UserError` raised when `product.tracking != 'none'` already implements FR-006 (research.md Decision 4).

**Checkpoint**: All four spec'd user stories (US1–US4) independently functional and tested

---

## Phase 7: Closed-Transfer Guard (FR-007 — cross-cutting edge case, no dedicated user story)

**Goal**: Close the one requirement gap the current code doesn't yet enforce — scanning MUST NOT add or modify lines on a `done`/`cancel` transfer (Edge Cases section of spec.md; FR-007)

- [X] T008 Add a closed-transfer guard to `action_scan_barcode` in `serichai-odoo/serichai_inventory_barcode/models/stock_picking.py`: at the top of the method, before the product lookup, raise `UserError` if `self.state in ('done', 'cancel')` (research.md Decision 2)
- [X] T009 [P] Wrap the `<widget name="stock_picking_barcode_scanner"/>` tag in `serichai-odoo/serichai_inventory_barcode/views/stock_picking_views.xml` with the same `invisible="state in ('cancel', 'done')"` condition already applied to the sibling info banner (defense-in-depth view fix per research.md Decision 2; does not replace T008)
- [X] T010 Add `test_scan_blocked_on_closed_transfer` to `serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py`: set the test picking's `state` to `'done'` (and separately `'cancel'`), call `picking.action_scan_barcode('B1')`, assert it raises `UserError`, and assert no move or move line changed (contract #5 in `contracts/module-interface.md`) — depends on T008

**Checkpoint**: FR-007 enforced and covered by a passing test; all functional requirements (FR-001–FR-010) now satisfied

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify the whole feature end-to-end per quickstart.md

- [X] T011 Run the full automated suite: from `odoo/`, `python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db --test-enable --stop-after-init -u serichai_inventory_barcode`; confirm all five tests in `tests/test_barcode_scan.py` pass and the module upgrades with no errors (quickstart.md steps 1–2)
- [ ] T012 Perform the manual browser walkthrough in `serichai-odoo/specs/003-inventory-barcode-scan/quickstart.md` steps 3–10: confirm the `web.assets_backend` bundle loads `barcode_scan_widget.js` with no 404, then scan-to-add (US1), scan-to-increment (US2), unrecognized-barcode notification (US3), lot/serial block (US4), closed-transfer block (FR-007), and that manual line entry (FR-010) still works at every step

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 (tests package must exist before T003 populates it) — BLOCKS all user story test tasks (T004–T007) and the closed-transfer test (T010)
- **User Stories (Phases 3–6)**: All depend on Foundational (Phase 2) completion; independent of each other but share one file (`tests/test_barcode_scan.py`), so sequence T004 → T005 → T006 → T007 to avoid edit conflicts
- **Closed-Transfer Guard (Phase 7)**: T008/T009 depend only on Foundational; T010 depends on T008 and on the shared test file, so run after T004–T007
- **Polish (Phase 8)**: Depends on all of Phases 2–7 being complete

### Within Phase 7

- T008 (model guard) and T009 (view tweak) touch different files and have no dependency on each other — parallelizable
- T010 (test) depends on T008 (the guard must exist for the test to pass) and must be sequenced after T004–T007 (same file)

### Parallel Opportunities

- T002 and T003 (Phase 2) touch different files and can run in parallel
- T008 and T009 (Phase 7) touch different files and can run in parallel
- T004–T007 and T010 all edit `tests/test_barcode_scan.py` and must be sequenced, not parallelized

---

## Parallel Example: Foundational Phase

```bash
# Launch both Foundational tasks together — different files, no shared dependency:
Task: "Fix broken asset path in serichai-odoo/serichai_inventory_barcode/__manifest__.py"
Task: "Create base TransactionCase test class + fixtures in serichai-odoo/serichai_inventory_barcode/tests/test_barcode_scan.py"
```

## Parallel Example: Closed-Transfer Guard Phase

```bash
# Launch both together — different files, no shared dependency:
Task: "Add closed-transfer guard to action_scan_barcode in serichai-odoo/serichai_inventory_barcode/models/stock_picking.py"
Task: "Wrap widget tag in invisible condition in serichai-odoo/serichai_inventory_barcode/views/stock_picking_views.xml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003) — this alone fixes the blocking bug that keeps the widget from loading at all
3. Complete Phase 3: User Story 1 (T004)
4. **STOP and VALIDATE**: Run T004; manually scan an untracked product's barcode on a draft transfer and confirm a new line appears at quantity 1
5. Deploy/demo if ready — note the module already effectively supports US2–US4 server-side, so the manifest fix alone (T002) unblocks far more than just US1 in practice, but T004 is the smallest independently-verifiable slice

### Incremental Delivery

1. Setup + Foundational → widget loads, fixtures ready
2. Add US1 (T004) → test independently → MVP
3. Add US2 (T005) → test independently
4. Add US3 (T006) → test independently
5. Add US4 (T007) → test independently
6. Close FR-007 gap (T008–T010) → test independently
7. Polish (T011–T012) → full-suite + manual quickstart validation

---

## Notes

- This is a fix-and-close-the-gap pass, not a fresh build: 3 of 4 spec'd user stories (US1–US3, plus most of US4) already work correctly server-side once T002's one-line manifest fix lands — the bulk of the task list is the test coverage this addon has never had (research.md Decision 5), not new application logic
- FR-007 (Phase 7) is the one genuine code gap (research.md Decision 2) — everything else in this addon was verified correct by inspection against the spec
- Never modify vendored `odoo/` or the unrelated `serichai_inventory` skeleton addon (per CLAUDE.md and contracts/module-interface.md's out-of-scope list)
- Commit after each task or logical group; stop at any checkpoint to validate a story independently
