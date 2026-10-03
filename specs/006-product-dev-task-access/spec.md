# Feature Specification: Expanded Task Access for Product Development Project

**Feature Branch**: `006-product-dev-task-access`

**Created**: 2026-09-30

**Status**: Closed (2026-10-01) — implemented; all automated tests pass. Manual walkthroughs T023/T029 (tasks.md) not yet performed.

**Input**: User description: "As solution architect, I want to update project security group list in module serichai-odoo/serichai_project_security to allow user group in group_project_task_list_only have more access in project 'Product Development'"

## Clarifications

### Session 2026-10-01

- Q: After delivery, the restricted user's "Product Development" menu showed column headers but no tasks — the pinned project's tasks sit in a stage ("To Do") outside the Production Planning stage filter. Should the pinned project's tasks be visible regardless of stage? → A: Yes — all tasks of the selected project must be shown, in every stage. This supersedes the original assumption that visibility was out of scope.
- Q: "All columns of the selected project" — list columns or Kanban stage columns? → A: Kanban stage columns: the "Product Development" entry point opens a Kanban board showing every stage of the pinned project as a column (including empty ones), like the standard project task board.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Restricted user works tasks in Product Development (Priority: P1)

A member of the "Task List Viewer (Production Planning Only)" role currently can only view a filtered, read-only list of tasks and cannot open a task's form or change anything on it. For the "Product Development" project specifically, these users need to actively work the tasks assigned to them (not just look at a list) — for example updating progress fields or moving a task forward — without being granted the full unrestricted access that a regular Project user has.

**Why this priority**: This is the entire purpose of the change; without it, nothing else in this feature has value.

**Independent Test**: Log in as a user with only the "Task List Viewer (Production Planning Only)" role, open a task that belongs to "Product Development", and confirm the expanded actions (see FR-002) succeed, while the same actions attempted on a task in any other project are still refused.

**Acceptance Scenarios**:

1. **Given** a restricted user and an existing task in the pinned "Product Development" project, **When** the user opens the task's full form and edits a field, **Then** the change is saved successfully.
2. **Given** a restricted user and a task in a project other than "Product Development", **When** the user attempts to open the form or edit a field, **Then** the system refuses it exactly as it does today.
3. **Given** a restricted user and tasks in the pinned "Product Development" project in any stage (including stages outside the Production Planning stage filter), **When** they open the "Product Development" menu, **Then** every task of that project is shown. *(Revised 2026-10-01 — originally "same visibility rules as before"; see Clarifications.)*
4. **Given** a restricted user and a task in the pinned "Product Development" project, **When** the user attempts to create a new task or delete an existing one, **Then** the system refuses it, since create/delete remain out of scope for this role.
5. **Given** a restricted user, **When** they open the "Product Development" menu, **Then** a Kanban board is shown with one column per stage of the pinned project (including stages with no tasks), and they can move a task between columns; they cannot create, rename, fold-configure, or delete stage columns.

---

### User Story 2 - Existing restrictions remain intact everywhere else (Priority: P2)

The solution architect needs assurance that loosening access for "Product Development" does not accidentally loosen access anywhere else, and does not regress any of the protections the restricted role already relies on (hidden menus, hidden Tags column, list-only view, stage-based visibility).

**Why this priority**: A security change that silently widens scope beyond the one named project would be a regression, not an enhancement.

**Independent Test**: Run the existing restricted-role regression checks (menu visibility, form-access denial, hidden Tags column) against a task in a project other than "Product Development" and confirm they all still pass unchanged.

**Acceptance Scenarios**:

1. **Given** a restricted user, **When** they interact with a task in any project other than "Product Development", **Then** all current restrictions (no form access, read-only, hidden Tags column, hidden menus) continue to apply exactly as before.
2. **Given** a restricted user, **When** the "Product Development" project is renamed, archived, or deleted, **Then** the expanded access no longer applies to tasks that were formerly under that project name (access is tied to the current project record, not a cached name).

---

### Edge Cases

