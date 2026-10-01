# Implementation Plan: Expanded Task Access for Product Development Project

**Branch**: `feat/006-product-dev-task-access` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-product-dev-task-access/spec.md`

## Summary

`group_project_task_list_only` (the "Task List Viewer (Production Planning Only)" role in
`serichai_project_security`) is currently read-only and list-only for `project.task` — no
form access, no write, no create/unlink, on every project. This feature carves out one named
exception: for tasks belonging to a single, administrator-pinned `project.project` record
(intended to be "Product Development"), members of that role gain the ability to open the
task form and edit fields on *existing* tasks. Create and delete stay blocked everywhere,
including in the pinned project. Every other project keeps today's behavior unchanged.

The pinned project is stored as a system parameter (configurable via Settings, no code
change/redeploy needed to repoint it), and is referenced by record — never by matching the
project's display name — so a rename doesn't drop the grant and a future unrelated project
reusing the name "Product Development" doesn't inherit it.

## Technical Context

**Language/Version**: Python 3.12 (repo `.venv`), Odoo 19.0 ORM/ORM-XML

**Primary Dependencies**: Odoo core `project` addon (`project.task`, `project.project`,
`res.config.settings`); the existing `serichai_project_security` addon being extended

**Storage**: PostgreSQL via the Odoo ORM; the pinned project reference is stored as an
`ir.config_parameter` system parameter (`serichai_project_security.expanded_access_project_id`),
edited through a `res.config.settings` field — no new table needed

**Testing**: Odoo `TransactionCase` suite (extends the existing
`tests/test_access_restriction.py` pattern), run via
`--test-enable --stop-after-init -u serichai_project_security`

**Target Platform**: Odoo 19.0 server (Linux) + standard Odoo web client

**Project Type**: Odoo addon (backend models + security data + views) — single-module change,
not a web/mobile split

**Performance Goals**: N/A — this adds one indexed-field equality comparison to record-rule
evaluation for a single group; no measurable overhead

**Constraints**: Must not change behavior for any project other than the pinned one; the pinned
project must be repointable by an administrator without a code deploy; create/unlink must stay
blocked everywhere, including the pinned project

**Scale/Scope**: One restricted group, one pinned project at a time, one company database
(`serichai-db`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` in this repo is still the unfilled template (no principles
have been ratified) — there are no project-specific gates to evaluate against. No violations
to justify; **PASS** (vacuously).

*Post-Phase-1 re-check*: unchanged — the constitution is still the unfilled template after
research/design; **PASS** (vacuously).

## Project Structure

### Documentation (this feature)

```text
specs/006-product-dev-task-access/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

(No `contracts/` directory: this feature exposes no external API/service interface — it is
entirely internal to the Odoo ORM/security layer of one addon. See research.md Decision 4.)

### Source Code (repository root: `serichai-odoo/serichai_project_security/`)

```text
serichai_project_security/
├── models/
│   ├── project_task.py              # MODIFY: add is_expanded_access_task computed+searchable
│   │                                 #   field, _get_expanded_access_project_id() helper;
│   │                                 #   drop the blanket "form" AccessError (now conditional
│   │                                 #   via the dedicated action + view, not this method)
│   ├── res_config_settings.py       # NEW: Many2one settings field -> project.project,
│   │                                 #   backed by config_parameter
│   └── __init__.py                  # MODIFY: import res_config_settings
├── security/
│   ├── ir.model.access.csv          # MODIFY: perm_write 0 -> 1 for
│   │                                 #   access_project_task_restricted (create/unlink stay 0)
│   └── ir_rule.xml                  # MODIFY: add rule_task_write_pinned_project
│                                     #   (perm_write only, domain on is_expanded_access_task)
├── views/
│   ├── project_task_views.xml       # MODIFY: add action_task_product_development_restricted
│   │                                 #   (domain-filtered list, form-openable) +
│   │                                 #   menu_task_product_development_restricted
│   └── res_config_settings_views.xml # NEW: expose the pinned-project field in Settings
├── __manifest__.py                  # MODIFY: add the new data/view file to `data`
└── tests/
    └── test_access_restriction.py   # MODIFY: replace the "form always denied" assertion with
                                      #   project-scoped write/open assertions (see quickstart.md)
```

**Structure Decision**: Everything lives inside the existing `serichai_project_security`
addon (`serichai-odoo/serichai_project_security/`) — this is an extension of that module's
existing security model and views, not a new addon. No `contracts/`, `frontend/`, or
`backend/` split applies; this is a single-addon Odoo change.

## Complexity Tracking

*No constitution violations — table intentionally omitted.*
