# Feature Specification: Restricted "All Tasks" Access (serichai_project_security)

**Feature Branch**: `001-restricted-task-access`

**Created**: 2026-08-06

**Status**: Draft (amended 2026-08-06 — see User Story 5)

**Input**: User description: "create spec for new module serichai_project_security base on /home/odoo/serichai-odoo/odoo-project-restricted-task-access-spec.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View only my relevant tasks (Priority: P1)

A production-planning staff member needs to see the list of tasks that are currently in the "Production Planning" (วางแผนการผลิต) stage, without being exposed to the full Project app's task backlog across every stage and project.

**Why this priority**: This is the entire reason the restricted role exists — without it, the user has no usable way to see their relevant work.

**Independent Test**: Assign the restricted role to a test user (and only that role) and confirm that opening "Tasks → All Tasks" shows a list containing exclusively tasks whose stage is "วางแผนการผลิต", regardless of which project they belong to.

**Acceptance Scenarios**:

1. **Given** a user holds only the restricted role, **When** they open Tasks → All Tasks, **Then** they see a list view containing only tasks in the "วางแผนการผลิต" stage.
2. **Given** tasks exist in other stages, **When** the restricted user views the list, **Then** none of those other-stage tasks appear, and no filter control exists that would let the user remove or bypass this restriction.
3. **Given** no tasks currently sit in the "วางแผนการผลิต" stage, **When** the restricted user opens All Tasks, **Then** they see an empty list rather than an error.

---

### User Story 2 - Cannot see or reach anything beyond the permitted list (Priority: P1)

The same user must not be able to drill into task details, switch to a different view style, or reach other parts of the Project app or other restricted apps — the role is meant to be a narrow, read-only window.

**Why this priority**: Equally critical to Story 1 — the feature is a security/visibility boundary, and any gap (clickable rows, alternate views, visible menus) defeats the purpose.

