# Design: Configurable Project Access by Department

Review aid for the human architect. Not production code; migrations and full tests excluded.
Spec: [spec.md](./spec.md) | Plan: [plan.md](./plan.md) | Findings: [research.md](./research.md)

## Approach

1. Two config models (profile, line) say who gets what. Users are never edited: department =
   the profile's `res.groups`.
2. One cached resolver `res.users._get_project_access()` merges every applicable line into a
   per-project `Grant` (FR-018). `None` means unrestricted.
3. Searchable computed booleans on `project.project` / `project.task` turn grants into domains.
   **Global** `ir.rule`s use them, so they narrow (group rules would widen, research D1).
4. Properties are filtered in `read()`; the open-detail guard is the generalised spec 007
   top-level `web_read` check; menus come from `_load_menus_blacklist`.
5. A `post_init_hook` migrates the old module, which is then uninstalled.

## Decisions

| # | Decision | Why |
|---|---|---|
| 1 | Global rules with search fields, unrestricted users get `Domain.TRUE` | OR/AND semantics, D1 |
| 2 | Restricted status via `implied_ids` sync on department groups | automatic for existing members, FR-017 |
| 3 | Cache key includes `_get_group_ids()`; unlink blocked by rule; no project write rule | FR-016, D3, D2 |
| 4 | Menu blacklist in code, not data overrides | nothing lingers, FR-025 |
| 5 | Project menu = stock project kanban, `action_view_tasks` overridden | no JS, SC-007 |
| 6 | Hook-based migration | `migrations/` never runs on fresh install, D12 |

## Flow

```text
Admin edits profile/line --> clear_cache(); _sync_restricted_group()
All Tasks --> ir.rule access_task_visible --> _get_project_access() (cached) --> Domain
Click row --> controller: access_task_detail ? navigate : warn
Direct link / pager --> web_read RPC --> guard --> AccessError when detail is False
Form load --> read() drops hidden properties; save --> rule access_task_writable
```

## Requirement groups -> key files

| Requirements | Key files |
|---|---|
| FR-001..FR-009 admin | `models/project_access_profile.py`, `project_access_line.py`, `views/project_access_profile_views.xml`, `security/ir.model.access.csv` |
| FR-010..FR-013, FR-015, FR-017, FR-018 | `models/res_users.py`, `models/project_task.py`, `models/project_project.py`, `security/*_security.xml` |
| FR-014 guard + greyed rows | `models/project_task.py`, `static/src/views/access_task_list.js`, `access_task_kanban.js` |
| FR-019..FR-021 navigation | `models/ir_ui_menu.py`, `views/project_access_menus.xml`, `views/project_project_views.xml` |
| FR-022 per-line settings | `project_access_line.py` (M2M `project_ids`) |
| FR-023..FR-026 migration | `hooks.py`, `__manifest__.py` |

## Key snippets

### `models/res_users.py` - resolver

```python
Grant = namedtuple('Grant', 'write detail stage_ids hidden')
# stage_ids: frozenset of allowed ids, None = all stages; hidden: normalised labels

def _norm(names):
    return frozenset(n.strip().casefold() for n in (names or '').splitlines() if n.strip())

class ResUsers(models.Model):
    _inherit = 'res.users'

    @tools.ormcache('self.id', 'self._get_group_ids()')
    def _get_project_access(self):
        """{project_id: Grant}, or None when the user is not restricted (FR-017)."""
        self.ensure_one()
        group_ids = set(self._get_group_ids())
        xmlid = self.env['ir.model.data']._xmlid_to_res_id
        if (xmlid('serichai_project_access.serichai_project_access_group_restricted') not in group_ids
                or xmlid('project.group_project_user') in group_ids):
            return None
        # sudo: users cannot read profiles; only the merged result leaves this method.
        lines = self.env['project.access.line'].sudo().search([
            ('profile_id.active', '=', True), ('profile_id.group_ids', 'in', list(group_ids))])
        grants = {}
        for line in lines:
            write = line.access_level == 'write'
            all_stages = write or not (line.stage_ids or line.stages_exhausted)
            new = Grant(write, write or line.task_access == 'detail',
                        None if all_stages else frozenset(line.stage_ids.ids),
                        frozenset() if write else _norm(line.hidden_property_names))
            for project in line.project_ids.filtered('active'):
                grants[project.id] = self._merge_grant(grants.get(project.id), new)
        return grants

    @staticmethod
    def _merge_grant(old, new):  # FR-018
        if old is None:
            return new
        stages = None if None in (old.stage_ids, new.stage_ids) else old.stage_ids | new.stage_ids
        return Grant(old.write or new.write, old.detail or new.detail, stages, old.hidden & new.hidden)
```

