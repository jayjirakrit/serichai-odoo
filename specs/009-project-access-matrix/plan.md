# Implementation Plan: Configurable Project Access by Department

**Branch**: `009-project-access-matrix` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/009-project-access-matrix/spec.md`; technical input `PROJECT_ACCESS_PLAN.md`
(verified and corrected in [research.md](./research.md)).

## Summary

New addon `serichai_project_access` replaces `serichai_project_security`. A configurable model
(`project.access.profile` + `project.access.line`) says which user groups ("departments") get which
projects at Read or Write level, with stages, hidden task properties and list-only/open-detail
per Read line. Enforcement is server-side: global record rules driven by searchable computed
fields over one cached resolver (`res.users._get_project_access`), a `read`/`write` override for
properties, the generalised top-level `web_read` guard, a code-based menu blacklist, and two
small OWL controllers (list, kanban) for greyed rows and warnings. A `post_init_hook` migrates
the old behaviour; the old module is then uninstalled. See [design.md](./design.md) for key code.

## Technical Context

**Language/Version**: Python 3.12, Odoo 19.0; OWL/JS ES modules for two controllers.

**Primary Dependencies**: Odoo `project` (auto-installed `project_todo` assumed present, research D1/D3); `web`
list/kanban controllers; no new third-party libs.

**Storage**: PostgreSQL. Two new tables plus three M2M relation tables (data-model.md). No per-user data.

**Testing**: `TransactionCase` + `new_test_user` (pattern of `serichai_project_security/tests`), `request` patched for the guard; `HttpCase` tour required for greyed rows (T025a). Positive and negative cases per Principle IV.

**Target Platform**: Odoo 19 on Linux, standard backend web client.

**Project Type**: Odoo addon, area `odoo` (fullstack).

**Performance Goals**: Resolver cached per (user, groups); rule evaluation adds one cached dict lookup per query. Domain size is bounded by granted projects.

**Constraints**: No edits to `odoo/` or `muk_web_theme/`; regular Project users unchanged (FR-017, US5-4); `web_search_read`/`read_group` must keep working under the guard; changes visible on next page load (SC-006).

**Scale/Scope**: Tens of users, a handful of departments, tens of projects; one database `serichai-db`.

## Constitution Check

| Principle | Status | Note |
|---|---|---|
| I. Extend, Never Fork | Pass | Only `_inherit`, view inheritance, `patch`/registry controllers; core menu change is one additive group on `project.menu_main_pm`. |
| II. Odoo conventions | Pass | Names per Technology Standards (`<model>_security.xml`, `<module>_groups.xml`, `<model>_rule_<group>` adapted for global rules, see below). |
| III. Security by default | Pass | ACL csv for both new models, server-side rules; `sudo()` only in resolver and group sync, each commented. Guard is not a confidentiality boundary (FR-015, as spec 007). |
| IV. Test what you change | Pass (planned) | Positive/negative tests in design.md "Specs must assert". |
| V. Spec first | Pass | Code traces to FR-001..FR-026. |

Technology Standards notes:
- Rule XML ids are `<model>_rule_access_<perm>` (global rules have no group suffix); documented deviation, no Complexity entry needed.
- "Addons" list in the constitution names `serichai_project_security`; after cutover run `/speckit-constitution` (PATCH) to replace it with `serichai_project_access`, and update `CLAUDE.md`.
- Reference code reused: `serichai_project_security` (groups, `web_read` guard, `js_class`, searchable boolean pattern).

## Contracts

One delta contract: [contracts/module-interface.md](./contracts/module-interface.md) (client controllers <-> server guard, resolver, security record ids). Single area `odoo`, so no cross-area contract is needed.

## Project Structure

### Documentation (this feature)

```text
specs/009-project-access-matrix/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── design.md
├── contracts/module-interface.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
serichai-odoo/serichai_project_access/
├── __init__.py
├── __manifest__.py                     # depends: project; post_init_hook
├── hooks.py                            # migration + menu restore (research D12)
├── models/
│   ├── __init__.py
│   ├── project_access_profile.py
│   ├── project_access_line.py
│   ├── res_users.py                    # _get_project_access resolver + cache
│   ├── project_project.py              # access_can_read, action_view_tasks
│   ├── project_task.py                 # fields, guard, read/write, stage columns
│   └── ir_ui_menu.py                   # _load_menus_blacklist
├── security/
│   ├── serichai_project_access_groups.xml
│   ├── ir.model.access.csv
│   ├── project_project_security.xml
│   └── project_task_security.xml
├── views/
│   ├── project_access_profile_views.xml
│   ├── project_project_views.xml       # restricted kanban + action
│   ├── project_task_views.xml          # restricted list/kanban + actions
│   └── project_access_menus.xml
├── static/src/views/{access_task_list.js,access_task_kanban.js}
└── tests/{test_access_resolver.py,test_access_enforcement.py,test_property_hiding.py,test_detail_guard.py,test_migration.py}
```

**Structure Decision**: one new addon next to the old one in `serichai-odoo/`; both stay
installable until cutover. Already on the addons path of `run_odoo.sh`.

## Complexity Tracking

No Constitution Check violations. Notable complexity, each justified in research.md: global
rules instead of group rules (D1), implied-group sync for automatic restricted status (D5),
a defensive property-write merge (D7).
