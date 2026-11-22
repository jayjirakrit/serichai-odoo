# Plan - 013 Task Confidential Information

**Module**: `serichai_project_access` (installed in `serichai-db`; `serichai_project_security` is not).

## Decisions
| Decision | Choice | Why |
|---|---|---|
| Access control | Field-level `groups='project.group_project_user'` | ORM enforces read, write, search, group-by, export, `fields_get`; the view node is stripped for non-members. Project Administrator implies Project User. |
| New group | None | Requested: reuse existing project groups. |
| Property-access mechanism | Not reused | `project.task.property.access` only filters `task_properties` labels at read time, has no HTML type, and does not block writes. |
| Copy / tracking / history | `copy=False`, no `tracking`, not in `_get_versioned_fields` | Content must not reach duplicates, chatter or the unprotected `html_field_history`. |
| Portal | Not added to `PROJECT_TASK_READABLE_FIELDS` | Portal and project-sharing users never see it. |
| Editor | `type="html"`, `resizable: false`, no `collaborative` | Collaboration needs the history mixin, which is deliberately not used. |

## Changes
- `models/project_task.py`: add `confidential_description` (Html).
- `views/project_task_views.xml`: record `view_task_form_confidential_description` inheriting `project.view_task_form2`; xpath `//page[@name='description_page']//field[@name='description']`, position `before`; separator + field (both with the group) + "General" separator.
- `tests/test_confidential_description.py` and `tests/__init__.py`.

## Risks
- Code calling `read()` on the field as a user without the group raises AccessError; use sudo or avoid it.
- A user holding Project User sees the field even if a Project Access Group otherwise restricts them.
- New nullable column; deployment needs `-u serichai_project_access`.
