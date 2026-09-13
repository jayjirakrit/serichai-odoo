# Feature Specification: Contract MO Print Report for Project Task

**Feature Branch**: `005-contract-mo-report`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Improve the MO/task report layout in serichai_project_mo to follow standard Odoo report design/QWeb conventions, using contract_mo_sample.jpg as the reference for required content, while preserving all existing content/fields."

## Clarifications

### Session 2026-09-10

- Q: How should the printed report handle the "สำหรับผลิตประกาศเลขที่" (production announcement/order number) field, which has no matching data in Odoo today? → A: Show linked MOs' reference numbers (comma-separated MO names/references).

### Session 2026-09-11

Layout revision against the annotated mockup `project_mo_report-sample.png` (supersedes parts of the 2026-09-10 session):

- Q: What replaces the header block (job / order date / project / announcement number)? → A: The task name in a bordered box, followed by the task's `task_properties` rendered as label/value pairs. The order date, project line and the announcement-number field are dropped — the MO references now have their own table column.
- Q: How are properties handled when the project's property definition does not contain them? → A: Each property is checked for existence first; a property that no longer exists in the definition (or that the reader is not allowed to see) is skipped rather than printed. A property that exists but has no value still prints its label with a blank value, like the blank fields on the paper form.
- Q: What are the item table's columns? → A: Manufacturing Order, Product, Quantity (replacing ลำดับ / รายการ / จำนวน).
- Q: Does the rest of the paper form survive the revision? → A: Yes — the remarks (หมายเหตุ) section and both signature blocks (หัวหน้าแผนกเย็บ / ผู้สั่งผลิต) are unchanged.

### Session 2026-09-13

- Q: How many task_properties label/value pairs should print per line? → A: Three per line (one-third page width each), wrapping to a new line after every third property, instead of the previous four-per-line layout.
- Q: Should the report ever span more than one printed page? → A: Only when it has to. When the linked-MO count doesn't exceed the item table's fixed row capacity (so the item table itself fits on one page), the whole report — header, properties, item table, remarks, and both signature blocks — MUST render on a single page, with no content pushed onto a trailing near-empty second page by excess margins/padding. A task with more linked MOs than the table's row capacity (FR-007) is still allowed to spill onto additional pages — that overflow is expected, not a bug.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Print a company-standard order document for a task (Priority: P1)

Production/order staff working a project task that has one or more linked Manufacturing Orders need to produce a printed/PDF order document that looks like the company's existing paper production order form — so it can be handed to the sewing department without staff manually re-transcribing the job name, date, item list, and sizes/quantities out of Odoo onto a blank paper form.

**Why this priority**: This is the entire value of the feature — eliminating manual re-entry between Odoo and the existing paper process.

**Independent Test**: Open a project task that already has 2-3 linked Manufacturing Orders (different sizes) filled in, use Print, select "Contract MO," and confirm the resulting PDF shows the task name as the job, the order date, one table row per linked MO with size (product) and quantity, and the signature lines — without any manual editing.

**Acceptance Scenarios**:

1. **Given** a task with 3 linked MOs (sizes M/L/XL with quantities), **When** staff prints "Contract MO" from the task, **Then** the PDF's item table shows exactly 3 rows under the Manufacturing Order / Product / Quantity columns, each with the correct MO reference, product/size and quantity.
2. **Given** a task with a set name, **When** the report is printed, **Then** the boxed header shows the task's name exactly as recorded.
3. **Given** a task with remarks entered in its description, **When** the report is printed, **Then** the remarks (หมายเหตุ) section shows that text.
4. **Given** a task whose project defines properties (e.g. เลขที่สัญญา, จำนวน, ระยะส่ง, วันที่ลงนาม, วันหมดสัญญา), **When** the report is printed, **Then** each of those properties prints as a label/value pair below the name box, values formatted per property type (dates, selections, tags, related records shown by name).

---

### User Story 2 - Discover and print the report the same way as every other Odoo document (Priority: P2)

Any staff member viewing a project task in Odoo expects to find a way to print it the same way they print a Sales Order, Invoice, or Manufacturing Order — via the standard Print menu — with the same company branding/header chrome Odoo already applies to every other printed document, rather than a special button or an inconsistent one-off layout.

**Why this priority**: This is what "use Odoo layout and practice" specifically calls for; it depends on User Story 1 already producing the document content.

