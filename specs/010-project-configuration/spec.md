# Feature Specification: Project Configuration – High-Value-First Task Sorting

**Feature Branch**: `010-project-configuration`

**Created**: 2026-10-19

**Status**: Draft (revised after plan review, 2026-10-19)

**Input**: User description: "I want to analysis and planning new module for project configuration starting with sort project task. New module call serichai_project_configuration." Reference rule: tasks whose project value (task property labelled "มูลค่าโครงการ") is above 50,000,000 come first, then all tasks by deadline (earliest first, no deadline last). If the property does not exist, tasks simply sort by deadline, with no errors.

## Background

Serichai wants a new "project configuration" module that will, over time, hold business-configurable behaviour for projects and tasks. This first feature delivers one fixed sorting rule: starred (high priority) tasks stay at the top of the task list and task board as today, high-value work comes next within them and within all other tasks, and everything is then ordered by deadline, so planners see the most important and most urgent work first.

The project value is not a standard task field. It is a **task property** (a custom field that each project defines for its tasks) labelled **"มูลค่าโครงการ"** (Thai for "project value"). Each project defines its own properties, so the property may exist in some projects and not in others, may be renamed or removed later, and may have been entered as a number or as text (for example "60,000,000").

Terms used in this spec:

- **Project value**: the amount entered in a task's "มูลค่าโครงการ" property, read as a number.
- **High-value task**: a task whose project value is strictly greater than the **high-value threshold** (default 50,000,000).
- **Hidden property**: a task property that the project access feature (spec 009) hides from some users.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Planners see starred, then high-value tasks first, then by deadline (Priority: P1)

