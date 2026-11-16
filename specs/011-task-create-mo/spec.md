# Feature Specification: Create Manufacturing Orders from a Project Task

**Feature Branch**: `011-task-create-mo`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Create MOs (Manufacturing Orders) from a Project Task, with a Finish Goods field on the task, a Create MO button, and an email to the project manager when all of a project's MOs are done."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create MOs from a task's Finish Goods (Priority: P1)

A production planner opens a task, lists the products to be manufactured under **Finish Goods**, then presses **Create MO** at the bottom of the Manufacturing Orders tab. A dialog asks who the MOs are assigned to. After confirming, one Manufacturing Order is created for each Finish Goods product, already linked to the task and the task's project.

**Why this priority**: This replaces manual MO creation and linking; it is the core value.

**Independent Test**: Put 3 products in Finish Goods on a task that belongs to a project, press Create MO, pick an assignee, confirm. Exactly 3 MOs exist, each with the chosen assignee, the task's project, and a link to the task.

**Acceptance Scenarios**:

1. **Given** a task in a project with Finish Goods set, **When** the user opens the Manufacturing Orders tab, **Then** a Create MO button is shown at the bottom of the tab.
2. **Given** a task with no Finish Goods, **When** the user opens the Manufacturing Orders tab, **Then** the Create MO button is not shown.
3. **Given** the dialog is open, **When** the user confirms without choosing an assignee, **Then** the system refuses and asks for an assignee.
4. **Given** the dialog is open with an assignee chosen, **When** the user confirms, **Then** one MO per Finish Goods product is created, assigned to that user, in the task's project, and linked to the task.
5. **Given** the dialog is open, **When** the user cancels, **Then** nothing is created.
6. **Given** MOs were created, **When** the dialog closes, **Then** the user sees the resulting MOs or a notice "N MOs created".

---

### User Story 2 - Safe re-runs without duplicates (Priority: P1)

A user who presses Create MO again, double-clicks Confirm, or adds one more product to Finish Goods and runs it again must never get duplicate MOs.

**Why this priority**: Duplicate MOs cause double production and stock errors.

**Independent Test**: Run Create MO twice on the same task; the second run creates nothing. Add a fourth product and run again; only one new MO appears.

**Acceptance Scenarios**:

1. **Given** every Finish Goods product already has a non-cancelled MO linked to the task, **When** the user confirms again, **Then** no MO is created and the user is told nothing new was needed.
2. **Given** some products are covered and one is new, **When** the user confirms, **Then** an MO is created only for the new product.
3. **Given** the only MO for a product was cancelled, **When** the user confirms, **Then** a new MO is created for that product.
4. **Given** the user double-clicks Confirm, **Then** only one set of MOs results.

---

### User Story 3 - Clear errors and warnings (Priority: P2)

The user is told plainly when the action cannot proceed, and warned about products that need attention.

**Why this priority**: Prevents confusing failures and half-prepared MOs.

**Independent Test**: Trigger Create MO on a task without Finish Goods and on a task without a project; each gives a clear message and creates nothing. Include a product with no bill of materials and see the warning.

**Acceptance Scenarios**:

1. **Given** a task with no Finish Goods, **When** Create MO is attempted by any means, **Then** a clear error is shown and nothing is created.
2. **Given** a task with no project, **When** Create MO is attempted, **Then** a clear error is shown and nothing is created.
3. **Given** a Finish Goods product has no bill of materials, **When** the dialog opens, **Then** it warns, naming those products, that their MOs will have no components; the user may still confirm.

---

### User Story 4 - Notify the project manager when all MOs are done (Priority: P2)

When every non-cancelled MO of a project is done, the project manager receives one email saying all finished goods are produced. The email wording is chosen on the project from a list of email templates; the default is "Project MO Complete Email Template", which gives the project, its manager, how many MOs are done, a table of those MOs with product and quantity, and a "View Project in Odoo" link. The email is handed to the mail queue at the end of the user's action, not while the user is still working, and projects that already existed receive the default template when the feature is installed (projects already complete at that moment are not notified retroactively).