**Independent Test**: As the restricted test user, attempt each forbidden action (click a task row, switch view, browse to a task's direct form URL, open Projects/Reporting/Configuration menus, open the Dashboards app) and confirm each is blocked.

**Acceptance Scenarios**:

1. **Given** the restricted user is viewing All Tasks, **When** they click anywhere on a task row, **Then** no task form opens.
2. **Given** the restricted user navigates directly to a specific task's detail URL, **When** the page attempts to load, **Then** access is denied.
3. **Given** the restricted user is on the All Tasks page, **When** they look for view-switcher controls, **Then** no Kanban, Calendar, Pivot, Graph, or Activity options are shown or reachable.
4. **Given** the restricted user is in the Project app, **When** they look at the top navigation, **Then** only the Tasks menu is visible — Projects, Reporting, and Configuration are absent.
5. **Given** the restricted user is logged in, **When** they look at the app sidebar, **Then** the Dashboards app does not appear.

---

### User Story 3 - Simplified list without irrelevant columns (Priority: P3)

The restricted list should present a clean view relevant to production planning, without the Tags column that isn't needed for this user's workflow.

**Why this priority**: A usability refinement on top of the core access restriction — valuable but not essential to the security boundary itself.

**Independent Test**: As the restricted test user, open All Tasks and confirm the Tags column is not present anywhere in the list.

**Acceptance Scenarios**:

1. **Given** the restricted user opens All Tasks, **When** the list renders, **Then** no Tags column is shown.

---

### User Story 4 - No impact on existing users and other apps (Priority: P1)

Everyone who is not assigned the new restricted role — including normal Project users/managers and users of Sales, Inventory, Invoicing, Manufacturing, and Employees — must continue working exactly as before.

**Why this priority**: A regression here would break existing staff workflows; this is a hard non-negotiable guardrail equal in importance to the restriction itself.

**Independent Test**: As an existing normal Project user (not given the new role), confirm all previously available menus, stages, view switchers, Tags column, and task-opening behavior are unchanged after the new module is installed.

**Acceptance Scenarios**:

1. **Given** a user without the restricted role, **When** they use the Project app, **Then** they still see all stages, all views, the Tags column, and can open tasks normally.
2. **Given** a user of any other app (Sales, Inventory, Invoicing, Manufacturing, Employees), **When** they use their app, **Then** nothing about their access has changed.

---

### User Story 5 - All Tasks is the default landing page (Priority: P1)

*(Added 2026-08-06 amendment.)* Today the restricted role's top menu shows only "Tasks" (with "All
Tasks" nested underneath), while "Projects" is already hidden. But clicking the Project app icon
still lands the restricted user on the Projects Kanban board (To Do / In Progress / Done /
Cancelled columns) before they navigate into Tasks → All Tasks — an extra, avoidable step that also
exposes a page the role is supposed to keep hidden until they navigate past it.

The restricted user should land directly on their filtered All Tasks list the moment they click the
Project app icon, with no intermediate Projects/Tasks navigation, and the top menu bar should show
only "All Tasks" — no other tab.

**Why this priority**: This closes the last usability/visibility gap in an otherwise-complete
access boundary — without it, the restricted role's very first click still surfaces navigation
structure (and, transiently, a board) it was never meant to see. Equal priority to the original
access-restriction stories since it's part of the same boundary, not a cosmetic add-on.

**Independent Test**: As the restricted test user, click the Project app icon directly from the
app launcher (not a submenu link) and confirm the All Tasks list loads immediately, with the top
menu bar showing only "All Tasks".

**Acceptance Scenarios**:

1. **Given** a user holds only the restricted role, **When** they click the Project app icon from
   the launcher, **Then** the All Tasks list loads directly — not the Projects Kanban board and not
   an intermediate Tasks menu.
2. **Given** the restricted user is in the Project app, **When** they look at the top navigation,
   **Then** only "All Tasks" is shown — the "Tasks" top-level tab (and its "My Tasks" child) is no
   longer visible, in addition to Projects/Reporting/Configuration already being hidden.
3. **Given** a normal Project user or manager (not holding the restricted role), **When** they click
   the Project app icon, **Then** their existing default landing page (Projects) and full top menu
   bar (Projects, Tasks, Reporting, Configuration) are unchanged.

---

### Edge Cases

- What happens if a user is assigned the new restricted role **in addition to** an existing broader role (e.g. standard Project User/Manager)? Odoo permissions are additive across all of a user's roles, so the broader role would take precedence and the restrictions in this spec would not visibly apply. This module cannot fix that by itself — administrators are responsible for assigning the restricted role **exclusively** (see Assumptions).
- What happens if the "วางแผนการผลิต" stage is later renamed or removed? The restricted list would show no tasks (or fail to match), since the filter is based on the stage name; keeping the filter in sync with the stage is an ongoing administrative responsibility, not something the module manages dynamically.
- What happens when a restricted user tries to access a task via a bookmarked or shared direct link? The system must deny access rather than silently redirecting or partially loading data.
- What happens if a restricted user has no other-app roles at all? They should see only the Project app (with its reduced menu) and none of the apps they weren't already granted.
- What happens if a future change adds a new top-level Project menu entry visible to the restricted role with a lower sequence than All Tasks? *(Added 2026-08-06.)* That entry would silently become the new default landing page instead of All Tasks. Anyone adding a new menu under the Project app must re-verify this ordering — not something the module enforces dynamically.
- What happens with Project's built-in "Projects (grouped by stage)" twin menu when the "Use Stages on Project" setting is enabled org-wide? *(Discovered and closed 2026-08-06.)* Odoo swaps in a second "Projects" menu record whenever a user holds `project.group_project_stages`; on this deployment that group is implied by every internal user's base access, so the restricted role held it too and could still see a "Projects" tab through this twin even with the original "Projects" menu hidden. Closed by hiding the twin the same way. Anyone re-checking this restriction later should verify with the actual rendered menu tree (not just a per-menu group check), since Odoo resolves this pair dynamically per-user rather than through static XML groups.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a new, distinct access role scoped to viewing a filtered list of project tasks (referred to here as the "restricted role").
- **FR-002**: Users holding the restricted role MUST be able to open an "All Tasks" list of project tasks.
- **FR-003**: The All Tasks list for the restricted role MUST contain only tasks whose stage is "วางแผนการผลิต" (Production Planning), and this filtering MUST be enforced as a hard data-access restriction rather than a user-removable filter.
- **FR-004**: Users holding the restricted role MUST NOT be able to switch the All Tasks list to Kanban, Calendar, Pivot, Graph, or Activity view.
- **FR-005**: Users holding the restricted role MUST NOT be able to open the detail/form view of any individual task, whether by clicking a row in the list or by navigating to a direct link — this MUST be enforced at the data-access level, not only hidden in the interface.
- **FR-006**: The All Tasks list for the restricted role MUST NOT display a Tags column.
- **FR-007**: Users holding the restricted role MUST NOT see or be able to open the Dashboards app.
- **FR-008**: Users holding the restricted role MUST see only the All Tasks entry in the Project app's top navigation; the Projects, Tasks (and its My Tasks child), Reporting, and Configuration entries MUST be hidden for this role. *(Amended 2026-08-06 — originally read "only the Tasks entry"; superseded by FR-011/FR-012 below, which promote All Tasks to a top-level entry and hide Tasks itself.)*
- **FR-009**: Introducing the restricted role MUST NOT change access, menus, views, or data visibility for any existing user or role — access changes must be purely additive for the new role and must not modify permissions of Project's existing standard roles or of any other app's roles.
- **FR-010**: The system MUST continue to deny detail/form access to a restricted-role user even if they attempt to reach it through means other than the standard list (e.g. a direct URL), matching FR-005.
- **FR-011** *(added 2026-08-06)*: The All Tasks entry MUST be promoted to a top-level tab (a sibling of Projects/Tasks/Reporting/Configuration) for the restricted role, rather than nested under the Tasks menu, and MUST resolve as the default page shown when the restricted user opens the Project app — reachable in a single click from the app launcher with no intermediate menu selection.
- **FR-012** *(added 2026-08-06)*: The top-level "Tasks" menu (and its "My Tasks" child) MUST be hidden for the restricted role, in addition to Projects/Reporting/Configuration already being hidden per FR-008, so that no other top-level entry with a lower resolution priority than All Tasks remains visible to this role.

### Key Entities

- **Restricted Role**: The new access group being introduced; determines which users get the filtered, list-only, read-only view of tasks described in this spec.
- **Project Task**: The work-item record being viewed; relevant attributes here are its stage and tags.
- **Task Stage**: Classification of a task's progress (e.g. "วางแผนการผลิต" / Production Planning); used as the filtering criterion for the restricted role.
- **All Tasks View**: The list presentation of project tasks that the restricted role is entitled to see; scoped by stage, limited to list mode, and without a Tags column.
- **Project App Navigation**: The set of top-level menu entries (Tasks, Projects, Reporting, Configuration) whose visibility differs between the restricted role and standard roles. *(Amended 2026-08-06: for the restricted role specifically, "All Tasks" is itself now one of these top-level entries — see FR-011/FR-012 — rather than a submenu of Tasks.)*

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user holding only the restricted role can reach the filtered All Tasks list within 2 navigation actions after logging in.
- **SC-002**: 100% of tasks visible to a restricted-role user belong to the "วางแผนการผลิต" stage; 0% of tasks from other stages ever appear to that user.
- **SC-003**: 100% of attempts by a restricted-role user to open a task's detail view — whether by clicking a row or using a direct link — are blocked.
- **SC-004**: 0% of restricted-role users are able to switch the All Tasks list away from list view (no alternate view control is reachable).
- **SC-005**: 100% of existing non-restricted users retain unchanged behavior (same menus, views, stages, and task-opening ability) after this module is installed.
- **SC-006**: The Tags column appears in 0% of the restricted role's list renders.
- **SC-007**: The Dashboards app and the Project app's Projects/Reporting/Configuration menus are invisible to 100% of restricted-role users.
- **SC-008** *(added 2026-08-06)*: 100% of restricted-role users land directly on the All Tasks list within one click (the Project app icon itself) — 0% see the Projects Kanban board or any intermediate menu first.
- **SC-009** *(added 2026-08-06)*: The Project app's top menu bar shows exactly one tab ("All Tasks") for 100% of restricted-role users, and remains unchanged (all four original tabs, default Projects landing page) for 100% of non-restricted users.

## Assumptions

- The restricted role applies to **any** user it is assigned to, not to one hardcoded individual; the specific person(s) to assign it to is an administrative decision made after the module is installed.
- Administrators are responsible for ensuring a user assigned the restricted role does **not** simultaneously hold a broader Project role (standard Project User/Manager); Odoo's additive permission model means holding both would override these restrictions. This module addresses the technical restriction, not the administrative assignment process.
- Administrators are likewise responsible for keeping this user out of whatever role(s) currently control Dashboards-app access, and for leaving all other-app roles (Sales, Inventory, Invoicing, Manufacturing, Employees, etc.) untouched — this module does not alter those roles.
- The stage name used for filtering is the exact string "วางแผนการผลิต" (Production Planning) as it currently exists in the system; if that stage is renamed, the filter will need to be updated to match.
- "All Tasks" refers to a company-wide list of tasks across projects (not scoped to one specific project), consistent with the existing Project app's "All Tasks" concept.
- This restriction applies only to the standard backend UI; portal/customer-facing access and API-level access beyond the backend UI are out of scope for this spec.
- Sub-tasks are treated the same as top-level tasks for stage-based filtering (no special-casing).