**Independent Test**: Open any project task form, open the Print dropdown, confirm "Contract MO" is listed automatically among the print options with no separate configuration step, and confirm the resulting PDF uses the same page layout conventions (headers/margins/company logo placement per the configured report layout) as other Odoo reports in this database.

**Acceptance Scenarios**:

1. **Given** any project task, **When** staff opens the Print dropdown on the task form, **Then** "Contract MO" appears in the list without needing a separate button or menu.
2. **Given** the company's configured report layout (logo, colors, footer) in Settings, **When** the Contract MO report is printed, **Then** it uses the same company header/footer chrome as other standard Odoo reports.

---

### User Story 3 - Report prints cleanly with incomplete data (Priority: P3)

Staff sometimes need to print or preview the order document for a task before every field is filled in yet — no Manufacturing Orders linked yet, no project set, or no remarks written — and the report must still produce a clean, usable document instead of an error or a broken layout.

**Why this priority**: Makes the feature reliable for real day-to-day use where data is entered progressively; depends on User Stories 1 and 2 already existing.

**Independent Test**: Create a bare-minimum task with no linked MOs, no project (hence no properties), and no description, print "Contract MO," and confirm the PDF renders without error, showing the same fixed-size ruled item table (all blank rows) as the paper form.

**Acceptance Scenarios**:

1. **Given** a task with zero linked Manufacturing Orders, **When** "Contract MO" is printed, **Then** the PDF renders without error, showing the full ruled item table with all rows blank.
2. **Given** a task with no project set (so no property definition) and no description text, **When** "Contract MO" is printed, **Then** the properties block and remarks section are simply omitted or left blank rather than causing an error.

---

### Edge Cases

- A task with more linked Manufacturing Orders than the table's default blank-row count still shows every linked MO row (the table grows) without dropping any data.
- A linked Manufacturing Order with an unusually long product/variant name wraps within its cell rather than being cut off or breaking the table layout.
- A task with multiple assignees lists all assignee names on the "ผู้สั่งผลิต" (orderer) signature line; a task with no assignees prints that line blank.
- A task with no linked Manufacturing Orders shows an entirely blank ruled item table rather than erroring.
- A task holding a stored property value whose definition has since been removed from its project skips that property entirely — no orphan label, no raw internal property name, no error.
- A task whose project defines many properties wraps them across multiple rows of three label/value pairs per line instead of overflowing the page width.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a printable "Contract MO" PDF report generated from a `project.task` record.
- **FR-002**: The report MUST be reachable from the task form's standard Print menu, using the same binding mechanism Odoo uses for every other document report (e.g., Sales Order, Manufacturing Production Order) — no dedicated print button or custom menu item.
- **FR-003**: The report MUST render using Odoo's standard report page chrome (company header/footer/logo as configured in the company's report layout settings), consistent with how other Odoo PDF reports render.
- **FR-004**: The report MUST show, at minimum, the following content items: company identity/branding, document title, the task name in a bordered box, the task's properties as label/value pairs, a boxed "Manufacturing Order" section heading, an itemized table (Manufacturing Order, Product, Quantity) with a fixed-size ruled grid, a remarks/notes area, and two labeled signature blocks.
- **FR-005**: The itemized table MUST include one row per Manufacturing Order linked to the task, showing that MO's product/variant (e.g., size) and ordered quantity.
- **FR-006**: When fewer Manufacturing Orders are linked than the table's default row count, the report MUST still render the remaining rows blank (ruled but empty), matching the fixed-size grid of the paper form.
- **FR-007**: When more Manufacturing Orders are linked than the table's default row count, the report MUST render every linked MO's row without omitting any.
- **FR-008**: The report MUST render without error for a task that has no linked Manufacturing Orders, no linked project, and no description text — omitting or blanking the corresponding sections rather than failing.
- **FR-009**: ~~The "สำหรับผลิตประกาศเลขที่" (production announcement/order number) field MUST show the comma-separated reference numbers/names of the task's linked Manufacturing Orders~~ — **superseded (2026-09-11)**: the announcement-number field, the order date and the project line are removed from the header; each linked Manufacturing Order's reference is instead shown in the item table's own "Manufacturing Order" column (FR-013).
- **FR-011**: The report MUST show the task's name inside a bordered box at the top of the page, as the job identifier (replacing the "สำหรับงาน" header line).
- **FR-012**: The report MUST render the task's `task_properties` as label/value pairs beneath the name box, restricted to the fixed set of contract fields เลขที่สัญญา, จำนวน, ระยะส่ง, วันที่ลงนาม, วันหมดสัญญา, ยื่นในนาม, หน่วยงาน (matched by the property's label/`string`) — any other property defined on the project is left off the report. Within that set, each property's existence is checked first: a property that is still defined for the task's project is printed (with a blank value when unset, mirroring the paper form's blank fields), and a property that is not (definition removed, or hidden from the reader by the project's property-visibility rules) MUST be skipped. Values MUST be printed in human-readable form per property type — dates formatted for the user's language, selection/tag properties by label, related records by display name. Properties MUST be laid out three per line (one-third page width each), wrapping to a new line after every third property rather than overflowing the page width. A task with none of these properties defined MUST omit the block entirely rather than error.
- **FR-013**: The item table MUST use the columns Manufacturing Order, Product and Quantity, one row per linked Manufacturing Order, showing that MO's reference, its product/variant and its ordered quantity with unit of measure.
- **FR-010**: Printing the report MUST follow the same access/visibility rules as viewing the underlying task — no separate permission layer is introduced.
- **FR-014**: When the number of linked Manufacturing Orders does not exceed the item table's fixed row capacity (so the table itself doesn't need to grow past one page, per FR-006/FR-007), the report MUST fit entirely on a single printed page — the template's spacing/margins MUST NOT push the remarks section or signature blocks onto a second page on their own. Tasks whose linked-MO count exceeds that capacity MAY still spill onto additional pages; that is expected, not a defect.

