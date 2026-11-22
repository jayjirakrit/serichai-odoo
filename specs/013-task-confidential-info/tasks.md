# Tasks - 013 Task Confidential Information

- [x] T001 Add `confidential_description` Html field to `serichai_project_access/models/project_task.py` (groups, `copy=False`)
- [x] T002 Add inherited form view `view_task_form_confidential_description` to `serichai_project_access/views/project_task_views.xml`
- [x] T003 Add `tests/test_confidential_description.py` and register it in `tests/__init__.py`
  - Project User and Project Administrator read/write (FR-001)
  - Internal user without `project.group_project_user` gets AccessError on read and write (FR-002)
  - Form arch contains the field only for Project User (FR-002)
  - Duplicate leaves the field empty (FR-004)
- [x] T004 Add the `serichai_project_access` section and spec link to `CLAUDE.md`
- [x] T005 Run gate: `-i serichai_project_access --test-enable --test-tags /serichai_project_access` (80 tests, 0 failed)
- [ ] T006 Deploy: stop the server, run `-u serichai_project_access -d serichai-db`, restart, hard-refresh the browser
- [ ] T007 Manual check as Project User, Project Administrator and a department user without the project group (Description tab shows the section only for the first two)

## Out of scope
Thai translations (the addon has no `i18n/`), field history/versioning, portal exposure.