**Why this priority**: Saves the manager from chasing progress, but depends on MOs existing.

**Independent Test**: In a project with 2 MOs, finish the first (no email), finish the second (one email to the project manager).

**Acceptance Scenarios**:

1. **Given** a project with at least one non-cancelled MO and all of them done, **When** the last one becomes done, **Then** one email using the project's selected template is sent to the project manager.
2. **Given** any MO of the project is still open, **Then** no email is sent.
3. **Given** all of a project's MOs are cancelled, **Then** no email is sent.
4. **Given** the email was already sent for the current batch, **When** further changes occur without a new MO, **Then** no second email is sent.
5. **Given** the email was sent, **When** a new MO is created for the project and later all MOs are done, **Then** a new email is sent.
6. **Given** a project with no template chosen, **Then** the default template is used; **Given** another template is chosen, **Then** that one is used.
8. **Given** the default template has been removed and the project has none chosen, **Then** no email is sent, the project is not marked as notified, and the problem is recorded in the server log so an administrator can fix it.
7. **Given** the project has no manager, **Then** no email is sent and the project is not marked as notified.

---

### User Story 5 - Right people can use the button (Priority: P1)

Project users can use the feature on tasks they can edit. People without Manufacturing creation rights can still create MOs through this button, but only if they are allowed to edit that task.

**Why this priority**: Without it users who lack Manufacturing creation rights cannot use the feature, or access could be widened by accident.

**Independent Test**: As a project user without Manufacturing creation rights, create MOs on a task they can edit (works); as a user who cannot edit the task, attempt it (refused).

**Acceptance Scenarios**:

1. **Given** a project user, **When** they use Create MO on a task they can edit, **Then** it works.
2. **Given** a user without Manufacturing creation rights who can edit the task, **When** they confirm, **Then** MOs are still created.
3. **Given** a user who cannot edit the task, **When** they attempt Create MO, **Then** it is refused and nothing is created.
4. **Given** the triggering user cannot send email, **When** the last MO becomes done, **Then** the project manager still receives the email.

### Edge Cases

- A product is removed from Finish Goods after its MO exists: the MO stays unchanged.
- A task is moved to another project after MOs exist: existing MOs keep their project; new MOs use the current one.
- An MO is linked to the task manually and covers a Finish Goods product: counts as covered.
- Two users press Confirm at the same time: still no duplicates.
- An MO is reopened after the email was sent: no re-send until a new MO is created.
- An MO created manually in Manufacturing for the project also resets the "already sent" state.
- An MO of the project is deleted or cancelled while the rest are done: the check is re-evaluated at that moment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The task form MUST provide a **Finish Goods** field accepting several products. There is no Buy Goods field.
- **FR-002**: The Manufacturing Orders tab MUST show a **Create MO** button at the bottom, visible only when Finish Goods is not empty.
- **FR-003**: The button MUST open a dialog with a required single **Assignee** and **Confirm** and **Cancel** actions.
- **FR-004**: The system MUST refuse to proceed, with a clear message, when the task has no Finish Goods or no project, wherever the action is triggered from.
- **FR-005**: On confirm, the system MUST create one MO per Finish Goods product, set to the chosen assignee and the task's project, and linked to the task.
- **FR-006**: Created MOs MUST be left in Draft, with quantity equal to the product's bill-of-materials quantity.
- **FR-007**: A Finish Goods product MUST be skipped when a non-cancelled MO for that product is already linked to the task; cancelled MOs do not count as coverage.
- **FR-008**: Repeated or simultaneous confirmations MUST NOT create duplicate MOs.
- **FR-010**: After confirmation the user MUST see the resulting MOs or the notice "N MOs created", and a notice when nothing new was needed.
- **FR-011**: The dialog MUST warn, naming the products, when Finish Goods products have no bill of materials; such products still create MOs (without components).
- **FR-012**: A project MUST allow choosing the email template for the "all MOs done" notice, defaulting to "Project MO Complete Email Template" (also assigned to projects that existed before installation).
- **FR-013**: When all non-cancelled MOs of a project are done and at least one exists, the system MUST send one email to the project manager using the project's template.
- **FR-014**: The system MUST NOT send that email while any non-cancelled MO is open, when all MOs are cancelled, or when it was already sent for the current batch.
- **FR-015**: The "already sent" state MUST reset whenever a new MO is created for the project, so a later batch can notify again.
- **FR-016**: The system MUST NOT mark the project as notified if there is no project manager to email.
- **FR-017**: Project users MUST be able to use the dialog on tasks they can edit.
- **FR-019**: Users lacking Manufacturing creation rights MUST be able to create MOs through this action only, and only after the system verifies they can edit the task.
- **FR-020**: The notification email MUST be sent regardless of the triggering user's email rights.
- **FR-021**: The "all done" check MUST run once per project at the end of the user's action, and only when something relevant changed: an MO becomes done or cancelled, an MO is deleted, or an MO moves to another project. Creating an MO does not trigger an email.
- **FR-022**: The **Create MO** button MUST be offered only to project users; the server checks of FR-004 and FR-019 apply regardless.
- **FR-023**: When the user who confirmed cannot view Manufacturing Orders, the confirmation MUST show the "N MOs created" notice instead of the MO list.