### Key Entities

- **Contract MO Report**: The printable document generated from a `project.task` record; combines fields from the task and its linked Manufacturing Orders into the company's standard order-form layout.
- **Project Task** (existing): The job/order being printed; supplies the job name, properties, remarks, and assignee(s) shown on the report.
- **Manufacturing Order** (existing, linked): Each one becomes a line item row on the printed report, contributing its reference number, product/variant and ordered quantity — one per table column.
- **Task Properties** (existing): The dynamic per-project properties held on `project.task.task_properties`; only the fixed contract header fields เลขที่สัญญา, จำนวน, ระยะส่ง, วันที่ลงนาม, วันหมดสัญญา, ยื่นในนาม, หน่วยงาน — matched by label, and still present in the project's property definition — are printed under the name box. Any other property defined on the project is not printed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Staff can produce a print-ready order document for any task with linked Manufacturing Orders in under 10 seconds (one click from the task's Print menu), with zero manual retyping of job, date, item, quantity, or reference-number data.
- **SC-002**: 100% of the report's required content sections (boxed task name, properties block, boxed "Manufacturing Order" heading, item table, remarks, two signature blocks) are present on the generated report.
- **SC-003**: The "Contract MO" report appears in the standard Print dropdown for 100% of project task records, with no per-task setup step.
- **SC-004**: Zero errors occur when printing the report for tasks with no linked Manufacturing Orders, no project, or no remarks — across a representative set of test tasks.
- **SC-005**: A task with more linked Manufacturing Orders than the table's default row count prints with 100% of its linked MOs represented as rows (no data loss).
- **SC-006**: A task whose linked-MO count is within the item table's default row capacity prints as exactly one page (no trailing near-empty second page), across a representative set of test tasks.

## Assumptions

- The report's item-table columns map to each linked Manufacturing Order's `name`, product/variant display name, and `product_qty` + unit of measure respectively.
- The report's default fixed-size item grid mirrors the paper form's row count (roughly 15-20 rows) closely enough to look consistent when printed; the exact count is a presentation detail, not a content requirement.
- Property labels printed on the report are the property definitions' own labels (their `string`), in whatever language/wording the project defines them — the report does not hardcode the contract field names shown in the mockup.
- The "ผู้สั่งผลิต" (orderer) signature line is labeled with the task's current assignee(s); if there are none, it prints as a blank line like "หัวหน้าแผนกเย็บ."
- This feature only adds the printable report; it does not change the existing Manufacturing Orders smart button, embedded MO list tab, or the many2many relation already in the module.
- Labels/section titles on the report may be presented bilingually (Thai primary, matching the paper form, with English secondary) for readability by all staff, consistent with how Thai and English terminology are already mixed in the module's existing UI.
