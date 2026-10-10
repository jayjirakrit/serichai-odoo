# Feature Specification: Configurable Project Access by Department

**Feature Branch**: `009-project-access-matrix`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Replace the hardcoded restricted task-viewer role with a configurable project and task access feature. Per department (user group), an administrator chooses which projects the department can access; per project, Read or Write; for Read, which task properties are hidden and which stages are shown; and whether users can only see the task list or also open task detail. Admin screen 'Project Access Group' under Project > Configuration. Restricted users see only the All Tasks and Project menus. Several departments merge by the most permissive rule. Migrate the current behaviour and remove the old module."

## Background

Today a single restricted role exists with fixed behaviour: one project is pinned in settings (full edit and open-detail), every other project shows only tasks in four production stages as a list-only view, and some task properties are hidden. Changing who sees what requires a developer. Business wants administrators to set this up themselves, per department and per project (specs 001, 002, 006, 007 describe the current behaviour that this feature generalises).

## Clarifications

### Session 2026-10-10

- Q: Should Write access allow deleting tasks? -> A: No. Write never deletes tasks or projects (FR-012).
- Q: What is the first screen of the Project menu? -> A: The list of accessible projects (FR-021); shown as project cards (the standard project overview), confirmed at plan review.
- Q: Are stages and hidden properties shared by all projects in a line? -> A: Yes, shared per line; administrators split lines when rules differ (FR-022).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator defines a department's project access (Priority: P1)

A project manager opens **Project > Configuration > Project Access Group**, sees a list of departments with the projects each one can access, and creates or edits a department entry. On the entry they choose the Odoo user group(s) that make up the department, then add project lines: which project(s), Read or Write, and for Read, the task properties to hide, the stages to show, and whether users may only see the task list or also open task detail. The entry also shows, read-only, which users belong to the department.

**Why this priority**: Without the configuration there is nothing to enforce; this replaces the developer-only setup.

**Independent Test**: Create a "Manufacturing" entry linked to a user group, add a line for one project with Read, list-only, two stages and one hidden property, save, and confirm the list shows "Manufacturing" with that project and the users tab lists the group's members.

**Acceptance Scenarios**:

1. **Given** a project manager, **When** they open Project > Configuration > Project Access Group, **Then** they see one row per department with its name and its projects.
2. **Given** a new department entry, **When** the manager selects a user group and adds a project line set to Read, **Then** the line offers the hidden-properties, shown-stages and task-access (list only / open detail) choices.
3. **Given** a project line set to Write, **When** the manager views it, **Then** hidden properties and stage choices are not offered, because writers need the full task.
4. **Given** a department entry, **When** the manager opens the User tab, **Then** the members of the selected user groups are listed read-only.
5. **Given** a user who is not a project manager, **When** they look in Project > Configuration, **Then** the Project Access Group screen is not available.
6. **Given** a project already granted in one line of a department, **When** the manager adds it in a second line of the same department, **Then** the system refuses it.

---

### User Story 2 - Read access with stage and property limits (Priority: P1)

A member of a department with Read access on a project sees only that project's tasks in the stages allowed, never sees the hidden task properties, and cannot change, create or open (beyond the allowed level) anything.

**Why this priority**: Protecting confidential data is the main business driver.

**Independent Test**: As a department member with Read on a project (stages "In Progress" and "Done", property "Cost" hidden), open All Tasks and the project; confirm only tasks in those stages appear, "Cost" is absent, and edits are refused.

**Acceptance Scenarios**:

1. **Given** Read access with stages "In Progress" and "Done", **When** the user lists tasks, **Then** tasks of that project in other stages are not shown.
2. **Given** Read access with no stages chosen, **When** the user lists tasks, **Then** tasks in all stages of that project are shown.
3. **Given** a hidden property, **When** the user views the task (list or detail), **Then** the property and its value are not shown, and a save by another party with Write access never loses its stored value.
4. **Given** Read access, **When** the user tries to edit, create a task in, or change that project, **Then** the system refuses.
5. **Given** a project the department was not granted, **When** the user searches or browses, **Then** its tasks and the project itself are not visible.

---

### User Story 3 - Task access level: list only or open detail (Priority: P1)

For each Read line the administrator chooses "list only" or "open detail". With list only, users see the task rows but cannot open the task; those rows are greyed out and a warning explains that opening is not allowed. With open detail, they can open the task and read all non-hidden information.

**Why this priority**: This is the second axis of the access matrix requested by business.

**Independent Test**: Give a department list-only on project A and open-detail on project B; in All Tasks, click a task of A (warning appears, not opened) and a task of B (opens).

**Acceptance Scenarios**:

1. **Given** list only on project A, **When** the user clicks a task of A in All Tasks, **Then** a warning appears and the task detail does not open; the row is shown greyed out.
2. **Given** list only, **When** the user reaches a task of A by direct link or by stepping to next/previous, **Then** the system also refuses to show its detail.
3. **Given** open detail on project B, **When** the user clicks a task of B, **Then** the detail opens, and stepping next/previous moves only among openable tasks.
4. **Given** a list only project, **When** the user looks for a way to create a task, **Then** none is offered.