### Key Entities

- **Task**: Work item in a project; gains Finish Goods and links to MOs.
- **Finish Goods**: Product list on the task; drives MO creation.
- **Manufacturing Order (MO)**: Production order for one product; has an assignee, a project, a status (Draft, in progress, done, cancelled), and links to tasks.
- **Project**: Holds the project manager, the chosen notification email template, and whether the current batch was already notified.
- **Assignee**: The single user responsible for the created MOs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A task with N Finish Goods products yields exactly N MOs, each with the correct assignee, project and task link, in under 1 minute from opening the dialog.
- **SC-002**: Re-running Create MO on an unchanged task, or confirming twice quickly, creates 0 additional MOs in 100% of attempts.
- **SC-003**: Create MO on a task with no Finish Goods or no project always shows a clear message and creates 0 MOs.
- **SC-004**: When the last non-cancelled MO of a project becomes done, the project manager receives exactly one email, and 0 emails in the no-send situations of FR-014.
- **SC-005**: A new batch of MOs followed by completion triggers exactly one further email.
- **SC-007**: Users without Manufacturing creation rights succeed only when they can edit the task.

## Assumptions

- Single assignee only; Finish Goods is the only product list on the task and drives MO creation; no Buy Goods field (removed from scope at spec review); the email goes to the project manager (decisions already made with the stakeholder).
- MO quantity defaults to the product's bill-of-materials quantity; task-driven quantities are out of scope.
- MOs are left in Draft; confirming or scheduling them is a separate manual step.
- Products without a bill of materials still create an MO (no components) with a warning.
- "Done" means the MO's completed status; "open" means any non-cancelled, non-done status.
- A task already linked to MOs through the existing manual link keeps working; those MOs count as coverage.
- Coverage is judged per product per task, not per project.
- The email template list and default are maintained by administrators; the default template's wording has been refined by hand and administrators may edit it further.
- The email names the project, the project manager, the number of done MOs, a table of those MOs (order, product, quantity) and a link back to the project.
- Thai labels are provided for the new screens (Finish Goods, Create MO, dialog texts); a few texts still appear in English until translated.
- Requirement numbering skips FR-009 and FR-018 on purpose: they were removed with the Buy Goods field and kept unused so references stay stable.
- Buy Goods stays out of scope. The restricted Task List Viewer role and its security addon also stay out of scope (see below).
- Builds on the existing task-to-MO link. The restricted Task List Viewer role and the `serichai_project_security` addon are out of scope: this feature adds no access for that role and no dependency on that addon.
