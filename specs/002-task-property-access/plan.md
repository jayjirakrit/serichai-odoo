# Implementation Plan: Task Property Group Visibility

**Branch**: `002-task-property-access` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-task-property-access/spec.md`

## Summary

Administrators need to restrict certain `project.task` Properties entries (identified by their displayed label) to specific user groups, while all other properties and normal task access stay unchanged. Implementation extends the existing `serichai_project_security` addon with a new configuration model (`property_string` → `group_ids`) and a `read()` override on `project.task` that strips restricted properties out of the `task_properties` value for users not in a permitted group. Enforcement is read-only for v1; no core Odoo files are modified.

## Technical Context

**Language/Version**: Python 3.12 (repo `.venv`), Odoo 19.0 ORM

**Primary Dependencies**: Odoo `project` addon (provides `project.task`/`project.project` and the `task_properties` Properties field); no new third-party dependencies

**Storage**: PostgreSQL via Odoo ORM (new `ir.model` table for the visibility-rule model, standard Odoo migration-free `-u` module upgrade)

**Testing**: Odoo `odoo.tests.common.TransactionCase`, run via `--test-enable --stop-after-init -u serichai_project_security`, matching the existing `tests/test_access_restriction.py` style already in this addon

**Target Platform**: Server-side Odoo addon (Linux), affects backend web client rendering of `project.task` (form/list/kanban/search) and any API/read consumers

**Project Type**: Odoo addon (single addon extension, no separate frontend/backend split)

**Performance Goals**: No dedicated targets beyond not measurably slowing task reads; filtering runs in-memory over a small per-task properties list (typically single-digit count of properties) plus one lookup of active visibility rules per read batch — negligible compared to existing ORM read cost

**Constraints**: Must not modify vendored Odoo core under `odoo/`; must not extend the core Properties JSON schema (`PropertiesDefinition.ALLOWED_KEYS`) or touch `odoo/odoo/orm/fields_properties.py`; enforcement confined to this addon

**Scale/Scope**: Single Odoo instance (`serichai-db`), scoped to the `project.task` model's `task_properties` field only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` in this repository is still the unfilled template (`[PROJECT_NAME] Constitution` with bracketed placeholders throughout) — no project-specific principles or gates have been ratified. There is nothing to check against; this gate is treated as **N/A / pass by default**. General repository conventions from `CLAUDE.md` (avoid modifying vendored `odoo/`, follow existing addon layout, avoid unrequested scope) are already reflected in the Constraints above and in the design that follows.

**Post-Phase-1 re-check**: No changes to this status — `research.md` and `data-model.md`/`contracts/` (Phase 1 outputs) introduce no new dependencies, no core-file modifications, and no scope beyond the existing addon, so the gate remains N/A / pass.

## Project Structure

### Documentation (this feature)

```text
specs/002-task-property-access/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
serichai-odoo/serichai_project_security/     # existing addon (own nested git repo), extended in place
├── __manifest__.py                          # add new data files to 'data' list
├── models/
│   ├── __init__.py                          # add import for new model module
│   ├── project_task.py                      # extend: add read() override alongside existing get_view() override
│   └── project_task_property_access.py      # NEW: project.task.property.access model
├── security/
│   ├── ir.model.access.csv                  # add access rows for the new model
│   └── security_groups.xml                  # unchanged (reuses existing project admin/manager groups)
├── views/
│   └── project_task_property_access_views.xml   # NEW: list/form view + menu for managing rules
└── tests/
    └── test_task_property_access.py         # NEW: TransactionCase tests, mirrors test_access_restriction.py style
```

**Structure Decision**: Everything lives inside the existing `serichai-odoo/serichai_project_security/` addon (decision already made with the user), following the module's current file layout (`models/`, `security/`, `views/`, `tests/`) rather than introducing a new addon or new top-level directories.

## Complexity Tracking

*No constitution violations — table not applicable.*