---

### User Story 4 - Write access (Priority: P2)

A department with Write on a project can view all stages of it, open every task in full, edit tasks and create new tasks in it, with no hidden properties.

**Why this priority**: Replaces today's "pinned project" and is needed by the departments that actively work in a project.

**Independent Test**: As a department member with Write on project C, create a task in C, edit it, and confirm the same actions on a Read project are refused.

**Acceptance Scenarios**:

1. **Given** Write on project C, **When** the user opens any task of C in any stage, **Then** it opens fully with all properties.
2. **Given** Write on project C, **When** the user edits or creates a task in C, **Then** it is saved.
3. **Given** Write on project C, **When** the user attempts to delete a task of C, **Then** the outcome follows the decision on FR-012.

---

### User Story 5 - Restricted navigation and project dashboard (Priority: P2)

A user covered by any department entry sees only two Project menus: **All Tasks** and **Project**. **All Tasks** lists the tasks they may see. **Project** shows the projects they can access; opening one shows its tasks by stage, limited to allowed stages.

**Why this priority**: Gives restricted users a clear way to reach their projects; secondary to the access rules.

**Independent Test**: Log in as a department member; confirm only the two menus appear, and Project shows exactly the granted projects.

**Acceptance Scenarios**:

1. **Given** a restricted user, **When** they open the Project application, **Then** only All Tasks and Project are available.
2. **Given** a restricted user, **When** they click Project, **Then** they see only projects granted to their departments.
3. **Given** a restricted user, **When** they open a project from there, **Then** they see its tasks grouped by stage, showing only allowed stages.
4. **Given** a regular project user or manager (not in any department entry), **When** they use the application, **Then** nothing changes for them.

---

### User Story 6 - Several departments merge (Priority: P2)

A user whose groups belong to more than one department entry gets the most permissive combination for each project.

**Why this priority**: People often belong to several teams; behaviour must be predictable.

**Independent Test**: User is in Dept X (Read, list-only, stage "Done", hides "Cost") and Dept Y (Read, open detail, stage "In Progress", hides nothing) on one project; confirm the user sees both stages, can open detail and sees "Cost".

**Acceptance Scenarios**:

1. **Given** Read in one department and Write in another on the same project, **Then** the user has Write.
2. **Given** list-only in one and open detail in another, **Then** the user can open detail.
3. **Given** different stage selections, **Then** the user sees the union of stages; if any grant shows all stages, all are shown.
4. **Given** a property hidden in one grant but not another, **Then** it is visible; it is hidden only when every granting department hides it.
5. **Given** a project granted by only one department, **Then** that department's settings apply unchanged.

---

### User Story 7 - Migrate current behaviour and retire the old role (Priority: P3)

On go-live, existing restricted users keep the access they have today without manual rework, and the old hardcoded role is removed.

**Why this priority**: Required for safe rollout, but only after the configurable feature works.

**Independent Test**: On a copy of production data, run the migration; compare what a restricted user could see and do before and after; confirm the old role no longer exists.

**Acceptance Scenarios**:

1. **Given** the old pinned project, **When** migration completes, **Then** the migrated department has Write with open detail on it.
2. **Given** every other project, **When** migration completes, **Then** the department has Read, list only, the four production stages, and the properties previously hidden for the old role hidden.
3. **Given** existing users of the old role, **When** migration completes, **Then** they belong to the migrated department and see the same tasks, menus and limits as before.
4. **Given** migration completed, **Then** the old role, its settings and its menus are gone, and no menu restriction from it lingers.

---

### Edge Cases

- A project is archived or deleted: its lines no longer grant anything; the administrator is not blocked.
- A stage chosen in a line is later deleted or does not exist in the project: it is ignored; if none remain valid, no tasks of that project are shown (only an empty selection means all stages).
- A hidden-property name matches no property in the line's projects: the administrator is warned when saving; saving is allowed.
- A hidden property is renamed later: the old name no longer matches and the property becomes visible; accepted limitation, as in spec 002.
- A user is added to or removed from a user group: their access changes immediately without further admin action.
- A department entry is deactivated or deleted: its members lose the access and restricted status it gave (unless another entry covers them).
- A granted project uses a visibility setting that limits it to followers or invited users: access may still be blocked; the line shows a warning.
- A user belongs to no department entry: no restriction is applied.
- A user group is in an entry and the user is also a project user or manager: the standard higher rights apply and no restriction is added.
- Timesheets, sub-tasks and other records related to tasks are not covered by this feature.

## Requirements *(mandatory)*

### Functional Requirements

**Administration**

