# Feature Specification: Task Property Group Visibility

**Feature Branch**: `002-task-property-access`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User description: "Add group-based visibility for individual properties inside the task_properties field on project.task, so that specific user groups can be restricted from seeing certain properties while everyone else with normal task access still sees the rest of the Properties widget. Properties are identified by their displayed label (string). Administrators define, per property label, which groups may see it; users outside those groups never see that property anywhere task properties are shown. Enforcement is read-only in this iteration — writing to a hidden property is not blocked. Properties with no configured rule remain visible to everyone, as today."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Restrict a sensitive property to specific groups (Priority: P1)

An administrator wants a specific task property (for example, a property showing budget or client-sensitive information) to be visible only to certain user groups, while the rest of the task's properties and general task access remain unchanged for everyone else.

**Why this priority**: This is the core value of the feature — without it, there is no way to selectively hide a sensitive property, which is the entire reason the feature exists.

**Independent Test**: Can be fully tested by configuring one visibility rule restricting a named property to a single group, then confirming a user in that group sees the property and a user outside it does not, anywhere task properties are displayed.

**Acceptance Scenarios**:

1. **Given** a property labeled "Client Budget" is restricted to the "Finance" group, **When** a user who is a member of "Finance" opens a task that has this property, **Then** they see "Client Budget" and its value as normal.
2. **Given** the same restriction, **When** a user who is not a member of "Finance" opens the same task (list, form, kanban, or search), **Then** "Client Budget" does not appear anywhere in that task's properties for them.

---

### User Story 2 - Unrestricted properties stay visible to everyone (Priority: P2)

Any property that has no visibility rule configured for it must keep behaving exactly as it does today — visible to anyone who already has normal access to the task.

**Why this priority**: This guarantees the feature is additive and safe to roll out — it must not accidentally hide properties nobody asked to restrict, and it must not change behavior for tasks/projects that never use this feature.

**Independent Test**: Can be fully tested by opening a task that has properties but no visibility rules configured at all, from multiple user accounts with different group memberships, and confirming all of them see identical property lists.

**Acceptance Scenarios**:

1. **Given** no visibility rule exists for the property "Priority Level", **When** any user with normal task access opens a task containing that property, **Then** they see "Priority Level" exactly as they do today.
2. **Given** a visibility rule exists for one property ("Client Budget") but not for others on the same task, **When** any user opens that task, **Then** only "Client Budget" is subject to filtering — every other property is unaffected.

---

### User Story 3 - Administrator manages visibility rules independently (Priority: P3)

An administrator can create, edit, and remove property visibility rules through a dedicated configuration screen, separate from the flow of defining the properties themselves, and changes take effect immediately.

**Why this priority**: Without ongoing management, the feature would only be usable as a one-time setup; administrators need to adjust restrictions over time as sensitive properties are added, renamed, or reclassified.

**Independent Test**: Can be fully tested by creating a rule and confirming it takes effect on the next read, then deleting it and confirming the property becomes visible to everyone again — without any system restart.

**Acceptance Scenarios**:

1. **Given** an administrator creates a new rule mapping "Client Budget" to the "Finance" group, **When** the rule is saved, **Then** the restriction applies the next time any user reads a task with that property, with no restart or delay.
2. **Given** an existing rule restricting "Client Budget", **When** an administrator deletes that rule, **Then** "Client Budget" becomes visible to all users again, as if it had never been restricted.

---

### Edge Cases

- What happens when two properties on different projects share the exact same label, but only one should be restricted? Both are affected identically — rules match by label text, not by a specific property's origin, so identically-labeled properties elsewhere are restricted together. This is a known limitation, not a defect.
- What happens when a user belongs to multiple groups, only one of which is permitted by the rule? The property is visible — a user needs to match at least one permitted group, not all of them.
- What happens when a property's label is renamed after a rule was created for the old label? The rule no longer matches anything (it was tied to the old label text), so the property becomes visible to everyone again until a new or updated rule is created for the new label.
- What happens when a rule is configured for a label that doesn't currently match any existing property? The rule has no visible effect until a property with that exact label exists.
- What happens when a restricted property is accessed through means other than the standard task views (e.g., bulk data export/import, reporting)? Any read path that returns task property values is expected to respect the same restriction; this is covered by FR-002.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow administrators to create, edit, and delete visibility rules, each specifying a task property's label and one or more user groups permitted to view it.
- **FR-002**: System MUST hide a restricted task property from any user who is not a member of at least one permitted group, in every place task properties are displayed or returned (form view, list view, kanban view, search, and any other read of task property data).
- **FR-003**: System MUST continue showing task properties that have no matching visibility rule to all users who already have standard access to the task, unchanged from current behavior.
- **FR-004**: System MUST grant visibility to a restricted property for any user belonging to at least one of the rule's permitted groups (permitted groups combine inclusively, not all-required).
- **FR-005**: System MUST match a visibility rule to a property using an exact match of the property's current displayed label; a rule does not automatically follow a property if its label is later changed.
- **FR-006**: Visibility rules MUST NOT restrict a user's ability to edit or save a property's value in this iteration — only visibility on read is enforced.
- **FR-007**: A newly created, edited, or deleted visibility rule MUST take effect on the next read, without requiring any system restart or reconfiguration.
- **FR-008**: Only users with administrator-level project configuration access MUST be able to create, edit, or delete visibility rules; standard task users MUST NOT be able to modify them.

### Key Entities

- **Task Property Visibility Rule**: Represents a restriction on one task property, identified by its displayed label; associated with one or more user groups permitted to view it. Created and managed by administrators.
- **Task Property**: Existing concept — a custom, per-task field defined within a project, shown to users as part of that task's "Properties" section, each with a displayed label.
- **User Group**: Existing concept — an existing grouping of users used elsewhere in the system to grant or restrict access.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can define a new property visibility rule in under 1 minute using the provided configuration screen.
- **SC-002**: 100% of task property reads (form, list, kanban, search, and other data reads) correctly exclude a restricted property for users outside its permitted groups.
- **SC-003**: Users belonging to a permitted group see 100% of the properties they are authorized for, with zero unintended hiding of unrestricted properties.
- **SC-004**: Tasks, projects, and users that never use a visibility rule show zero behavior change compared to before this feature existed.

## Assumptions

- Rules are matched by a property's current displayed label rather than a stable internal identifier; renaming a property requires updating or recreating its rule to keep the restriction attached.
- Rules apply wherever a property with the matching label appears, rather than being scoped to one specific project — if two properties in different projects share a label, a rule for that label affects both.
- Only read-time visibility is restricted in this iteration; saving/writing a value for a restricted property is not blocked or specially validated.
- Administrative access to manage visibility rules is limited to users who already hold project administrator/manager-level access, consistent with how other project configuration areas are restricted today.
- This feature extends existing task management functionality without modifying the underlying platform's core behavior for users and projects that don't configure any rules.
