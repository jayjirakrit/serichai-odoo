# Data Model: serichai_project_access

Module `serichai_project_access` (depends: `project`). No data is stored per user; effective
access is computed (research D4).

## project.access.profile ("Project Access Group")

| Field | Type | Notes |
|---|---|---|
| `name` | Char, required | Department name (FR-003) |
| `active` | Boolean, default True | Inactive profile grants nothing (FR-001, edge cases) |
| `group_ids` | M2M `res.groups`, required | Rel `project_access_profile_group_rel`. Constraint: none of the forbidden groups (research D5) |
| `line_ids` | O2M `project.access.line` (`profile_id`) | cascade delete |
| `user_ids` | M2M `res.users`, computed, non-stored | Members of `group_ids` (incl. implied), read-only User tab (FR-004) |
| `project_names` | Char/tags via related on lines | List column "Project": `project_ids` of all lines (computed M2M non-stored) |

Create/write(`group_ids`, `active`)/unlink → `_sync_restricted_group(affected_groups)` (only the
groups of the changed profiles) and `registry.clear_cache()`.

## project.access.line

| Field | Type | Notes |
|---|---|---|
| `profile_id` | M2O profile, required, ondelete cascade | |
| `project_ids` | M2M `project.project`, required | Rel `project_access_line_project_rel`. Same project at most once per profile (Python constraint, FR-007) |
| `access_level` | Selection `read`/`write`, default `read` | |
| `task_access` | Selection `list`/`detail`, default `list` | Computed stored, readonly=False: forced to `detail` for `write` (FR-008) |
| `stage_ids` | M2M `project.task.type` | Rel `project_access_line_stage_rel`. Empty = all stages. Read only (FR-006) |
| `hidden_property_label_ids` | M2M `project.access.property.label` | Rel `project_access_line_property_label_rel`. Shown as tags in the line form. Read only |
| `hidden_property_names` | Text, computed stored, inverse | One label per line = the tag names. Writing the text creates/reuses tags, writing tags rewrites the text; the resolver, warning and migration hook read/write this text. Matched with `norm_label` (NFKC, inner spaces collapsed, trim, casefold) |
| `available_property_labels` | Char, computed | Labels defined on the selected projects, shown as a hint under the tags |
| `stages_exhausted` | Boolean, stored, default False | Set by `project.task.type` ondelete when every selected stage was deleted: the M2M rows cascade, which would otherwise turn the line into "all stages" (fail open, spec edge case). Resolver then grants no stage. Reset when `stage_ids` is written by an admin |
| `warning_message` | Text, computed, non-stored | Unmatched names + `followers`/`invited_users` projects (FR-009) |

`project.access.property.label` (v1.1.0): `name` (Char, required), `name_norm` (computed stored,
`unique`); `name_create` reuses an existing label by normalised name; ACL: Project manager CRUD, nobody
else. Renaming/deleting a label clears the registry cache (resolver). Migration `migrations/1.1.0`
turns existing text values into tags.
Management screen: `line_count` ("Used in lines", computed non-stored) feeds an editable list/form under
Project > Configuration > Hidden Property Labels (managers only). `unlink` recomputes the text mirror of the
lines that used the label (the M2M rows cascade in SQL), renaming recomputes it through the `name` dependency;
both clear the registry cache.

Rules: for `write` lines `stage_ids`, `hidden_property_label_ids`, `hidden_property_names` and `stages_exhausted` are cleared on
every create/write (and ignored by the resolver); moving write -> read resets `task_access` to `list`.
`warning_message` also warns when `stages_exhausted` is set. Sequence handle for ordering only.

## Control group

`serichai_project_access.serichai_project_access_group_restricted`, implies `base.group_user`, privilege
Project. Implied by every group listed in an active profile. Not assignable meaningfully by hand
(help text says so). Plus `group_production_planning` created by the migration hook only.

## Computed search fields (non-stored, no table change)

| Model | Field | Meaning for restricted user | Unrestricted |
|---|---|---|---|
| `project.project` | `access_can_read` | project granted by any line | always true |
| `project.task` | `access_task_visible` | project granted and stage allowed | always true |
| `project.task` | `access_task_writable` | project granted with Write | always true |
| `project.task` | `access_task_detail` | visible and (Write or merged detail) | always true |

## Effective access (cache value, per user)

`dict[project_id] -> Grant(write: bool, detail: bool, stage_ids: frozenset|None,
hidden: frozenset[str])`; `None` for an unrestricted user. Merge (FR-018): `write` = any write;
`detail` = write or any detail; `stage_ids` = union, `None` if any contributing line has no
stages or is Write; `hidden` = intersection over contributing lines, empty if any Write.

## Removed / migrated

`project.task.property.access`, `res.config.settings` fields, the config parameter and
`group_project_task_list_only` disappear with `serichai_project_security` after migration.
