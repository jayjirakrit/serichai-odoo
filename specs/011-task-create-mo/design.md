# Design: Create Manufacturing Orders from a Project Task

Spec: `spec.md` · Plan: `plan.md` · Contracts: none (single area) · Data: `data-model.md`

## 1. Approach

Built. Extend `serichai_project_mo`: Finish Goods M2M on the task, a transient wizard, and a project-level
"all MOs done" email. `mrp.production` only detects relevant changes and schedules a deferred, once-per-project
check; the project decides and sends. Creation goes through one task method so the button, the wizard and any RPC
share the same checks. Reused: `project_mrp.project_id`, the `project_task_mrp_production_rel` link, existing task
write rules. Untouched: `odoo/`, MuK, the existing record rules. `serichai_project_security` is not modified.

## 2. Key decisions

| Decision | Choice | Why / trade-off |
|----------|--------|-----------------|
| Access | `check_access('write')` as real user, then `sudo()` create | No group can create MOs; task write rules enforced for free; `create_uid` stays the user |
| Idempotency | row lock on task + write task row | Stale-snapshot competitors fail and are retried by Odoo (research D5) |
| Hooks | `_write_multi` (write and computed-field flush), `create`, `unlink` -> `_on_tracked_fields_changed` -> `_schedule_all_mos_done_check` (precommit, once per project) | `state` and `project_id` are stored computes: a change can arrive without `write`; `_write_multi` is their common sink, so no copy of core's `@api.depends`; the final state is only known after recomputes |
| Email | queued `send_mail` under sudo at precommit, flag set under project lock | No SMTP in transaction; no double send; busy project lock -> never raises, skipped (no recheck cron) |
| ACL | one row for project users in the mo addon | Self-contained; no cross-addon dependency |
| Result | MO action filtered by task; notification if nothing new or if the user cannot read MOs | Matches FR-010, FR-023 |
| Button | `groups="project.group_project_user"` | UI only; server check unchanged |
| Template | hand-edited rich template, assigned to existing projects at install | FR-012 |

## 3. Flow

```text
button -> task.action_open_create_mo_wizard()
            check_access('write'); finish goods? project?  -> UserError / AccessError
        -> wizard (assignee, BoM warning)
Confirm -> wizard.action_confirm() -> task._create_mos_from_finish_goods(assignee)
            same checks again (never trust the UI)
            lock task (LockError -> "try again")
            todo = finish_goods - products of non-cancelled linked MOs
            sudo create MOs (draft) + link on task side
            -> new MOs ? MO action (domain: task) : "nothing new" notification
MO create / state -> done/cancel / unlink / project change (write or computed-field flush, all via _write_multi)
        -> project._schedule_all_mos_done_check()   # set on cr.precommit, one callback per transaction
        -> (precommit) _check_all_mos_done(): try-lock projects (busy -> skipped, no raise)
           -> _all_mos_done()? -> _send_mo_done_mail() -> queue mail, flag = True
MO create (open) / open MO joins a project -> _reset_mo_done_mail_sent()
```

## 4. Key files

| Requirements | Key files |
|--------------|-----------|
| FR-001, 002 | `models/project_task.py`, `views/project_task_views.xml` |
| FR-003..006, 010, 011, 023 | `wizard/project_task_create_mo.py`, `wizard/project_task_create_mo_views.xml` |
| FR-004, 007, 008, 019 | `models/project_task.py` (`_create_mos_from_finish_goods`) |
| FR-012..016, 020, 021 | `models/project_project.py`, `models/mrp_production.py`, `data/project_project_data.xml`, `views/project_project_views.xml` |
| FR-017, 022 | `security/ir.model.access.csv` (mo addon), task write rules, button `groups` |
| Thai labels | `i18n/th.po`, `i18n/serichai_project_mo.pot` |
| FR-001..023 | `tests/test_create_mo_from_task.py` |

### 4.1 Backend