- What happens if no project named exactly "Product Development" exists yet in a given database (e.g., a fresh install)? The expanded permission grant should simply apply to no tasks, without error, until such a project exists.
- What happens if two different projects both happen to be named "Product Development"? Resolved: the expanded access is pinned to one specific, administrator-selected project record (see FR-003/FR-004), not to a name match, so a later, unrelated project reusing the same name does not inherit the access.
- What happens to a task that is moved out of "Product Development" into another project? The restricted user's expanded access should end for that task the moment it leaves the project, and the ordinary restricted-role rules should apply again.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST continue to apply all of the restricted role's current limitations (read-only access, no form view, hidden Tags column, hidden Projects/Reporting/Configuration menus, stage-based visibility filter) to every project except "Product Development".
- **FR-002**: For tasks that already exist in the "Product Development" project, the restricted role MUST additionally be able to open the full task form and edit its fields (e.g. update progress, change stage). Creating new tasks and deleting tasks remain out of scope for this role — those actions continue to be refused, in "Product Development" as everywhere else.
- **FR-003**: The expanded access MUST be pinned to one specific project record, selected by an administrator during configuration (not resolved by matching the project's display name at runtime). It MUST NOT extend to any other project, including one created later with the same or a similar name, unless an administrator explicitly re-configures it to point at a different record.
- **FR-004**: If the pinned "Product Development" project is renamed, the expanded access MUST continue to follow the same underlying project record (i.e., it MUST NOT silently drop the grant just because the name changed, and MUST NOT accidentally pick up a different, newer project that happens to reuse the old name).
- **FR-005**: The system MUST NOT grant the restricted role any additional access to projects other than "Product Development" as a side effect of this change.
- **FR-007**: For tasks in the pinned project only, the restricted role MUST be able to see the task regardless of its stage (the Production Planning stage filter does not apply to the pinned project). Tasks in every other project remain subject to the stage filter unchanged.
- **FR-008**: The restricted role's "Product Development" entry point MUST open a Kanban board grouped by stage that shows every stage of the pinned project as a column, including empty stages, with list and form views also available. Stage (column) management stays unavailable to this role.
- **FR-006**: All expanded actions performed by the restricted role on "Product Development" tasks MUST remain subject to the same data-visibility and audit expectations already in place for the standard Project module (e.g., normal Odoo change tracking / chatter logging continues to record who changed what).

### Key Entities

- **Restricted Role (`group_project_task_list_only`)**: The existing user group whose members get a filtered, mostly read-only view of project tasks; this feature adds project-scoped exceptions to what they can do.
- **Project ("Product Development")**: The specific `project.project` record that the expanded permissions apply to; identified by its project record, not merely reused whenever a project of that name exists.
- **Task**: A `project.task` record whose applicable permission level (the current restricted rules vs. the new expanded rules) now depends on which project it belongs to.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A restricted-role user can successfully complete the expanded action(s) on a "Product Development" task on the first attempt, with no administrator intervention needed after initial setup.
- **SC-002**: 100% of restricted-role attempts to perform the same expanded action on a task outside "Product Development" continue to be refused, matching pre-change behavior.
- **SC-003**: Existing restricted-role regression checks (menu visibility, hidden Tags column, form-access denial, stage-based visibility) pass unchanged for every project other than "Product Development" after this feature ships.
- **SC-004**: No project other than "Product Development" gains any new capability for the restricted role as a result of this change, verified by spot-checking at least one other existing project.
- **SC-005**: 100% of restricted-role attempts to create or delete a task — including within "Product Development" — continue to be refused, confirming the expanded access stayed limited to editing existing tasks.

## Assumptions

- "Product Development" refers to a single, specific `project.project` record that already exists in this deployment; an administrator pins the expanded-access configuration to that exact record (not to a name match), per FR-003.
- ~~The stage-based visibility rule (`rule_task_stage_restricted`) is a separate concern from this feature.~~ *Superseded 2026-10-01 (see Clarifications, FR-007)*: the stage filter is lifted for the pinned project only; it continues to apply to every other project. A consequence is that pinned-project tasks in any stage also appear in the restricted "All Tasks" list (still list-only there, no form). *Superseded 2026-10-03 by spec 007 (`specs/007-all-tasks-pinned-open/`)*: pinned-project tasks can now be opened from "All Tasks" too; other rows there remain closed.
- This change is additive/scoped: the broader "Task List Viewer (Production Planning Only)" role keeps its name, its implied base membership, and all of its current restrictions for every project except the one named exception.
- No new user-facing role name or menu structure is required; the existing role simply behaves differently depending on which project a task belongs to.
