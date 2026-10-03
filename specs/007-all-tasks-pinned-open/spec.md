# Feature Specification: Open Pinned-Project Tasks from the Restricted "All Tasks" List

**Feature Branch**: `007-all-tasks-pinned-open`

**Created**: 2026-10-03

**Status**: Closed (2026-10-03). Implemented and deployed to `serichai-db`. All 33 automated tests pass. The user confirmed the browser behaviour after the T025 ACL fix. Known follow-up, not done: timesheets on pinned tasks (see tasks.md Notes).

**Input**: User description: "As solution architect, analysis this module serichai-odoo/serichai_project_security. I want to make Task List Group user can access inside task list detail information too for only allow project group. Currently, user in this group cannot enter inside due to the blocking. I want user on this to be able to access only Project that set in setting while other task cannot go inside." (Specified from the approved plan: "analysis requirement from this plan".)

## Clarifications

### Session 2026-10-03

- Q: How strictly should opening a task outside the pinned project be blocked? → A: In the interface **and** on the server. The "All Tasks" list opens only rows from the pinned project, and the system also refuses to show the task detail page for any other task when it is reached some other way: a direct link, a bookmarked URL, a link in an email or activity, or stepping to the next or previous record.
- Q: What should the user see when they click a task they are not allowed to open? → A: A short warning notice that they can only open tasks of the project allowed for their role. Rows that cannot be opened are also shown greyed out (muted) so the user can tell them apart before clicking.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a pinned-project task straight from "All Tasks" (Priority: P1)

A member of the "Task List Viewer (Production Planning Only)" role lands on **All Tasks**, their default page. The list shows production-stage tasks from many projects, plus every task of the project an administrator pinned in Settings (spec 006). Today clicking any row does nothing. To work on a pinned-project task, the user has to know to switch to the separate project menu and find the task again. The user should be able to click a pinned-project task in **All Tasks** and go straight to its detail page, where they can read and edit it as they already can from the project menu.

**Why this priority**: This is the core request. Without it the user still cannot "enter" a task from the list they work in every day.

**Independent Test**: Log in as a user who holds only the restricted role, with a project pinned in Settings. Open **All Tasks**, click a task that belongs to the pinned project, and confirm that its detail page opens and a field edit saves.

**Acceptance Scenarios**:

1. **Given** a restricted user and a pinned project, **When** they click a pinned-project task in **All Tasks**, **Then** the task detail page opens.
2. **Given** the detail page of a pinned-project task opened from **All Tasks**, **When** the user edits a field and saves, **Then** the change is saved. Editing rights are the same as from the project menu (spec 006 FR-002).
3. **Given** the detail page of a pinned-project task opened from **All Tasks**, **When** the user steps to the next or previous record, **Then** they move only between pinned-project tasks from that list and never land on a task they are not allowed to open.
4. **Given** the detail page of a pinned-project task, **When** the user tries to create a new task or delete this one, **Then** the action is unavailable or refused, as it is everywhere else for this role.

---

### User Story 2 - Tasks from other projects stay closed (Priority: P1)

The solution architect needs assurance that this opening applies only to the pinned project. Every other task in **All Tasks** must stay list-only: the user cannot reach its detail page by clicking, by URL, or by any other path.

**Why this priority**: This is equal to Story 1 because it is the security boundary the request depends on ("other task cannot go inside"). Shipping Story 1 without it would widen access beyond the request.

**Independent Test**: As the same restricted user, click a task in **All Tasks** that is not in the pinned project and confirm that nothing opens and a warning appears. Then paste that task's direct URL into the browser and confirm that access is refused.

**Acceptance Scenarios**:

1. **Given** a restricted user, **When** they look at **All Tasks**, **Then** rows outside the pinned project are visibly muted and pinned-project rows are not.
2. **Given** a restricted user, **When** they click a task outside the pinned project in **All Tasks**, **Then** no detail page opens and a warning says they can only open tasks of the project allowed for their role.
3. **Given** a restricted user, **When** they open the direct link of a task outside the pinned project (a typed URL, a bookmark, or a link from an email, notification, or activity), **Then** the system refuses with an access message and shows none of that task's detail page.
4. **Given** a restricted user viewing a pinned-project task whose detail page shows a related task from another project (for example a parent task or subtask), **When** they try to open that related task, **Then** access is refused.

---

### User Story 3 - Everyone else and every existing restriction is unaffected (Priority: P2)

Regular Project users and managers, and every existing protection on the restricted role, must behave exactly as before.

**Why this priority**: This is a regression guard. It matters, but it delivers no new value on its own.

**Independent Test**: Run the existing restricted-role regression checks (menus, hidden Tags column, stage filter, create and delete refusal, write limited to the pinned project) and the regular-Project-user checks, and confirm they all still pass.

**Acceptance Scenarios**:

