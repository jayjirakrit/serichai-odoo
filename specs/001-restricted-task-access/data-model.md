# Phase 1 Data Model: Restricted "All Tasks" Access (serichai_project_security)

This module introduces **no new persistent models**. It composes existing Odoo `project` models
via security/view configuration. The entities below are the existing records this module reads,
constrains, or extends — captured for traceability against the feature spec's Key Entities section.

## Entities

### Restricted Role (new `res.groups` record)

- **Odoo model**: `res.groups`
- **New record**: `group_project_task_list_only` — "Task List Viewer (Production Planning Only)"
- **Category**: `privilege_id` set to `project.res_groups_privilege_project` — the same privilege
  `project.group_project_user` and `project.group_project_manager` use. This makes the role appear
  as a selectable option in the "Project" access-rights dropdown on the user form (Settings → Users
  → Access Rights tab), alongside "No" / "User" / "Administrator", rather than being invisible
  outside Settings → Technical → Groups. `sequence` is `5` (below `group_project_user`'s `10` and
  `group_project_manager`'s `20`), so it reads as the lowest Project level in that dropdown.
  In this Odoo 19 build, `res.groups.category_id` (the field the Odoo-18-era source document
  assumed) has been replaced by `privilege_id` (→ `res.groups.privilege` → `category_id`); the
  original design used no `privilege_id` at all (the pattern for a purely technical/hidden group,
  e.g. `hr_recruitment.group_applicant_cv_display`), but this was changed on request so
  administrators could assign the role through the normal Users UI instead of the technical Groups
  list. Because this role is **not** part of `group_project_user`/`group_project_manager`'s implied
  hierarchy, the privilege dropdown's single-select behavior makes it mutually exclusive with
  them — picking this option automatically clears User/Administrator for that user (and vice
  versa), which enforces the "must not hold both the restricted role and a broader project role"
  assumption through the UI itself, rather than relying on an administrator to remember it.
- **Relationships**:
  - Does **not** inherit `project.group_project_user` or `project.group_project_manager` — kept
    fully independent so it never gains their broader permissions (this is the entire point of the
    restriction; see spec Assumptions on administrators keeping role assignment exclusive).
  - **Implies `base.group_user`** via `implied_ids` (following the precedent in
    `hr_recruitment.group_hr_recruitment_interviewer`), so assigning this one group is sufficient
    to grant baseline internal-user login access — no separate `base.group_user` assignment needed.
    This grants no project permissions beyond what this module explicitly adds.
- **Validation rules**: None beyond Odoo's standard `res.groups` constraints. Membership is managed
  by administrators via Settings → Users (out of this module's data).

### Project Task (existing `project.task` model — extended, not modified in shape)

- **Fields relevant to this feature**: `stage_id` (many2one → `project.task.type`, used for
  filtering), `tag_ids` (many2many → `project.tags`, hidden from the restricted list), `project_id`
  (many2one → `project.project`, needed for read access since list/kanban context references it).
- **Behavior added by this module** (not a schema change): `get_view()` is extended so that, for
  users holding **only** the restricted role, requesting `view_type='form'` raises `AccessError`
  instead of returning a form view. No fields are added or altered on this model.
- **Access control added**:
  - `ir.model.access.csv` row granting the restricted role `perm_read=1`,
    `perm_write=0`, `perm_create=0`, `perm_unlink=0`.
  - `ir.rule` (global, conditional `domain_force`) restricting visible rows to
    `stage_id.name = 'วางแผนการผลิต'` for members of the restricted role only, no-op for everyone
    else — see research.md §5 for why this must be global rather than group-scoped.

### Project (existing `project.project` model — read-only access grant only)

- **Why involved**: the task list/kanban context and `project_id` field require read access to the
  parent project record for rendering; no project-level restriction is requested by the spec beyond
  read access.
- **Access control added**: `ir.model.access.csv` row granting the restricted role `perm_read=1`,
  `perm_write=0`, `perm_create=0`, `perm_unlink=0`. No `ir.rule` added — the task-level stage rule
  already scopes which tasks (and thus which projects appear via `project_id`) are visible; no
  additional project-level filtering is specified.

### Task Stage (existing `project.task.type` model — referenced by name, not modified)

- **Why involved**: the filtering criterion for FR-003. No changes to this model; its `name` field
  value `"วางแผนการผลิต"` is referenced literally in the `ir.rule` and the restricted action's
  domain.
- **Data integrity note** (carried from spec Assumptions): this module does not create or manage
  this stage record — it must already exist in the target database with this exact name. If renamed,
  the domains in this module must be updated to match (documented as a known coupling, not a runtime
  configuration option, per the source spec's own scope).

### All Tasks View (new `ir.ui.view` + `ir.actions.act_window` records)

- **New records**:
  - `view_task_list_restricted` (`ir.ui.view`, inherits `project.view_task_tree2`): sets
    `column_invisible="1"` on `tag_ids`; sets `open_form_view="false"` on the list root as a UI-level
    defense-in-depth measure (see research.md §3–4 for why this alone is insufficient).
  - `action_task_all_restricted` (`ir.actions.act_window`): `res_model=project.task`,
    `view_mode="list"` only, `view_id` = the view above, `domain=[('stage_id.name', '=',
    'วางแผนการผลิต')]`, `group_ids` = the new restricted role only.
- **Relationships**: The action is the only entry point the restricted role is granted to
  `project.task`; it is not reachable by any other group (mirrors the existing unrestricted
  `action_view_all_task`, which remains untouched and fully available to manager/user roles).

### Project App Navigation (existing `ir.ui.menu` records — `group_ids` field modified)

- **Existing records whose `group_ids` this module changes** (see research.md §2 for the exact
  before/after semantics of each):
  - `project.menu_main_pm` — additively grants the new restricted role (keeps existing groups).
  - `project.menu_projects`, `project.menu_project_report`, `project.menu_project_config`,
    `project.menu_project_management_all_tasks` — explicitly whitelisted to
    `project.group_project_manager` / `project.group_project_user` only (replace semantics),
    ensuring the new restricted role never sees them.
- **New record**: `menu_task_all_restricted` (`ir.ui.menu`), parented under
  `project.menu_project_management` ("Tasks"), pointing at `action_task_all_restricted`,
  `groups="serichai_project_security.group_project_task_list_only"` only.

## State / lifecycle notes

None of the above involve a state machine or record lifecycle — this feature is purely an access
and view-composition layer over existing, unmodified `project` data. No migrations, no new tables,
no computed/stored fields.