### `models/project_task.py` - search fields, guard, properties, columns

```python
access_task_visible = fields.Boolean(compute='_compute_access_flags',
    search='_search_access_task_visible')
access_task_writable = fields.Boolean(compute='_compute_access_flags',
    search='_search_access_task_writable')
access_task_detail = fields.Boolean(compute='_compute_access_flags',
    search='_search_access_task_detail')

def _compute_access_flags(self):
    grants = self.env.user._get_project_access()
    for task in self:
        g = None if grants is None else grants.get(task.project_id.id)
        ok = grants is None or bool(g and (g.stage_ids is None or task.stage_id.id in g.stage_ids))
        task.access_task_visible = ok
        task.access_task_writable = grants is None or bool(g and g.write)
        task.access_task_detail = ok and (grants is None or g.detail)

@api.model
def _access_domain(self, flag):  # flag: visible | writable | detail
    grants = self.env.user._get_project_access()
    if grants is None:
        return Domain.TRUE
    by_stage = defaultdict(list)
    for pid, g in grants.items():
        if (flag == 'writable' and not g.write) or (flag == 'detail' and not g.detail):
            continue
        by_stage[g.stage_ids].append(pid)
    return Domain.OR(
        Domain('project_id', 'in', pids)
        & (Domain.TRUE if stages is None else Domain('stage_id', 'in', list(stages)))
        for stages, pids in by_stage.items())

def web_read(self, specification):
    if self._access_is_restricted_form_load() and not all(self.mapped('access_task_detail')):
        raise AccessError(self.env._("You are not allowed to open this task."))
    return super().web_read(specification)
```

`_search_access_task_*` call `_search_bool(operator, value, self._access_domain(flag))`, the
old `in`/`not in` boolean normalisation factored into one helper. `_access_is_restricted_form_load`
is the spec 007 method with the test `user._get_project_access() is not None`.

```python
def read(self, fields=None, load='_classic_read'):   # same file
    result = super().read(fields=fields, load=load)
    grants = self.env.user._get_project_access()
    if grants is None or not result or 'task_properties' not in result[0]:
        return result
    for vals in result:
        grant = grants.get(self.browse(vals['id']).project_id.id)
        if grant and grant.hidden and vals.get('task_properties'):
            vals['task_properties'] = [p for p in vals['task_properties']
                                       if (p.get('string') or '').strip().casefold() not in grant.hidden]
    return result

@api.model
def _read_group_stage_ids(self, stages, domain):     # D8: no empty columns for hidden stages
    stages = super()._read_group_stage_ids(stages, domain)
    grants, pid = self.env.user._get_project_access(), self.env.context.get('default_project_id')
    if grants is None or not pid:
        return stages
    grant = grants.get(pid)
    if grant is None:
        return stages.browse()
    return stages if grant.stage_ids is None else stages.filtered(lambda s: s.id in grant.stage_ids)
```

`write()` (defensive, D7): hidden stored property values are merged back on save.

### `models/project_access_profile.py` - group sync

```python
@api.constrains('group_ids')
def _check_group_ids(self):
    if self.group_ids & self._forbidden_groups():   # user, portal, public, system, project groups
        raise ValidationError(self.env._("This group cannot define a department."))

@api.model
def _sync_restricted_group(self):
    # sudo: project managers cannot write res.groups; only the control group is linked to or
    # unlinked from implied_ids of department groups, nothing else is touched.
    restricted = self.env.ref('serichai_project_access.serichai_project_access_group_restricted')
    wanted = self.sudo().search([]).group_ids              # active profiles only
    current = self.env['res.groups'].sudo().search([('implied_ids', 'in', restricted.id)])
    (wanted - current).write({'implied_ids': [Command.link(restricted.id)]})
    (current - wanted - restricted).write({'implied_ids': [Command.unlink(restricted.id)]})

def _after_change(self):          # called from create / write / unlink overrides
    self._sync_restricted_group()
    self.env.registry.clear_cache()
```

### `models/project_access_line.py` - constraints and warnings

