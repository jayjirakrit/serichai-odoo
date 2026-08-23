# Phase 0 Research: Task Property Group Visibility

All Technical Context items were resolvable from the existing codebase and the prior planning conversation with the user — no items are left as `NEEDS CLARIFICATION`. This document records the key technical decisions and why the alternatives were rejected.

## Decision 1: Where to enforce the restriction

**Decision**: Override `read()` on `project.task` in `serichai_project_security/models/project_task.py`, post-processing the `task_properties` value in the returned records to drop restricted entries the current user isn't permitted to see.

**Rationale**: Confirmed by reading `odoo/addons/web/models/models.py:109` (`web_read`) — the web client's `web_read()` method (used by every form/list/kanban/search rendering) calls `self.read(fields_to_read, load=None)` internally (line 117) and does no additional per-field post-processing of `task_properties` beyond what `read()` already returns. Overriding `read()` therefore covers `web_read()` (the UI), direct RPC/API `read()` calls, and any other code path that goes through the ORM's standard read, with a single override — exactly matching FR-002's "every place task properties are displayed or returned."

**Alternatives considered**:
- *Override the field's compute/`convert_to_read_multi` by subclassing `fields.Properties`*: would require redeclaring `task_properties` with a custom Field subclass and touching semantics documented in `odoo/odoo/orm/fields_properties.py`. Rejected — heavier, closer to core internals than needed, and the plan's constraint is to avoid touching Properties JSON-schema internals.
- *Add a `groups` key to the property definition itself (native schema extension)*: requires overriding `_additional_allowed_keys_properties_definition`/`_validate_properties_definition` on `base` and new frontend widget work in `property_definition.js`. Rejected in the earlier planning session in favor of the simpler mapping-model approach (already an approved decision, not re-litigated here).
- *Filter in `search_read` only*: incomplete — `web_read` (used for form view display) doesn't go through `search_read`, so this would miss form-view rendering. Rejected.

## Decision 2: Visibility-rule storage model

**Decision**: New model `project.task.property.access` with `property_string` (Char, required) and `group_ids` (Many2many `res.groups`, required), stored as ordinary `ir.model.data`-tracked records, managed through a standard list/form view.

**Rationale**: Matches the approach already agreed with the user (Option A from the prior planning session): no core schema changes, plain Odoo model + view + access rights, consistent with how the rest of `serichai_project_security` is built (`security_groups.xml`, `ir.model.access.csv`, `ir_rule.xml` all use stock Odoo security primitives).

**Alternatives considered**: See Decision 1's second alternative — same rejection rationale (native schema extension is heavier and was already decided against).

## Decision 3: Matching mechanism

**Decision**: For each record's `task_properties` read value (a list of dicts, each containing a `'string'` key — confirmed via `Properties.convert_to_read_multi`/`_dict_to_list` in `odoo/odoo/orm/fields_properties.py:200-226,619-637`), for every dict whose `'string'` exactly matches an active `project.task.property.access.property_string`, remove that dict from the list unless `self.env.user` is a member of at least one group in that rule's `group_ids`.

**Rationale**: Directly implements FR-002/FR-004/FR-005 from the spec — exact label match, inclusive-OR group membership, read-only. Property dicts with no matching rule pass through untouched (FR-003).

**Alternatives considered**:
- *Match by property `name` (the internal key, e.g. `'3adf37f3258cfe40'`) instead of `string`*: more stable across renames, but the spec explicitly scopes this feature to label-based matching (documented as an accepted limitation in the spec's Assumptions/Edge Cases) since the user asked to "filter by string field" — not changed here.

## Decision 4: Who can manage visibility rules

**Decision**: Restrict create/write/unlink (and read, for configuring) on `project.task.property.access` to `project.group_project_manager` (confirmed at `odoo/addons/project/security/project_security.xml:18` as the standard "Project / Administrator" group already used elsewhere in this deployment).

**Rationale**: Matches FR-008 ("administrator-level project configuration access") and the spec's Assumptions ("consistent with how other project configuration areas are restricted today"). `project.group_project_manager` is the existing, already-installed group for exactly this level of access — no new group needs to be created for this feature.

**Alternatives considered**:
- *New dedicated group just for this feature*: unnecessary indirection for a small, single-purpose config screen; rejected to keep scope minimal, consistent with CLAUDE.md's guidance against unrequested abstraction.

## Decision 5: Performance approach

**Decision**: No caching layer. On each `read()` call, load all `project.task.property.access` records once per call (small table, expected to hold a handful of rows) and filter in Python.

**Rationale**: Scale/Scope is a single Odoo instance with a small number of visibility rules; the existing `read()` override pattern in this addon (`get_view()` in `project_task.py`) does no caching either. An `ir.model` read of a small table per `read()` call is negligible next to the rest of the ORM read pipeline. Introducing `ormcache` invalidation logic would add complexity not justified by FR-007's "no restart required" requirement, which plain per-call reads already satisfy trivially.

**Alternatives considered**: `@tools.ormcache` on a helper that returns `{property_string: group_ids}`, invalidated on write to the rule model. Rejected as premature optimization for this scale.

## Decision 6: Testing approach

**Decision**: `odoo.tests.common.TransactionCase`, run via `--test-enable --stop-after-init -u serichai_project_security`, in a new `tests/test_task_property_access.py` file mirroring the structure and naming conventions already used in `tests/test_access_restriction.py` (per-test setup of `restricted_user`/`control_user`, explicit group assignment, assertions on `.read()` / `.task_properties` output).

**Rationale**: Consistency with the existing test suite in the same addon; no new testing framework or tooling needed.