#### serichai_project_mo/models/project_task.py - FR-001, 004, 007, 008, 019
```python
finish_goods_ids = fields.Many2many(
    'product.product', 'project_task_finish_goods_rel', 'project_task_id', 'product_id',
    string='Finish Goods', domain="[('type', '=', 'consu')]", copy=False)

def _check_can_create_mos(self):
    self.ensure_one()
    self.check_access('write')  # real user: ACL + record rules
    if not self.finish_goods_ids:
        raise UserError(self.env._("Add at least one Finish Goods product first."))
    if not self.project_id:
        raise UserError(self.env._("Set a project on the task before creating Manufacturing Orders."))

def action_open_create_mo_wizard(self):
    self._check_can_create_mos()
    return {
        'type': 'ir.actions.act_window', 'name': self.env._("Create Manufacturing Orders"),
        'res_model': 'project.task.create.mo', 'view_mode': 'form', 'target': 'new',
        'context': {'default_task_id': self.id},
    }

def _create_mos_from_finish_goods(self, user):
    """Create one draft MO per uncovered Finish Goods product; return the new MOs."""
    self._check_can_create_mos()
    try:
        self.lock_for_update(allow_referencing=True)
    except LockError:
        raise UserError(self.env._("Manufacturing Orders are being created for this task. Try again."))
    self.invalidate_recordset(['mrp_production_ids'])
    # sudo: no custom group may create mrp.production; access to the task was checked above.
    # sudo() keeps the uid, so create_uid is the real user; user_id is the chosen assignee.
    task = self.sudo()
    covered = task.mrp_production_ids.filtered(lambda mo: mo.state != 'cancel').product_id
    todo = task.finish_goods_ids - covered
    mos = task.env['mrp.production'].create([{
        'product_id': product.id, 'user_id': user.id,
        'project_id': task.project_id.id, 'origin': task.name,
    } for product in todo])
    # Writing the task row makes a stale-snapshot concurrent confirm fail and be retried (research D5)
    task.write({'mrp_production_ids': [Command.link(mo.id) for mo in mos]})
    return mos
```
**Check**: manual links count as coverage because `mrp_production_ids` is the shared M2M; cancelled are filtered out.
**Specs must assert**: N MOs with `user_id`, `project_id`, task link, `origin`, draft; rerun creates 0; cancelled-only product recreated; manual-linked MO covers; no finish goods / no project -> `UserError`; user without task write -> `AccessError` and 0 MOs; `create_uid` = acting user; task `write_date` bumps.

#### serichai_project_mo/models/project_task.py - smart button (same file)
```python
def action_view_mrp_productions(self):
    self.ensure_one()
    return {
        'type': 'ir.actions.act_window', 'name': self.env._("Manufacturing Orders"),
        'res_model': 'mrp.production', 'view_mode': 'list,form',
        'domain': [('project_task_ids', 'in', self.ids)],
    }
```
**Check**: added by this feature (CLAUDE.md named it but the code lacked it); the stat button uses `type="object" name="action_view_mrp_productions"`.
**Specs must assert**: button action domain returns exactly the task's MOs.

#### serichai_project_mo/wizard/project_task_create_mo.py - FR-003, 010, 011, 023
```python
class ProjectTaskCreateMo(models.TransientModel):
    _name = 'project.task.create.mo'

    task_id = fields.Many2one('project.task', required=True, readonly=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Assignee", required=True,
        default=lambda self: self.env.user if self.env.user.has_group('mrp.group_mrp_user') else False,
        domain=lambda self: [('all_group_ids', 'in', self.env.ref('mrp.group_mrp_user').id)])
    warning = fields.Text(compute='_compute_warning')

    def action_confirm(self):
        self.ensure_one()
        mos = self.task_id._create_mos_from_finish_goods(self.user_id)
        if not mos:
            return self._notification(
                'info', self.env._("Nothing new to create: every Finish Goods product already has an MO."))
        title = self.env._("%s Manufacturing Orders created", len(mos))
        if not self.env['mrp.production'].has_access('read'):
            # the MO list would raise an AccessError for this user
            return self._notification('success', title)
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.mrp_production_action')
        action.update(name=title, domain=[('project_task_ids', 'in', self.task_id.ids)])
        return action

    def _notification(self, notification_type, message):
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'type': notification_type, 'message': message,
            'next': {'type': 'ir.actions.act_window_close'}}}
```
`_compute_warning` (BoM lookup with `mrp.bom.sudo()._bom_find`, product names only) is unchanged from research D8.
**Check**: no logic beyond the task method; the wizard is replaceable. The assignee domain is a UI filter, not enforced server-side.
**Specs must assert**: confirm without assignee refused (required); warning names only BoM-less products and is empty otherwise; confirm creates MOs and returns an action with the task domain; second confirm returns the notification; a user without `mrp.production` read gets the "N created" toast, not the list.