```python
task_access = fields.Selection([('list', 'List only'), ('detail', 'Open detail')],
    compute='_compute_task_access', store=True, readonly=False, default='list')
stages_exhausted = fields.Boolean(help="All selected stages were deleted: grant no stage.")

@api.constrains('project_ids', 'profile_id')
def _check_project_unique_in_profile(self):          # FR-007
    for line in self:
        if dupes := line.project_ids & (line.profile_id.line_ids - line).project_ids:
            raise ValidationError(self.env._("%(projects)s already granted in this department.",
                                             projects=', '.join(dupes.mapped('name'))))

@api.depends('access_level')
def _compute_task_access(self):                       # FR-008
    for line in self.filtered(lambda l: l.access_level == 'write'):
        line.task_access = 'detail'

@api.depends('project_ids', 'hidden_property_names', 'access_level')
def _compute_warning_message(self):                   # FR-009
    for line in self:
        known = {_norm_label(p) for d in line.project_ids.mapped('task_properties_definition') for p in d or []}
        unknown = _norm(line.hidden_property_names) - known if line.access_level == 'read' else ()
        blocked = line.project_ids.filtered(lambda p: p.privacy_visibility not in ('employees', 'portal'))
        line.warning_message = '\n'.join(
            [self.env._("No property named '%s'", n) for n in sorted(unknown)]
            + ([self.env._("Visibility may block members: %s", ', '.join(blocked.mapped('name')))]
               if blocked else []))
```

A `project.task.type` ondelete hook sets `stages_exhausted` on lines whose whole `stage_ids`
is being deleted (M2M rows cascade, which would otherwise mean "all stages").

### `models/project_project.py`

```python
access_can_read = fields.Boolean(compute='_compute_access_can_read', search='_search_access_can_read')

def _search_access_can_read(self, operator, value):
    grants = self.env.user._get_project_access()
    granted = Domain.TRUE if grants is None else Domain('id', 'in', list(grants))
    return self._search_bool(operator, value, granted)

def action_view_tasks(self):
    if self.env.user._get_project_access() is None:
        return super().action_view_tasks()
    self.ensure_one()
    action = self.env['ir.actions.act_window']._for_xml_id(
        'serichai_project_access.project_task_action_access_project')
    action.update(display_name=self.name, domain=[('project_id', '=', self.id)],
                  context={'default_project_id': self.id, 'active_id': self.id,
                           'project_kanban': True, 'create': False})
    return action
```

### `models/ir_ui_menu.py`

```python
def _load_menus_blacklist(self):
    res = super()._load_menus_blacklist()
    own = (self.env.ref('serichai_project_access.menu_task_all_access')
           + self.env.ref('serichai_project_access.menu_project_access'))
    if self.env.user._get_project_access() is None:
        return res + own.ids                        # project users keep the standard menus only
    root = self.env.ref('project.menu_main_pm')
    return res + (self.sudo().search([('id', 'child_of', root.id)]) - root - own).ids
```

### `security/project_task_security.xml` (+ ACL csv)

```xml
<record id="project_task_rule_access_read" model="ir.rule">
    <field name="name">Project access: read only visible tasks</field>
    <field name="model_id" ref="project.model_project_task"/>
    <field name="domain_force">[('access_task_visible', '=', True)]</field>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
<!-- project_task_rule_access_write: same shape, perm_write + perm_create only,
     domain [('access_task_writable', '=', True)] -->
<!-- project_task_rule_access_unlink: the only rule testing the group, because project_todo
     gives base.group_user unlink -->
<field name="domain_force">[(0, '=', 1)] if user.has_group('serichai_project_access.serichai_project_access_group_restricted') and not user.has_group('project.group_project_user') else [(1, '=', 1)]</field>
```

<!-- project_task_rule_access_group_write: GROUP rule (restricted group), domain [(1, '=', 1)],
     perm_write + perm_create. Core's group rule for base.group_user only covers private tasks,
     so without this the global write rule above would have nothing to narrow. See research D1a. -->

ACL (restricted group): `project.task` r/w/c; `project.project`, `.role`, `.task.recurrence` read;
profile/line full for managers. `project_project_security.xml`: read rule on `access_can_read`.

### `static/src/views/access_task_list.js`

```js
export class AccessTaskListController extends ListController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async openRecord(record, { force, newWindow } = { force: false }) {
        if (!record.data.access_task_detail) {
            this.notification.add(_t("You are not allowed to open this task."), { type: "warning" });
            return;
        }
        const activeIds = this.model.root.records
            .filter((r) => r.data.access_task_detail)
            .map((r) => r.resId);
        this.props.selectRecord(record.resId, { activeIds, force, newWindow });
    }
}
registry.category("views").add("serichai_access_task_list",
    { ...listView, Controller: AccessTaskListController });
```