- **FR-001**: Project managers MUST be able to create, edit, deactivate and delete department entries under Project > Configuration > "Project Access Group"; no other users may.
- **FR-002**: The list screen MUST show, per entry, the department name and the projects it grants (as tags).
- **FR-003**: Each entry MUST have a name and at least one user group; every member of those groups belongs to the department.
- **FR-004**: The entry form MUST have a User tab (read-only members) and a Project tab (editable lines).
- **FR-005**: A line MUST specify one or more projects, access level (Read or Write) and task access (list only or open detail).
- **FR-006**: For Read lines, the administrator MUST be able to choose stages to show (empty means all) and a list of task property names to hide, typed one per line. These two options MUST not apply to Write lines.
- **FR-007**: A project MUST appear at most once within one department entry.
- **FR-008**: Task access choice MUST apply to Read lines only; Write lines always allow opening detail.
- **FR-009**: The system MUST warn the administrator about hidden-property names matching no property in the line's projects, and about projects whose visibility setting may block department members.

**Enforcement**

- **FR-010**: A department member MUST see only granted projects and, within them, only tasks in allowed stages; everything else is invisible in lists, searches, reports and direct links.
- **FR-011**: Read access MUST refuse any edit, creation or removal of tasks and any change to the project.
- **FR-012**: Write access MUST allow editing and creating tasks in the project, and MUST NOT allow deleting tasks or projects; deletion stays with project managers.
- **FR-013**: Hidden properties MUST be absent from what the user sees, and a save by an authorised person MUST never erase their stored values.
- **FR-014**: For list-only tasks the system MUST refuse to open task detail by any route (list click, direct link, bookmark, notification link, next/previous), show a warning on click, and show such rows greyed out.
- **FR-015**: The system MUST apply restrictions server-side, not only by hiding interface elements. Task list-only is a guard against opening the task, not a guarantee that the data cannot be read by other means, consistent with spec 007.
- **FR-016**: Access changes (entry edited, user group membership changed) MUST take effect without users needing to be reconfigured individually.
- **FR-017**: Members of any active department entry MUST become restricted users, unless they already hold standard project user or manager rights.

**Merging**

- **FR-018**: When several grants cover the same project for one user, the system MUST apply: Write over Read; open detail over list only; union of stages (any grant with all stages means all); a property hidden only if every granting entry hides it.

**Navigation**

- **FR-019**: Restricted users MUST see only the **All Tasks** and **Project** menus in the Project application.
- **FR-020**: **All Tasks** MUST list the tasks permitted by FR-010 with no creation option.
- **FR-021**: **Project** MUST show the accessible projects, and opening one shows its tasks by stage, limited to allowed stages. The first screen of Project MUST be the list of accessible projects.

**Settings per line**

- **FR-022**: One line MUST be able to cover several projects that share the same settings (access level, task access, stages, hidden properties). Administrators add separate lines when projects need different settings.

**Migration and removal**

- **FR-023**: Migration MUST create a department entry reproducing current behaviour: the pinned project as Write with open detail; all other projects as Read, list only, the four production stages, and the previously hidden properties.
- **FR-024**: Migration MUST move all users of the old role into that entry's department with no loss or gain of access.
- **FR-025**: After migration the old restricted role module MUST be removed, with all its menu and visibility restrictions, and no conflicting restrictions remaining.
- **FR-026**: The migration MUST be repeatable on a copy of production data for rehearsal before go-live.

### Key Entities

- **Department entry (Project Access Group)**: A named department linked to one or more user groups; can be active or inactive; owns project lines; shows its members.
- **Project line**: Belongs to a department entry; covers one or more projects; has access level (Read or Write), task access (list only or open detail), stages to show, and property names to hide.
- **Project**: An existing project that can be granted.
- **Stage**: An existing task stage, selected per Read line.
- **Task property**: A custom field defined on a project's tasks, identified by its label.
- **Restricted user**: A user covered by at least one active department entry who has no standard project user or manager rights.
- **Effective access**: The merged result for one user and one project (FR-018).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can set up a new department with one project grant (Read, stages, hidden property, task access) in under 5 minutes without developer help.
- **SC-002**: In acceptance tests, 100% of attempts by a restricted user to see ungranted projects, hidden stages, or hidden properties fail.
- **SC-003**: 100% of attempts to edit, create or delete on Read projects, and to open list-only tasks by any route, are refused.
- **SC-004**: All merge cases in FR-018 yield the expected result in tests.
- **SC-005**: After migration, a before/after comparison for each former role user shows identical visible tasks, menus and permitted actions.
- **SC-006**: Changing a grant or user group membership is reflected for affected users on their next page load, with no manual per-user action.
- **SC-007**: A restricted user reaches any granted project from the Project menu in no more than 2 clicks.

## Assumptions

- "Department" means one or more existing user groups; users are managed through normal group membership, not on the entry itself.
- Only two task access levels exist (list only, open detail).
- Typed property names are matched ignoring case and surrounding spaces; renaming a property breaks the match (accepted).
- Granted projects are expected to use the visibility setting that lets all internal staff see them; others show a warning.
- Task deletion by Write departments is not allowed (confirmed).
- Project and task editing by managers and standard project users is unchanged.
- Timesheets and other records linked to tasks are out of scope (same follow-up as spec 007).
- The old module's configuration is captured before it is removed; nothing is kept from it afterwards.
- No "copy department" convenience is included in this version.