#### serichai_project_mo/models/mrp_production.py - FR-013..016, 021
```python
@api.model_create_multi
def create(self, vals_list):
    productions = super().create(vals_list)
    productions._on_tracked_fields_changed(dict.fromkeys(productions.ids, (False, False)))  # new = from nothing
    return productions

def _write_multi(self, vals_list):
    """Single sink of write() and of the flush of recomputed stored fields."""
    if not any('state' in vals or 'project_id' in vals for vals in vals_list):
        return super()._write_multi(vals_list)
    old = self._snapshot()          # {id: (state, project_id)} read from the database
    res = super()._write_multi(vals_list)
    self._on_tracked_fields_changed(old)
    return res

def unlink(self):
    projects = self.project_id  # super() cancels the MOs first, which already schedules the check
    res = super().unlink()
    projects._schedule_all_mos_done_check()
    return res

def _on_tracked_fields_changed(self, old):
    Project = self.env['project.project']
    to_reset = to_check = Project
    for mo in self.filtered(lambda mo: mo.id in old):
        old_state, old_project_id = old[mo.id]
        if (mo.project_id.id or None) != old_project_id:   # SQL NULL snapshot vs 0/False
            if mo.state != 'cancel':
                to_reset |= mo.project_id                 # open MO joins: new batch
            to_check |= Project.browse(old_project_id)    # old project may now be complete
            if mo.state == 'done':
                to_check |= mo.project_id
        if mo.state != old_state and mo.state in ('done', 'cancel'):
            to_check |= mo.project_id
    to_reset._reset_mo_done_mail_sent()
    to_check._schedule_all_mos_done_check()
```
No override of `_compute_state` / `_compute_project_id` (they would copy core's `@api.depends`). The old values come from the database because at flush time the cache already holds the new ones. The hook fires when the write reaches `_write_multi` (at flush for plain assignments); every path flushes before commit, and the precommit runner flushes first.
**Specs must assert**: done, cancel and unlink of the last open MO each lead to the email; an MO created directly in done state can complete the project, one created cancelled does not reset the flag; state or project changed by compute alone triggers/resets; `create` of open MOs schedules no check; one check per project per transaction; a cancelled MO joining a project or a same-project write does not reset the flag.

#### serichai_project_mo/models/project_project.py - FR-012..016, 020, 021
```python
def _schedule_all_mos_done_check(self):
    project_ids = [pid for pid in self.ids if isinstance(pid, int)]
    if not project_ids:
        return
    precommit = self.env.cr.precommit
    pending = precommit.data.get(PENDING_CHECKS_KEY)
    if pending is None:
        pending = precommit.data[PENDING_CHECKS_KEY] = set()
        Project = self.env['project.project']
        precommit.add(lambda: Project._run_scheduled_all_mos_done_check())
    pending.update(project_ids)

def _check_all_mos_done(self):
    # sudo: the outcome must not depend on the acting user's rights (FR-020)
    projects = self.sudo().filtered(lambda p: p.id and not p.mo_done_mail_sent)
    if not projects:
        return
    locked = projects.try_lock_for_update(allow_referencing=True)
    if locked != projects:
        # a concurrent transaction holds a project row: never raise (the mail must not veto the MO
        # change); the locked projects are skipped (logged) and the other transaction checks its own state
        _logger.info("Projects %s are locked ...", (projects - locked).ids)
    for project in locked:
        project.invalidate_recordset(['mo_done_mail_sent'])
        if project.mo_done_mail_sent or not project.user_id.partner_id:
            continue  # no manager: do NOT set the flag (FR-016)
        if project._all_mos_done():
            project._send_mo_done_mail()

def _send_mo_done_mail(self):
    template = self.mo_done_mail_template_id or self.env.ref(DEFAULT_MAIL_TEMPLATE_XMLID, raise_if_not_found=False)
    if not template:
        _logger.warning("Project %s (id %s): all MOs are done but no email template is set ...", self.name, self.id)
        return
    template.sudo().send_mail(self.id, force_send=False)
    self.mo_done_mail_sent = True
```
`_all_mos_done` is `search_count` of non-cancelled MOs > 0 and none non-done (sudo). `_set_default_mo_done_mail_template` assigns the default template to projects without one (install only). `_mark_completed_projects_as_notified` (install only, idempotent) sets `mo_done_mail_sent = True` on projects having at least one non-cancelled MO and no open one, so the first cron run does not email projects that were already complete.
**Check**: the precommit callback flushes first, so recomputed states are visible.  The flag claim and the project row lock allow one mail per batch.
**Specs must assert**: 2 MOs: first done = 0 mails, second = 1 `mail.mail` to manager partner; open MO = 0; all cancelled = 0; repeat check = still 1; new MO resets, finishing it = 2nd mail; no manager = 0 mails and flag False; missing template = warning logged, flag False; a locked project does not raise and is skipped; chosen template used, empty falls back to default; trigger user without mail rights still yields the mail; install sets the default on existing projects and flags already-complete projects as notified.

### 4.2 Views and data

#### serichai_project_mo/views/project_task_views.xml - FR-001, 002, 022
```xml
<button class="oe_stat_button" icon="fa-industry" type="object"
        name="action_view_mrp_productions" invisible="mrp_production_count == 0"> ... </button>
<!-- inside the Manufacturing Orders page -->
<field name="finish_goods_ids" widget="many2many_tags"/>
<!-- ...existing mrp_production_ids list... -->
<div class="mt-2">
    <button name="action_open_create_mo_wizard" type="object" string="Create MO"
            class="btn-primary" icon="fa-industry"
            groups="project.group_project_user"
            invisible="not finish_goods_ids"/>
</div>
```
**Check**: button is at the bottom of the tab, invisible with empty Finish Goods and hidden from non-project users (UI only; server re-checks).
**Specs must assert**: view loads for a project user; not asserted: visibility (client side).

#### serichai_project_mo/wizard/project_task_create_mo_views.xml - FR-003
```xml
<form>
    <field name="task_id" invisible="1"/>
    <div class="alert alert-warning" role="alert" invisible="not warning"><field name="warning" nolabel="1"/></div>
    <group><field name="user_id" options="{'no_create': True}"/></group>
    <footer>
        <button name="action_confirm" type="object" string="Confirm" class="btn-primary" data-hotkey="q"/>
        <button string="Cancel" special="cancel" data-hotkey="x"/>
    </footer>
</form>
```
**Specs must assert**: covered by wizard tests (Cancel creates nothing is UI-only).

#### serichai_project_mo/views/project_project_views.xml and data/project_project_data.xml - FR-012
```xml
<!-- inherit project.edit_project -->
<xpath expr="//page[@name='settings']" position="inside">
    <group name="mo_notification" string="Manufacturing">
        <field name="mo_done_mail_template_id" options="{'no_create': True}"/>
    </group>
</xpath>
<!-- data (noupdate=1), body abbreviated -->
<record id="mail_template_all_mos_done" model="mail.template">
    <field name="name">Project MO Complete Email Template</field>
    <field name="model_id" ref="project.model_project_project"/>
    <field name="use_default_to" eval="False"/>
    <field name="partner_to">{{ object.user_id.partner_id.id }}</field>
    <field name="subject">{{ object.name }}: all finished goods produced</field>
    <field name="body_html" type="html">
        <t t-set="productions" t-value="object.env['mrp.production'].search([('project_id', '=', object.id), ('state', '!=', 'cancel')], order='name')"/>
        <!-- header, project / manager / "N done" summary, MO table (name, product, quantity), "View Project in Odoo" link -->
    </field>
    <field name="lang">{{ object.user_id.partner_id.lang }}</field>
</record>
<function model="project.project" name="_set_default_mo_done_mail_template"/>
<function model="project.project" name="_mark_completed_projects_as_notified"/>
```
**Upgrade path**: Odoo skips `<function>` tags in noupdate files on `-u`, so the two calls above run on a fresh install only. `migrations/19.0.1.1.1/post-migration.py` calls both on upgrade (manifest `1.1.1`; Odoo prefixes the server version, and runs the script when the installed version is lower). A `post-` script runs right after the module data is loaded, so the template xmlid exists (an `end-` script is not needed); on upgrade the new columns hold NULL template and `False` flag, which are what it fixes. Both functions are idempotent, so a second run changes nothing.
**Check**: the quantity cell uses `t-options="{'widget': 'float', 'decimal_precision': 'Product Unit'}"` (usual number formatting: `1.00`, `1,234.50`, recipient-language separators); wording is administrators' to edit; `noupdate` protects edits. The body counts non-cancelled MOs (all done at send time) and is rendered under sudo (queued by `template.sudo()`).
**Specs must assert**: default template exists, is the default on new projects and is assigned to existing ones at install and on upgrade (post-migration); the domain lists only `project.project` templates; the body renders under sudo and shows formatted quantities.

### 4.3 Security

#### serichai_project_mo/security/ir.model.access.csv - FR-017
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_project_task_create_mo_user,project.task.create.mo.user,model_project_task_create_mo,project.group_project_user,1,1,1,1
```
**Check**: no new rule. A user without write on the task gets `AccessError` from `check_access('write')`; the MO create runs only inside our `sudo()`.
**Specs must assert**: project user without `mrp.group_mrp_user` can create when the task is writable; user without task write refused (`AccessError`, 0 MOs); wizard record creatable by project users.

### 4.4 Manifest

#### serichai_project_mo/__manifest__.py
```python
'version': '1.1.1',
'depends': ['project', 'mrp', 'project_mrp', 'mail'],
'data': [
    "security/ir.model.access.csv",
    "data/project_project_data.xml",
    "views/mrp_production_views.xml",
    "views/project_task_views.xml",
    "views/project_project_views.xml",
    "wizard/project_task_create_mo_views.xml",
    "report/project_task_report_views.xml",
    "report/project_task_report_templates.xml"
],
```
`wizard` is imported in `__init__.py`. Translations in `i18n/th.po` (+ `.pot`) are loaded by Odoo automatically; they need no manifest entry.

### 4.5 Tests

#### serichai_project_mo/tests/test_create_mo_from_task.py (follows test_contract_mo_report.py)
Specs must assert (no code in design):
- US1/FR-005/006: 3 finish goods -> 3 draft MOs with assignee, project, task link, origin; `project_id` not overwritten by the BoM compute.
- US2: rerun = 0; add 4th = 1; cancelled recreated; manual link covers; two sequential confirms = no duplicates.
- US3: no finish goods / no project -> `UserError` from `action_open_create_mo_wizard`, wizard confirm and the model method; BoM warning text.
- US4: all email cases of 4.1 `project_project.py` and `mrp_production.py` (use `mail.mail` count for the manager partner), including the deferred, once-per-project check, compute-driven triggers, created-done MO, locked-project recheck cron and missing template.
- US5 (as non-MRP project user): create works only with task write; `create_uid` is the acting user; a user without MO read gets a notification.
Run: `--test-enable --test-tags /serichai_project_mo`.

## 5. Risks

- R1 Concurrency: lock + task-row write relies on Odoo's serialization retry; unit tests cannot reproduce two real transactions, so verify manually with two sessions (quickstart 8). A truly simultaneous confirm gets a "try again" `UserError`.
- R3 `sudo()` create: runs MO create side effects (sequence, moves, mail tracking) as superuser rights but real uid; `create_uid` = clicking user, responsible = assignee, who may not be able to open MOs they are assigned if not an MRP user (domain prevents choosing such users in the UI only).
- R4 RESOLVED: state/project changes by pure recompute are caught in `_write_multi` (no copy of core's depends), and every trigger goes through the deferred, deduplicated precommit check.
- R5 Backorders: marking done with a backorder creates a new MO first (flag reset), so no premature email.
- R6 Queued email depends on the mail queue cron; default Odoo cron sends within minutes. The mail row itself is written at precommit, not during the MO write.
- R7 `project_mrp` is a new dependency: installing it on the live DB adds its views (project MO/BoM buttons) for MRP users.
- R8 A locked project at check time (concurrent sibling MO) does not raise but is skipped: in the rare race where two sibling MOs finish at the same instant and each sees the other as open, no email is sent (no recheck cron by decision; the flag stays False, so the next MO change on the project re-checks it). Two-session verification stays manual (quickstart 8).
- R9 Thai translation is partial; untranslated texts fall back to English.

## 6. Spec / code mismatches

- CLAUDE.md said `project.task.action_view_mrp_productions` exists; the code lacked it (added here).
- Spec FR-010 allows "MO list or N MOs created"; code shows the list (title carries N) and uses a notification for "nothing new" and for users who cannot read MOs (FR-023).
- Template name differs from the first draft: "Project MO Complete Email Template" (hand-edited by the user); the subject still says "all finished goods produced".

## 7. Decisions (Gate 2, resolved)

- Add the missing `action_view_mrp_productions` (small scope growth): accepted, done.
- Flag reset also when an open MO is written or recomputed into a project (beyond "created"): accepted; cancelled MOs and same-project writes do not reset.
- Assignee not enforced server-side as an MRP user, UI domain only like core: accepted.
- Final task: update CLAUDE.md `serichai_project_mo` section: handled by a separate task, not part of this design.
- Email check deferred through `cr.precommit`, once per project: accepted (replaces direct hook calls).
- Button limited to project users in the view: accepted (UI only).
