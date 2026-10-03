# Implementation Plan: Open Pinned-Project Tasks from the Restricted "All Tasks" List

**Branch**: `007-all-tasks-pinned-open` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-all-tasks-pinned-open/spec.md`

**Note**: This plan was written after the fact. The design below matches the code that was
already implemented on 2026-10-03, with automated tests passing. `tasks.md` records what was
done and what is still open, which is the manual walkthrough and deploying to `serichai-db`.

## Summary

The "Task List Viewer (Production Planning Only)" role (`group_project_task_list_only`) lands on
**All Tasks**, which until now could open no row at all. The block came from the action having
no `form` view. It did not come from the list's `open_form_view="false"` attribute: the web
client ignores that attribute on non-editable lists (research.md Decision 1).

This feature lets that list open a task's form **only** when the task is in the project pinned
in Settings (spec 006, `is_expanded_access_task`). It works in two layers:

1. **Client.** The action gains a `form` view. A custom list controller
   (`js_class="serichai_restricted_task_list"`) opens only pinned rows. It shows a warning for
   any other row and limits the form pager to pinned rows. Non-pinned rows are muted.
2. **Server.** A guard on `project.task.web_read` refuses a **direct** RPC load of a
   non-pinned task for this role. That covers deep links, the pager, and mail links. List,
   kanban, read_group and co-record reads are untouched (research.md Decisions 2 and 3).

Editing rights come unchanged from spec 006's write rule. Create and delete stay blocked.

## Technical Context

**Language/Version**: Python 3.12 (repo `.venv`), Odoo 19.0. JavaScript ES modules (Odoo 19 web client, OWL).

**Primary Dependencies**: Odoo core `project` and `web` addons (`ListController`, `listView`,
the `notification` service, `odoo.http.request`). Builds on the existing
`serichai_project_security` addon from specs 001, 002 and 006.

**Storage**: N/A. No new fields or tables. It reuses the `ir.config_parameter`
`serichai_project_security.expanded_access_project_id` and the computed, searchable
`project.task.is_expanded_access_task` from spec 006.

**Testing**: Odoo `TransactionCase` (`tests/test_access_restriction.py`). The server guard is
exercised by patching the module-level `request` with a stub whose `params` carry
`model`/`method`. The run command is `--test-enable --test-tags /serichai_project_security
--stop-after-init`. Tests run against a throwaway database so `serichai-db` is not upgraded.

**Target Platform**: Odoo 19.0 server on Linux, plus the standard Odoo backend web client.

**Project Type**: Odoo addon. A single-module change spanning model, views, assets and tests.

**Performance Goals**: N/A. The client check is O(rows) on data that is already loaded. The
server guard costs one `has_group` check and one computed-field read per direct form load.

**Constraints**: The set of listed tasks must not change (FR-007). Regular Project users must
not be affected (FR-008). The guard must not break `web_search_read`, `web_read_group` or
co-record reads, all of which call `web_read` internally. Vendored Odoo core must not be
modified (CLAUDE.md).

**Scale/Scope**: One restricted group, one pinned project, one database (`serichai-db`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template and no principles have been
ratified. There are no project-specific gates, so this **passes** vacuously, the same as in
spec 006. The repo conventions from CLAUDE.md are respected anyway: Odoo core and `muk_web_theme`
are untouched, new assets are registered in `__manifest__.py`, and commits carry no AI attribution.

*Post-Phase-1 re-check*: unchanged. **PASS** (vacuously).

## Project Structure

### Documentation (this feature)

```text
specs/007-all-tasks-pinned-open/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0: decisions 1-5
├── data-model.md        # Phase 1: entities reused, the openability rule
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   └── module-interface.md   # UI and server behaviour contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (`serichai-odoo/serichai_project_security/`)

```text
serichai_project_security/
├── __manifest__.py                         # version 1.1.0, assets → web.assets_backend, description
├── models/
│   ├── project_task.py                     # + _is_restricted_form_load(), web_read() guard
│   └── res_config_settings.py              # help text
├── static/src/views/
│   └── restricted_task_list.js             # NEW: RestrictedTaskListController + view registration
├── views/
│   ├── project_task_views.xml              # restricted list arch + All Tasks action view_mode list,form
│   └── res_config_settings_views.xml       # help text
└── tests/
    └── test_access_restriction.py          # +6 tests
```

**Structure Decision**: Extend the existing addon in place, following the layout already used
by specs 001, 002 and 006. The only new directory is `static/src/views/`, the standard Odoo
location for view JavaScript. Its manifest `assets` entry follows the pattern in
`serichai_inventory_barcode`.

## Complexity Tracking

No constitution violations. Two design choices are documented in research.md for reviewers:

| Choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| Server guard keyed on the top-level RPC method (`request.params`) | `web_read` is called internally by `web_search_read`, `web_read_group`, `web_name_search` and co-record reads, so a blanket guard breaks the list and kanban | A blanket `web_read` or `read` override rejects the list itself (spec 006 research Decision 3) |
| Custom list controller (JS) | Odoo list views have no per-row "can open" attribute | XML only: `open_form_view` is ignored on non-editable lists, and leaving out the form view blocks every row |