`access_task_kanban.js` differs from the list: extends `KanbanController` (kanbanView),
`openRecord(record, { newWindow } = {})` without `force`, key `serichai_access_task_kanban`;
same warning and `activeIds` filter. Arches load `access_task_detail`; the list adds `decoration-muted`, `create="0"`, `delete="0"`.

### `views/project_access_profile_views.xml` (form core)

```xml
<notebook>
    <page string="User" name="users"><field name="user_ids" readonly="1"/></page>
    <page string="Project" name="projects">
        <field name="line_ids">
            <list>
                <field name="project_ids" widget="many2many_tags"/>
                <field name="access_level"/>
                <field name="task_access"/>
            </list>
            <form>
                <div class="alert alert-warning" invisible="not warning_message">
                    <field name="warning_message"/>
                </div>
                <group invisible="access_level == 'write'">  <!-- on stage_ids, hidden_property_names, task_access -->
                    <field name="stage_ids" widget="many2many_tags"/>
                    <field name="hidden_property_names"/>
                </group>
            </form>
        </field>
    </page>
</notebook>
```

List view: Department (`name`) and project tags (FR-002). Menu `project_access_profile_menu`
under `project.menu_project_config`, manager-only.

### `hooks.py` - migration (idempotent, D12)

```python
def post_init_hook(env):
    old_group = env.ref(f'{OLD}.group_project_task_list_only', raise_if_not_found=False)
    Profile = env['project.access.profile'].with_context(active_test=False)
    if not old_group or Profile.search_count([('name', '=', MIGRATED_NAME)]):
        return                                  # fresh install, or already migrated
    group = _get_or_create_group(env)           # implies base.group_user
    pinned = int(env['ir.config_parameter'].sudo().get_param(f'{OLD}.expanded_access_project_id', 0)) or False
    projects = env['project.project'].search([('is_template', '=', False), ('id', '!=', pinned)])
    stages = env['project.task.type'].search([('name', 'in', STAGES)])   # the 4 Thai names
    if len(stages) < len(STAGES):
        _logger.warning("Migration: some production stages not found")
    hidden = [r.property_string for r in env['project.task.property.access'].sudo().search([])
              if old_group not in r.group_ids]
    lines = [Command.create({'project_ids': [Command.set(projects.ids)], 'access_level': 'read',
                             'task_access': 'list', 'stage_ids': [Command.set(stages.ids)],
                             'stages_exhausted': not stages,
                             'hidden_property_names': '\n'.join(hidden)})]
    if pinned:
        lines.append(Command.create({'project_ids': [Command.set([pinned])], 'access_level': 'write'}))
    Profile.create({'name': MIGRATED_NAME, 'group_ids': [Command.set(group.ids)], 'line_ids': lines})
    old_group.sudo().user_ids.write({'group_ids': [Command.link(group.id)]})
    _restore_core_menu_groups(env)              # six core menus back to core values
```

## Specs must assert

- Read vs Write per project; ungranted project and its tasks invisible (search, read_group, direct read).
- Stage filter: allowed stages only; empty selection = all; `stages_exhausted` = none; kanban columns limited.
- `create` and `write` succeed only with Write (proves rule works at create); Read refused; `unlink` refused for Write users; project write refused.
- Hidden property absent in `read`/`web_read`, present for Write/unrestricted; stored value survives a write.
- `web_read` guard: list-only refused, open-detail allowed, `web_search_read` still works under patched `request`; project users exempt.
- Merge cases FR-018 (write>read, detail>list, stage union with "all", hidden intersection, single grant unchanged).
- Cache: group added/removed, line edited, profile archived, project archived change results without restart.
- Restricted status: profile create/archive/delete adds/removes the implied group; forbidden groups rejected; project user/manager unaffected.
- Constraint: same project twice in one profile refused; write line forces `detail`.
- Menus: restricted sees exactly two Project menus; a member with project rights sees the standard ones only.
- Migration: profile, lines, users moved, idempotent rerun, hidden names, core menu groups restored.
- Profile screens only for project managers.

## Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Global rules + non-stored search fields slow queries or break `create` checks | Resolver cached; test create path early (phase 2 spike) |
| R2 | Implied-group sync touches core `res.groups` | Constraint on forbidden groups, idempotent diff, tests |
| R3 | Migration parity: users with extra groups see different properties than the approximation | Rehearsal diff per user (SC-005) before uninstall |
| R4 | Chatter/attachments of list-only tasks still readable via other RPCs | Accepted (FR-015, spec 007); documented |
| R5 | Granted projects with `followers`/`invited_users` visibility stay blocked by core rules | Warning on line, documented (D11) |
| R7 | New projects after migration are not auto-granted (old role saw all) | Open question 3 |

## Open questions (resolved at Gate 2, 2026-10-10)

1. First Project screen: stock project kanban cards (no custom JS). Accepted.
2. Forbidden department groups: `base.group_user/portal/public/system` and Project user/manager. Accepted.
3. Migrated "all other projects" line is a snapshot; new projects are granted manually. Accepted.
4. Defensive `write()` merge of hidden values is kept. Accepted.
5. Constitution addon list and `CLAUDE.md` are amended at cutover. Accepted.

## Review fixes (2026-10-10)

- Tasks without a project (private tasks) are not governed by the matrix: the three access
  flags and `_access_domain` let `project_id = False` through, the group write rule is limited to
  `project_id != False` and the unlink rule leaves `project_id = False` open, so core's "own
  private task" rule alone decides.
- `create`/`write` on `project.task` refuse, for restricted users, a `project_id` that is not a
  Write project (`_access_check_target_project`).
- `_read_group_stage_ids` limits columns for restricted users to stages allowed by the granted
  projects (stage list of the grant, or, for "all stages", stages shared or linked to the
  project), narrowed to the project(s) named by the domain and/or `default_project_id`.
- Write lines are normalised on every create/write (no stages, hidden names or exhausted flag,
  `task_access = detail`); write -> read resets `task_access` to `list` unless given.
- `stages_exhausted` shows in the line form (read-only, only when set) and in `warning_message`.
- `_check_group_ids` also rejects groups transitively implying a forbidden group, except
  `base.group_user` (implied by almost every internal group, the control group and the migration
  group); `base.group_user` itself stays forbidden.
- `_sync_restricted_group(affected)` links/unlinks only the groups of the created, changed or
  deleted profiles; a group is unlinked only if no active profile still wants it.


## Addendum: hidden-property leaks and tags input (v1.1.0)

**Bug A (hidden property still visible in All Tasks).** Property *values* were already filtered in
`project.task.read`, but the property *definitions* travel separately: the web client reads the
project co-record (`project_id` with `task_properties_definition`, via `web_read`/`web_search_read`
of `project.project`) and the search panel lists property names through
`web_search_read` on `project.project`; both bypass the task filter. Fixes:

- `project.project.read` drops hidden definitions per project grant (restricted users have no
  project write, so the definition is never saved back).
- `project.task._search` / `_read_group` refuse a domain, group-by or order naming a hidden property
  (filtering or grouping would reveal its values); `get_property_definition` returns `{}` for it;
  `export_data` refuses `task_properties` when the project hides a property.
- One normaliser `norm_label` (NFKC, inner spaces collapsed, trim, casefold) is used by the
  resolver, `read`, the project read and the warning, so labels with extra spaces, different case
  or Thai combining marks typed in another order match.
- Matching is on the definition `string` (the label the client shows), not the internal `name`.

Remaining open paths for hidden property data (accepted limits): none for values or labels over the
ORM/web RPC paths above. Residual: a property name shared by projects (copied definitions) is blocked
for search/group-by in all granted projects (safe side); sorting by a hidden property inside a
custom SQL/report outside the ORM is not covered; chatter/tracking of properties is not enabled in
core; values of a task in a project granted with `Write` are intentionally visible. If the admin
typed a label that matches no definition (see the warning), nothing is hidden.

**Bug B (tags).** `hidden_property_label_ids` (M2M to `project.access.property.label`) is the input
(`many2many_tags`, create on the fly); `hidden_property_names` stays as the stored text mirror so the
resolver, hook and tests are unchanged. Upgrade: `migrations/1.1.0/post-migration.py`.

**Hidden Property Labels screen.** `views/project_access_property_label_views.xml` (list editable, form with an
in-use warning, search, action) and menu `project_access_property_label_menu` (Project > Configuration,
`groups="project.group_project_manager"`). `project.access.property.label.unlink` collects the lines using the
labels, lets the M2M rows cascade, then `add_to_compute` on `hidden_property_names` of those lines and clears
the registry cache, so the text mirror and the resolver stay consistent. Tests in `test_hidden_property_tags.py`.
