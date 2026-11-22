# 013 - Task Confidential Information

## Goal
A second rich-text area, "Confidential Information", on the Description tab of the
project task form, above the existing "General" description. Only Project User and
Project Administrator can see and edit it.

## Requirements
- FR-001: Project User (`project.group_project_user`) and Project Administrator
  (which implies it) can read and write the field.
- FR-002: Internal users without `project.group_project_user` (e.g. department users reaching tasks through a Project Access Group) cannot read,
  write or see it in the form. No new group is introduced.
- FR-003: Portal and project-sharing users never see it.
- FR-004: The content is not copied on duplicate, not tracked in the chatter and not
  stored in the html field history.

## Design
- `project.task.confidential_description` (Html, `copy=False`,
  `groups='project.group_project_user'`), `serichai_project_access/models/project_task.py`. The ORM enforces the
  group on read, write, search, group-by, export and `fields_get`.
- Form: inherited record `view_task_form_confidential_description` on
  `project.view_task_form2`, inserted before `description` in `description_page`;
  the view post-processing strips the nodes for non-members.
- Not reusing `project.task.property.access`: it only filters `task_properties`
  labels at read time, has no HTML type and does not block writes.

## Acceptance
See `tasks.md` T003 and T007. Plan: `plan.md`.

## Verification
`tests/test_confidential_description.py` in `serichai_project_access` (read/write per role,
AccessError for an internal user without the project group, form arch, copy). Gate:
`-i serichai_project_access --test-enable --test-tags /serichai_project_access`.
The module lives in `serichai_project_access`, not `serichai_project_security`, because the
latter is not installed in `serichai-db`.