1. **Given** a regular Project user, including one who also happens to hold the restricted role, **When** they open any task by any path, **Then** it opens as it did before this change.
2. **Given** a restricted user, **When** they browse **All Tasks**, **Then** the same set of tasks is listed as before this change. Nothing new becomes visible and nothing disappears.
3. **Given** a restricted user, **When** they use the project menu from spec 006 (board, list, and detail pages for the pinned project), **Then** it works exactly as before.

---

### Edge Cases

- **No project pinned** (fresh install, or the setting is cleared): every row in **All Tasks** is muted and none can be opened. Clicking shows the warning, and direct links to any task are refused. No error occurs.
- **Pinned project changed by an administrator**: what can be opened follows the new setting. Tasks of the previously pinned project become list-only again, and tasks of the newly pinned project can be opened. A list that is already open may need a refresh to update its muted styling, but the server-side refusal applies immediately.
- **Task moved out of the pinned project** while the user has it open: the next attempt to load or save it follows the normal rule for its new project, so it is refused.
- **Task moved into the pinned project**: it can be opened as soon as the list is refreshed.
- **Grouped or filtered "All Tasks" list**: the same per-row rule applies however the list is grouped, sorted, or filtered.
- **Opening in a new browser tab** (for example with a modifier-click): the same rule applies. A pinned-project row opens and any other row shows the warning.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In the restricted role's **All Tasks** list, the system MUST let the user open the detail page of a task that belongs to the project pinned in Settings (spec 006 FR-003).
- **FR-002**: In the same list, the system MUST NOT open the detail page of any task outside the pinned project. It MUST instead show a short, non-blocking warning that the user can only open tasks of the project allowed for their role.
- **FR-003**: The list MUST visually set apart (mute) rows that cannot be opened from rows that can.
- **FR-004**: The system MUST refuse to show the detail page of any task outside the pinned project to a restricted-role user, whatever path they use: list click, direct link, bookmark, notification or email link, or next/previous navigation. The refusal MUST NOT depend only on the list's on-screen behaviour.
- **FR-005**: Next/previous navigation from a detail page opened via **All Tasks** MUST move only between openable (pinned-project) tasks of that list.
- **FR-006**: The detail page opened from **All Tasks** MUST grant the same rights as the project menu from spec 006: existing pinned-project tasks can be edited, and creating and deleting tasks stays refused.
- **FR-007**: The set of tasks listed in **All Tasks** for the restricted role MUST NOT change. This feature changes only which listed tasks can be opened, not which tasks are visible.
- **FR-008**: Users who hold regular Project user or manager rights MUST NOT be affected, even if they also hold the restricted role.
- **FR-009**: All existing restrictions on the restricted role MUST continue to apply unchanged: hidden menus, hidden Tags column, the stage-based visibility filter outside the pinned project, editing limited to the pinned project, and create and delete refused everywhere.
- **FR-010**: Settings MUST keep using the single pinned-project setting from spec 006. Its help text MUST say that the pinned project's tasks can be opened from both **All Tasks** and the project menu.

### Key Entities

- **Restricted role ("Task List Viewer (Production Planning Only)")**: the existing user group whose members get a filtered, mostly read-only task list. This feature adds a project-scoped ability to open task detail pages from that list.
- **Pinned project (expanded-access project)**: the single project an administrator selects in Settings (spec 006). Being in this project is the only thing that decides whether a task can be opened.
- **Task**: a task listed in **All Tasks**. Whether it can be opened depends only on whether it currently belongs to the pinned project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A restricted user can get from **All Tasks** to the detail page of a pinned-project task in a single click, with no menu switch and no search.
- **SC-002**: 100% of attempts by a restricted user to open a task outside the pinned project are refused. This covers list clicks, direct URLs, notification links, and next/previous navigation, each checked on at least one task.
- **SC-003**: The number of tasks a restricted user sees in **All Tasks** is identical before and after the change, for the same data.
- **SC-004**: Every existing automated regression check for the restricted role and for regular Project users passes unchanged after the change.
- **SC-005**: In a walkthrough, a restricted user correctly tells openable rows from non-openable rows before clicking, from the visual styling alone.

## Assumptions

- "Only allow project group" in the request means "only tasks of the project pinned in Settings > Project > Task List Viewer Role" (spec 006). Exactly one project is pinned. Supporting several pinned projects is out of scope and could be a later extension.
- This feature controls who can open a task's detail page. It does not make data confidential. The restricted role can already read the tasks it sees in the list, and this feature does not narrow that. Hiding particular fields of non-pinned tasks would be a separate feature.
- The detail page shown is the standard task detail page that the project menu from spec 006 already uses. No new or reduced layout is introduced.
- This supersedes the spec 006 assumption that pinned-project tasks appear in **All Tasks** "still list-only there, no form". From this feature on they can be opened there too.
- The server-side refusal applies when the system is used interactively by a signed-in user. Background jobs and administrator scripts are unaffected.
- Depends on spec 006 (pinned-project setting, editing limited to the pinned project, the project menu) and spec 001 (restricted role, **All Tasks** list, hidden menus and Tags column).