A planner opens the task list or task board (All Tasks, My Tasks, or a project's tasks). Starred (high priority) tasks appear at the top, as today. Within the starred tasks, and within all other tasks, high-value tasks come first. Within each of these groups, tasks are ordered by deadline, earliest first, with tasks with no deadline last; tasks with the same deadline are shown most recently created first. On the task board, the same order applies inside each stage column.

**Why this priority**: This is the business rule that motivated the feature; it alone delivers the value.

**Independent Test**: In a project that has the "มูลค่าโครงการ" property, create tasks with values 60,000,000 (deadline next month), 40,000,000 (deadline tomorrow), none (deadline next week), 70,000,000 (no deadline), and a starred task with no value (deadline in two weeks). Open the task list and confirm the order: starred task, 60M (next month), 70M (no deadline), 40M (tomorrow), no value (next week).

**Acceptance Scenarios**:

1. **Given** a task with project value 60,000,000 and a task with 40,000,000 and an earlier deadline, both not starred, **When** a planner opens the task list, **Then** the 60,000,000 task is listed first.
2. **Given** a starred task that is not high-value and a high-value task that is not starred, **When** the list is shown, **Then** the starred task is first.
3. **Given** two starred tasks, one high-value and one not, **When** the list is shown, **Then** the high-value starred task is first.
4. **Given** two high-value tasks with the same priority and different deadlines, **When** the list is shown, **Then** the one with the earlier deadline is first.
5. **Given** two tasks with the same priority that are not high-value, one with a deadline and one without, **When** the list is shown, **Then** the task with the deadline comes first.
6. **Given** two tasks with the same priority, high-value status and deadline, **When** the list is shown, **Then** the more recently created task is first.
7. **Given** the task board grouped by stage, **When** a planner looks at any stage column, **Then** tasks in that column follow the same order.
8. **Given** the property value is entered as text "60,000,000", **When** the list is shown, **Then** the task is treated as a 60,000,000 high-value task.
9. **Given** a value of exactly 50,000,000, **When** the list is shown, **Then** the task is not high-value.
10. **Given** a planner clicks a column heading to sort the list differently, **When** the list re-sorts, **Then** the planner's choice is applied for that view and the default order returns the next time the view is opened.

---

### User Story 2 - Sorting never fails when the property is missing or odd (Priority: P1)

The property may be missing from some or all projects, may be renamed or deleted, or may contain unexpected entries (letters, blank, several values). In all of these cases the task list and board still open, tasks still save, and affected tasks simply sort by priority and deadline as non-high-value tasks. No error or warning is shown to users.

**Why this priority**: A sorting convenience must never block daily work; this is a hard business requirement.

**Independent Test**: In an environment where no project has the property, open the task list and confirm the order is exactly priority, then deadline order. Then enter "abc" as the value of one task and confirm it saves and sorts by priority and deadline only.

**Acceptance Scenarios**:

1. **Given** no project has the "มูลค่าโครงการ" property, **When** a planner opens the task list, **Then** tasks appear in priority then deadline order only (starred first; earliest deadline first, no deadline last), with no errors or warnings.
2. **Given** a task without a project, or in a project without the property, **When** the list is shown, **Then** the task has a project value of 0, is not high-value, and sorts by priority and deadline.
3. **Given** a value that cannot be read as a number (e.g. "abc", blank), **When** the task is saved, **Then** the save succeeds and the task is treated as value 0, not high-value.
4. **Given** two projects that each define a property labelled "มูลค่าโครงการ" independently, **When** tasks in both are listed, **Then** values from both projects are recognised.
5. **Given** a task is moved to another project, **When** the move is saved, **Then** its project value and high-value status are re-evaluated immediately using the new project's property (0 if it has none).
6. **Given** a project removes or renames the "มูลค่าโครงการ" property, **When** the project's property definitions are saved, **Then** its tasks keep their current high-value status until an administrator runs "Recalculate high-value flag" or the task's value is next edited, after which they are not high-value; the definition change itself causes no error.

---

### User Story 3 - Planners can see and filter by project value (Priority: P2)

In the task list, planners can show a "Project Value" column (shown by default, can be hidden) and apply a "High Value" filter to see only high-value tasks. When a task's value is edited, the amount shown and the high-value status are updated together.

**Why this priority**: Makes the sort explainable and lets planners focus on high-value work; useful but not required for the sort itself.

**Independent Test**: Open the task list, confirm the Project Value column shows each task's value, apply the "High Value" filter and confirm only tasks above the threshold remain.

**Acceptance Scenarios**:

1. **Given** the task list, **When** a planner opens it, **Then** a "Project Value" column is shown and can be hidden through the optional-columns menu.
2. **Given** the search options, **When** the planner applies "High Value", **Then** only high-value tasks are listed.
3. **Given** a planner edits a task's "มูลค่าโครงการ" value, **When** the task is saved and the list is shown, **Then** the Project Value column and the task's high-value status both reflect the new value.

---

### User Story 4 - Administrators adjust the threshold and refresh values (Priority: P2)

An administrator can change the high-value threshold in the Project settings. Because tasks are re-evaluated automatically only when their own value changes, the administrator runs a "Recalculate high-value flag" action that re-evaluates every task after changing the threshold or after a project's property definitions change. The Settings screen reminds the administrator to do this.

**Why this priority**: The 50,000,000 limit is a business figure that will change; changing it should not need a developer.

**Independent Test**: Set the threshold to 30,000,000 in Settings, save, run the recalculation, and confirm a 40,000,000 task now sorts in the high-value group and appears under "High Value".

**Acceptance Scenarios**:

1. **Given** the threshold has never been set, **When** tasks are evaluated, **Then** 50,000,000 is used.
2. **Given** the administrator changes the threshold to 30,000,000 and runs the recalculation, **When** the list is shown, **Then** tasks above 30,000,000 are high-value.
3. **Given** the administrator changes the threshold but has not yet run the recalculation, **When** the list is shown, **Then** tasks keep their previous high-value status, except tasks whose value has been edited since.
4. **Given** the administrator views the threshold setting, **When** they read it, **Then** the screen tells them to run "Recalculate high-value flag" after changing the threshold.
5. **Given** the threshold is set to something that is not a valid amount (e.g. empty, letters, negative), **When** tasks are evaluated, **Then** 50,000,000 is used silently.
6. **Given** one task's data cannot be evaluated during the recalculation, **When** the recalculation runs, **Then** that task is set to value 0 and all other tasks are still processed.
7. **Given** a user who is not an administrator, **When** they look for the threshold setting or the recalculation action, **Then** neither is available.

---

### User Story 5 - Existing tasks are ready on installation (Priority: P2)

When the module is installed, every existing task gets its project value and high-value status, so the new order is correct immediately. Installation succeeds even when no project has the property.

**Why this priority**: Without it, the sort would only be right for tasks edited after go-live.

**Independent Test**: Install the module on a copy of production data and confirm, without editing any task, that existing high-value tasks are at the top of All Tasks.

**Acceptance Scenarios**:

1. **Given** existing tasks with project values, **When** the module is installed, **Then** their values and high-value status are set without any task being edited.
2. **Given** a company where no project has the property, **When** the module is installed, **Then** installation succeeds and all tasks have value 0.
3. **Given** some tasks with unreadable values, **When** the module is installed, **Then** installation still succeeds and those tasks get value 0.

---

### User Story 6 - Users who cannot see the project value still get a correct list (Priority: P1)

When the project access module (spec 009) is installed, some users have the "มูลค่าโครงการ" property hidden from them by its settings. No special handling is added for them: their task list and board follow the same order as for everyone else, without errors, and they get the same "Project Value" column and "High Value" filter. Where the property is hidden from them, the column shows only what they are allowed to read (0 or nothing), which is acceptable.

**Why this priority**: Restricted users use the same All Tasks list daily; an error there is not acceptable.

**Independent Test**: As a restricted user for whom "มูลค่าโครงการ" is hidden on a project, open All Tasks: the list loads in the same order as for other users, the Project Value column and "High Value" filter are offered, and the column shows 0 or nothing for that project's tasks, never the real amount.

**Acceptance Scenarios**:

1. **Given** a user for whom the property is hidden, **When** they open the task list or board, **Then** it loads without error and follows the same order as for other users.
2. **Given** that user, **When** they look at the Project Value column for tasks where the property is hidden from them, **Then** it shows 0 or nothing, not the real amount.
3. **Given** that user, **When** they apply the "High Value" filter, **Then** it works as for other users, without errors.
4. **Given** a user who can see the property in project A but not in project B, **When** they view tasks from both, **Then** real amounts are shown only for project A tasks.

---

### Edge Cases

- Value entered with thousands separators, spaces or a decimal part ("60,000,000.50", " 60000000 "): read as the number; other symbols or words make it unreadable (value 0).
- Negative values: read as entered; never high-value while the threshold is positive.
- More than one property in the same project carries the label "มูลค่าโครงการ": the first one in the project's property order is used.
- Label typed with leading or trailing spaces: still matched; any other spelling difference is not matched.
- Property holds a list or another non-amount type: value 0.
- Monetary values in different currencies: compared as plain amounts, without currency conversion.
- Threshold changed but recalculation not run: tasks keep their previous high-value status until their value is edited or the administrator runs the recalculation; the setting tells the administrator to run it.
- Property definition changed on a project (added, renamed, removed): the high-value status of that project's tasks is updated by the next recalculation or when each task's value is edited. Until then, the displayed project value may already reflect the change while the high-value status does not (accepted limitation; see Assumptions).
- Starred task that is also high-value: shown above starred tasks that are not high-value; all starred tasks stay above all unstarred tasks.
- Archived tasks: evaluated like other tasks; they appear in the same order when shown.
- Task board drag and drop: dropping a task at a position inside a column does not keep that manual position; see Assumptions.
- Customer portal, printed reports, other modules and other task screens (e.g. activities, calendar, Gantt): keep their current order.

## Requirements *(mandatory)*

### Functional Requirements

**Module**

- **FR-001**: The feature MUST be delivered as a new, separately installable project configuration module named `serichai_project_configuration`, intended to hold future project configuration features. It MUST depend only on the standard Project application (no dependency on other Serichai modules), so that other Serichai modules can build on it. The project access module (spec 009) MUST NOT be changed by this feature.

**Project value**

- **FR-002**: The system MUST determine each task's project value from the task property labelled "มูลค่าโครงการ" in the task's own project, matching by label (ignoring leading and trailing spaces), never by a fixed internal identifier.
- **FR-003**: The system MUST accept the value whether entered as a whole number, a decimal number, a monetary amount, or text containing a number with optional thousands separators.
- **FR-004**: The project value MUST be 0 when the task has no project, the project has no such property, the value is empty, or the value cannot be read as a number.
- **FR-005**: A task MUST be high-value when, and only when, its project value is strictly greater than the high-value threshold.
- **FR-006**: A task's project value and high-value status MUST be re-evaluated together and immediately, as part of the same save, only when the task's "มูลค่าโครงการ" value changes: (a) the task's own property value is edited; (b) the task moves to another project (which changes its property values). Editing a project's property definitions and changing the threshold MUST NOT re-evaluate tasks automatically; their effect on the high-value status applies when the recalculation (FR-015) runs or when a task's value is next edited.
- **FR-007**: Evaluation failures MUST never block saving a task, saving a project's property definitions, saving the settings, opening a list or board, installing the module, or running the recalculation, and MUST NOT show any error or warning to users. Failures are recorded only in technical logs, identifying the task, for support use.

**Sorting**

- **FR-008**: The internal task list and task board views (including All Tasks, My Tasks, a project's tasks, and the restricted task list and board from spec 009) MUST by default order tasks by: (1) starred (high priority) tasks first; (2) then high-value tasks first; (3) then, as today, tasks in the same status together (the standard status order, so open tasks stay apart from done and cancelled ones); (4) then deadline ascending, with tasks without a deadline last; (5) then most recently created first.
- **FR-009**: When no task is high-value (including when no project has the property), the default order MUST be identical to ordering by priority (starred first), then status as today, then deadline ascending with empty deadlines last, then most recently created first.
- **FR-010**: The new order MUST NOT change the order of tasks anywhere else, including the customer portal, printed reports, exports, other modules and other task screens.
- **FR-011**: Users MUST still be able to re-sort a list by clicking a column heading.

**Visibility**

- **FR-012**: The task list MUST offer a "Project Value" column, shown by default and hideable by the user.
- **FR-013**: The task search MUST offer a "High Value" filter showing only high-value tasks.

**Administration**

- **FR-014**: Administrators MUST be able to set the high-value threshold as an amount, including 0 (which makes every task with a positive value high-value); when it is not set or not a valid non-negative amount, the system MUST use 50,000,000 without warning.
- **FR-015**: Administrators MUST be able to run a "Recalculate high-value flag" action that re-evaluates every task; it is the normal step after changing the threshold or a project's property definitions, and is also used for maintenance. A failure on one task MUST NOT stop the others. The threshold setting MUST tell the administrator to run this action after changing the threshold.
- **FR-016**: Only administrators MUST be able to change the threshold or run the recalculation.
- **FR-017**: On installation, the system MUST evaluate every existing task, in portions so that installation stays reliable with large numbers of tasks, and installation MUST succeed whether or not any project has the property.

**Interaction with hidden properties (spec 009)**

- **FR-018**: Users for whom "มูลค่าโครงการ" is hidden on a project MUST get the same order as everyone else for that project's tasks, without errors.
- **FR-019**: The "Project Value" column and the "High Value" filter MUST be offered to all users. The column MUST NOT show an amount the user is not allowed to read; where the property is hidden from them, it may show 0 or nothing, which is acceptable.
- **FR-020**: This feature MUST NOT weaken any existing access restriction; users still see only the tasks they were already allowed to see.

### Key Entities

- **Task**: An existing project task; gains a project value (number, 0 by default) and a high-value status (yes/no), both derived, never typed by users, and updated together when the task's value is edited or recalculated.
- **Project**: An existing project; defines the properties its tasks carry, possibly including "มูลค่าโครงการ".
- **Task property "มูลค่าโครงการ"**: A per-project custom task field, identified by its label, holding the task's project value.
- **High-value threshold**: A single company-wide amount set by administrators, default 50,000,000.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance tests, 100% of task lists and boards in scope show every starred task above every unstarred task, every high-value task above every other task of the same priority, and each resulting group in deadline order with empty deadlines last.
- **SC-002**: With no project defining the property, the default list order matches priority then deadline order for 100% of tasks.
- **SC-003**: Zero errors or warnings are shown to users across all test cases with missing, renamed, deleted or unreadable property values, including installation, saving property definition changes, saving threshold changes and recalculation.
- **SC-004**: All value formats in FR-003 (number, decimal, monetary, text "60,000,000") are recognised correctly in 100% of test cases.
- **SC-005**: An administrator can change the threshold in Settings, run the recalculation and see the new result in the task list in under 2 minutes, without developer help.
- **SC-006**: Immediately after installation on a copy of production data, 100% of existing tasks with a value above the threshold appear in the high-value group, with no manual task edits.
- **SC-007**: A user for whom the property is hidden opens All Tasks without error, in the same order as other users, and sees the real project value amount on 0 tasks where it is hidden.
- **SC-008**: Customer portal and printed report task order is unchanged before and after installation.
- **SC-009**: In 100% of test cases, after a task's "มูลค่าโครงการ" value is edited or the task is moved to another project, the Project Value column, the high-value status and the task order all reflect the change the next time the list is opened, with no recalculation run; after a threshold or property definition change, they do so in 100% of test cases once the recalculation has run.

## Assumptions

- The rule is fixed for this version: high-value first, then deadline. Configurable sort rules or presets chosen by users, a "Sort By" menu, and task templates (described in the earlier project configuration plan) are out of scope and planned as future features of the same module.
- The priority star keeps precedence over the configuration sort (confirmed at plan review): starred tasks stay on top, and high-value then deadline apply within the starred and unstarred groups. Tasks with the same priority, high-value status and deadline are shown most recently created first.
- The default order replaces the manual position used by the standard order in the views in scope. As a result, **dragging a task to a new position inside a task board column will not keep that position** (known limitation, accepted). Moving a task to another stage still works.
- The property label is exactly "มูลค่าโครงการ"; the label itself is not configurable in this version.
- "Administrator" means a user with the system settings right; the threshold lives with the other Project settings.
- Project value and high-value status are re-evaluated immediately only when a task's "มูลค่าโครงการ" value changes, by editing it or by moving the task to another project (confirmed at plan review). Changing the threshold or a project's property definitions does not re-evaluate tasks automatically; the administrator runs the recalculation, or each task is updated when its value is next edited.
- Accepted limitation: after a property definition change and before the recalculation, the displayed project value may already reflect the change while the high-value status (and therefore the order and the "High Value" filter) does not.
- There is no special integration with the project access module (spec 009) and that module is not changed (confirmed at plan review: "if a user cannot see the project value, that is fine"). Without it installed, every user who can see a task sees its project value; User Story 6 applies only when spec 009 is installed.
- Monetary values are compared without currency conversion; all project values are assumed to be in Thai baht.
- A user who cannot see the amount may still be able to tell that a task is high-value, from its position in the sorted list, from the "High Value" filter, or through technical access to the high-value status; this is accepted (confirmed at plan review), since the sort is the requested behaviour and the amount itself is not shown.
- The default order applies when a user opens a view; any sort chosen by clicking a column heading lasts only for that view session.
