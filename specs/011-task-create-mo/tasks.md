# Tasks: Create Manufacturing Orders from a Project Task

**Input**: `specs/011-task-create-mo/` (spec.md, plan.md, design.md, data-model.md, research.md, quickstart.md)
**Area**: `odoo` (root `serichai-odoo/`, fullstack). All paths below are relative to the repo root `/home/odoo/serichai-odoo/`.
**Tests**: Included (constitution principle IV; plan.md "Testing"). Test files are Odoo `TransactionCase` with `@tagged('post_install', '-at_install')`, `consu` products, following `serichai-odoo/serichai_project_mo/tests/test_contract_mo_report.py`.
**Scope notes**: Buy Goods is OUT of scope (no `buy_goods_ids`). `serichai_project_security` is OUT of scope (not modified, not a dependency; Task List Viewer role gets no wizard ACL). No new `ir.rule`, no new group. Assignee is a UI-only filter (no server-side MRP-user check). Never edit `odoo/` or `muk_web_theme/`.
**Module gate** (run after each phase): `cd odoo && ../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db --test-enable --stop-after-init -u serichai_project_mo`

Format: `- [ ] T### [P?] [US?] Description with file path`. `[P]` = can run in parallel (different files, no unfinished dependency).

---

## Phase 1: Setup

**Purpose**: Dependencies, package skeleton, manifest wiring.

- [X] T001 Update `serichai-odoo/serichai_project_mo/__manifest__.py`: set `depends` to `['project', 'mrp', 'project_mrp', 'mail']`; add to `data` (before the existing report files, in this order): `security/ir.model.access.csv`, `data/project_project_data.xml`, `views/project_task_views.xml` (keep if already listed), `views/project_project_views.xml`, `wizard/project_task_create_mo_views.xml`. Keep every existing entry.
- [X] T002 [P] Create `serichai-odoo/serichai_project_mo/wizard/__init__.py` (`from . import project_task_create_mo`) and add `from . import wizard` to `serichai-odoo/serichai_project_mo/__init__.py`.
- [X] T003 [P] Create `serichai-odoo/serichai_project_mo/models/project_project.py` (empty `_inherit = 'project.project'` class shell) and import it in `serichai-odoo/serichai_project_mo/models/__init__.py` (alongside the existing `project_task` and `mrp_production` imports).
- [X] T004 [P] Ensure `serichai-odoo/serichai_project_mo/tests/__init__.py` imports `test_create_mo_from_task` (keep the existing `test_contract_mo_report` import) and create the empty test module `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py` with the shared `setUpClass` fixtures: a project with a manager (`user_id`), a task in it, three `consu` products (`type='consu'`), a project user (`project.group_project_user`, no `mrp.group_mrp_user`), an MRP user, and a helper that creates the wizard.

**Checkpoint**: addon still installs/updates with empty shells.

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: Field, wizard model, ACL, and the single creation choke point that every story relies on.

- [X] T005 Add to `serichai-odoo/serichai_project_mo/models/project_task.py` the field `finish_goods_ids = fields.Many2many('product.product', 'project_task_finish_goods_rel', 'project_task_id', 'product_id', string='Finish Goods', domain="[('type', '=', 'consu')]", copy=False)`. Constraints verbatim from data-model.md: table `project_task_finish_goods_rel`, columns `project_task_id`, `product_id`; domain `[('type','=','consu')]`; `copy=False`; one-sided (no inverse field on `product.product`). Do not touch the existing `project_task_mrp_production_rel` M2M.
- [X] T006 Add to `serichai-odoo/serichai_project_mo/models/project_task.py` the method `action_view_mrp_productions` (act_window on `mrp.production`, `view_mode` `list,form`, domain `[('project_task_ids', 'in', self.ids)]`, name "Manufacturing Orders"). It is missing today although CLAUDE.md names it.
- [X] T007 Add `_check_can_create_mos(self)` to `serichai-odoo/serichai_project_mo/models/project_task.py` per design.md 4.1: `ensure_one()`, `self.check_access('write')` as the real user, `UserError` if no `finish_goods_ids` ("Add at least one Finish Goods product first."), `UserError` if no `project_id` ("Set a project on the task before creating Manufacturing Orders."). Import `UserError`, `Command` (and `LockError` from `odoo.exceptions` if available in 19.0; verify the import in the venv).
- [X] T008 Add `_create_mos_from_finish_goods(self, user)` to `serichai-odoo/serichai_project_mo/models/project_task.py` per design.md 4.1: call `_check_can_create_mos()`; `lock_for_update(allow_referencing=True)` with `LockError` mapped to `UserError("... Try again.")`; `invalidate_recordset(['mrp_production_ids'])`; `task = self.sudo()` (why-comment: no custom group may create `mrp.production`; access checked above; `sudo()` keeps the uid so `create_uid` is the acting user); `covered` = products of non-cancelled MOs in `mrp_production_ids`; one `create([...])` with `product_id`, `user_id`, `project_id`, `origin = task.name`; then `task.write({'mrp_production_ids': [Command.link(mo.id) ...]})` (this write bumps the task row and defeats stale-snapshot concurrent confirms); return the new MOs. MOs stay in Draft, quantity left to core defaults (BoM quantity). Do not redefine `mrp.production.project_id`.
- [X] T009 [P] Add `serichai-odoo/serichai_project_mo/security/ir.model.access.csv` with header `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink` and one row: `access_project_task_create_mo_user,project.task.create.mo.user,model_project_task_create_mo,project.group_project_user,1,1,1,1`.
- [X] T010 Create the wizard model in `serichai-odoo/serichai_project_mo/wizard/project_task_create_mo.py`: `TransientModel` `project.task.create.mo` with `task_id` (Many2one `project.task`, required, readonly, `ondelete='cascade'`), `user_id` (Many2one `res.users`, string "Assignee", required; default = current user only if it has `mrp.group_mrp_user`; domain = users in `mrp.group_mrp_user`, UI filter only, no server-side enforcement) and `warning` (Text, computed). Implement `action_confirm()` calling `self.task_id._create_mos_from_finish_goods(self.user_id)`; if no MOs were created return a `display_notification` (type info, "Nothing new to create: every Finish Goods product already has an MO.") whose `next` is `act_window_close`; otherwise return `mrp.mrp_production_action` with `name = "%s Manufacturing Orders created"` and `domain = [('project_task_ids', 'in', task.ids)]`. Leave `_compute_warning` as a stub returning `False` (filled in US3).
- [X] T011 Add `action_open_create_mo_wizard(self)` to `serichai-odoo/serichai_project_mo/models/project_task.py`: call `_check_can_create_mos()` then return the `ir.actions.act_window` (`res_model` `project.task.create.mo`, `view_mode` `form`, `target` `new`, `context` `{'default_task_id': self.id}`).

**Checkpoint**: models import cleanly; `-u serichai_project_mo` loads (views come in US1).

---

## Phase 3: User Story 1 - Create MOs from Finish Goods (P1) MVP

**Goal**: A user lists Finish Goods on a task, presses Create MO, picks an assignee, and gets one MO per product linked to the task and project (FR-001 to FR-006, FR-009 removed, FR-010).
**Independent test**: 3 products in Finish Goods on a task in a project; confirm with an assignee; exactly 3 draft MOs with the assignee, the task's project, and the task link.

- [X] T012 [US1] Edit `serichai-odoo/serichai_project_mo/views/project_task_views.xml` (inherits `project.view_task_form2`): give the existing stat button `type="object" name="action_view_mrp_productions"`; inside `mrp_production_page` add `<field name="finish_goods_ids" widget="many2many_tags"/>` (label "Finish Goods") above the existing `mrp_production_ids` list, and at the bottom of the page a `<button name="action_open_create_mo_wizard" type="object" string="Create MO" class="btn-primary" icon="fa-industry" invisible="not finish_goods_ids"/>`. No Buy Goods field.
- [X] T013 [P] [US1] Create `serichai-odoo/serichai_project_mo/wizard/project_task_create_mo_views.xml`: form view for `project.task.create.mo` per design.md 4.2 (hidden `task_id`, warning alert `invisible="not warning"`, `user_id` with `no_create`, footer **Confirm** `action_confirm` primary and **Cancel** `special="cancel"`) plus the act_window record if needed for the ACL/menu-less dialog.
- [X] T014 [P] [US1] Write tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`: (a) 3 finish goods produce 3 MOs, each `state == 'draft'`, with `user_id` = assignee, `project_id` = task project (not overwritten by the BoM compute), `origin` = task name, linked in `task.mrp_production_ids`; (b) Buy-Goods-free: the task has no `buy_goods_ids` field; (c) `action_confirm` returns an action whose domain selects the task's MOs and whose name contains the count; (d) `action_view_mrp_productions` domain returns exactly the task's MOs; (e) wizard `user_id` is required (create without it raises).
- [X] T015 [US1] Run the module gate and fix failures for `serichai_project_mo` (views load, tests T014 pass).

**Checkpoint**: US1 works end to end as a project user with MRP rights.

---

## Phase 4: User Story 2 - No duplicates on re-run (P1)

**Goal**: Re-runs, double clicks and added products never duplicate MOs (FR-007, FR-008).
**Independent test**: run twice, second run creates none; add a 4th product, only one new MO; cancelled-only product is recreated.

- [X] T016 [P] [US2] Write tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`: rerun on an unchanged task creates 0 MOs and the wizard returns the "nothing new" notification; adding a 4th product creates exactly 1 MO; a product whose only MO is cancelled gets a new MO; a manually linked non-cancelled MO (via `mrp_production_ids`) counts as coverage; two sequential confirms leave no duplicates.
- [X] T017 [US2] Verify and, if needed, adjust the coverage logic in `serichai-odoo/serichai_project_mo/models/project_task.py` (`_create_mos_from_finish_goods`) so T016 passes: coverage = non-cancelled MO linked to the task for the same product; cancelled MOs never count; the lock and the task-row write stay in place.
- [ ] T018 [US2] Run the module gate; then run the two-session manual concurrency check from `specs/011-task-create-mo/quickstart.md` (section 8) and record the result in the quickstart notes if it differs from expectation.

**Checkpoint**: US1 + US2 safe to re-run.

---

## Phase 5: User Story 5 - Right people can use the button (P1)

**Goal**: Project users can use the feature; users without MO create rights still can after the task-write check (FR-017, FR-019). No new rule, no change to `serichai_project_security`.
**Independent test**: a project user without MRP rights creates MOs on a task they can edit; a user without task write is refused with 0 MOs.

- [X] T019 [P] [US5] Add tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py` for a project user WITHOUT `mrp.group_mrp_user`: creation works when the task is writable; `create_uid` of the MOs is the acting user; a user lacking task write raises `AccessError` from `action_open_create_mo_wizard` and `_create_mos_from_finish_goods`, with 0 MOs created.
- [X] T020 [US5] Run the module gate (`-u serichai_project_mo`); confirm `serichai-odoo/serichai_project_security/` is untouched (`git status` in `serichai-odoo/` shows no changes there).

**Checkpoint**: P1 stories complete.

---

## Phase 6: User Story 3 - Clear errors and warnings (P2)

**Goal**: Plain errors when no Finish Goods or no project, and a warning naming products without a BoM (FR-004, FR-011).
**Independent test**: Create MO on a task without Finish Goods / project gives a clear error and 0 MOs; a BoM-less product shows the warning but can still be confirmed.

- [X] T021 [US3] Implement `_compute_warning` in `serichai-odoo/serichai_project_mo/wizard/project_task_create_mo.py` per design.md 4.1: `@api.depends('task_id.finish_goods_ids')`; look up BoMs with `self.env['mrp.bom'].sudo()._bom_find(products)` (why-comment: the restricted role cannot read `mrp.bom`; only product names are exposed); text "No bill of materials for: %s. Their MOs will have no components." naming only BoM-less products; `False` when none.
- [X] T022 [P] [US3] Add tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`: `UserError` with a clear message from `action_open_create_mo_wizard`, wizard `action_confirm` and `_create_mos_from_finish_goods` for a task with no Finish Goods and for a task with no project (0 MOs each); the warning names only BoM-less products, is empty when all have a BoM, and confirming with a warning still creates the MOs.
- [X] T023 [US3] Run the module gate.

---

## Phase 7: User Story 4 - Email the project manager when all MOs are done (P2)

**Goal**: One email to the project manager when the last non-cancelled MO of a project is done; selectable template; resets per batch (FR-012 to FR-016, FR-020).
**Independent test**: Project with 2 MOs: first done = no mail; second done = exactly one mail to the manager.

- [X] T024 [P] [US4] Create `serichai-odoo/serichai_project_mo/data/project_project_data.xml` (`noupdate="1"`): `mail.template` with id `mail_template_all_mos_done`, name "All finished goods produced", `model_id` `project.model_project_project`, `partner_to` `{{ object.user_id.partner_id.id }}`, subject `{{ object.name }}: all finished goods produced`, simple `body_html` stating all manufacturing orders of the project are done, `lang` from the manager partner.
- [X] T025 [US4] Implement in `serichai-odoo/serichai_project_mo/models/project_project.py`: `mo_done_mail_template_id` (Many2one `mail.template`, string "All MOs Done Email", domain `[('model', '=', 'project.project')]`, default = `serichai_project_mo.mail_template_all_mos_done` with `raise_if_not_found=False`, `ondelete='set null'`) and `mo_done_mail_sent` (Boolean, `copy=False`, technical, not shown); methods `_reset_mo_done_mail_sent()` and `_check_all_mos_done()` per design.md 4.1: `sudo()`, skip projects already flagged, `try_lock_for_update(allow_referencing=True)` then re-read the flag, no manager = continue WITHOUT setting the flag (FR-016), count non-cancelled MOs with `search_count` (non-empty and none with `state != 'done'`), choose the project template or fall back to the default template, `template.send_mail(project.id, force_send=False)`, then set `mo_done_mail_sent = True`. Each `sudo()` carries a why-comment (outcome must not depend on the acting user's rights, FR-020).
- [X] T026 [US4] Edit `serichai-odoo/serichai_project_mo/models/mrp_production.py` (keep the existing `project_task_ids` M2M untouched): override `create` (`@api.model_create_multi`; reset the flag via `projects.sudo()._reset_mo_done_mail_sent()` then `_check_all_mos_done()`), `write` (watch `state` and `project_id` in vals; reset when `project_id` is written; check both old and new projects), `_action_cancel` (check after `super()`) and `unlink` (capture projects before deletion, check after). `write` without `state`/`project_id` must do no project queries.
- [X] T027 [P] [US4] Create `serichai-odoo/serichai_project_mo/views/project_project_views.xml`: inherit `project.edit_project`, add a group "Manufacturing" with `mo_done_mail_template_id` (`no_create`) inside the `settings` page (verify the page name in the core view; adjust the xpath if it differs).
- [X] T028 [P] [US4] Add tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py` (count `mail.mail` addressed to the manager partner): 2 MOs, first done = 0 mails, second done (through `button_mark_done`) = 1; an open MO = 0; all MOs cancelled = 0; repeated check = still 1; creating a new MO (also a manual one) and finishing it = a second mail; writing an MO into a project resets the flag; no manager = 0 mails and flag False, then setting a manager and re-checking sends one; chosen template used, empty template falls back to the default; cancel and unlink of the last open MO trigger the check; the default template exists and is the default on new projects; the template field domain only lists `project.project` templates; a triggering user without mail rights still yields the mail.
- [ ] T029 [US4] Run the module gate; then perform the manual email check from `specs/011-task-create-mo/quickstart.md` (outgoing mail queue / Discuss).

---

## Phase 8: Polish and Cross-Cutting

- [X] T030 [P] Update the `serichai_project_mo` section of `/home/odoo/serichai-odoo/CLAUDE.md` (Finish Goods field, Create MO wizard, "all MOs done" email on `project.project`, new `project_mrp`/`mail` dependencies, and fix the stale `action_view_mrp_productions` statement). Do not touch the Git attribution section.
- [X] T031 [P] Update `serichai-odoo/README.md` only if it lists addon features or dependencies (check first; skip if it does not).
- [ ] T032 Run the full module gate with `-u serichai_project_mo`, then run `specs/011-task-create-mo/quickstart.md` end to end (upgrade command, manual flow as a project user, access check as a user without task write).
- [X] T033 Self-review against design.md section 5: confirm every `sudo()` has a why-comment, there is no raw SQL, `odoo/` and `muk_web_theme/` are unchanged, and report any deviation from design.md.

---

## Dependencies and Execution Order

- **Phase 1** Setup: no dependencies; T002, T003, T004 are parallel after T001.
- **Phase 2** Foundational: depends on Phase 1. T005 to T008, T011 edit the same file (`project_task.py`) and must run in order; T009 and T010 are parallel with them (different files).
- **Phase 3** US1 (MVP): depends on Phase 2. T013 and T014 are parallel; T012 edits the task view.
- **Phase 4** US2: depends on US1 (same creation method).
- **Phase 5** US5: depends on Phase 2 (ACL and wizard); independent of US2 code, but share `test_create_mo_from_task.py` with other stories, so test tasks that edit that file must be serialized.
- **Phase 6** US3: depends on Phase 2 (wizard). Independent of US2/US4.
- **Phase 7** US4: depends on Phase 1 (project_project shell) and is independent of the wizard stories; T024, T027 are parallel; T025 precedes T026 and T028.
- **Phase 8** Polish: after all desired stories.

Story order by priority: US1 (P1) -> US2 (P1) -> US5 (P1) -> US3 (P2) -> US4 (P2).

## Parallel Examples

- After T001: T002, T003, T004 together.
- Phase 2: T009 (CSV) alongside T005-T008 (task model) and T010 (wizard model).
- Phase 7: T024 (template XML) and T027 (project view) while T025/T026 are implemented.

## Implementation Strategy

- **MVP**: Phases 1, 2 and 3 (US1): Finish Goods field, wizard, one MO per product. Validate manually as a project user.
- **Increment 2**: US2 and US5 (the remaining P1): safe re-runs and access checks, then deploy-ready for production planners.
- **Increment 3**: US3 (messages) and US4 (email), then Polish (docs, full quickstart).
- Run the module gate at every checkpoint; the test files are shared, so serialize edits to `serichai_project_mo/tests/test_create_mo_from_task.py`.

---

## Phase 9: Convergence

- [X] T034 Add edge-case tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`: (a) moving the task to another project after MOs exist leaves the existing MOs in their original project, and a later Create MO (after adding a product) creates the new MO in the task's current project; (b) removing a product from Finish Goods after its MO was created leaves that MO unchanged (no cancel, no unlink) per spec Edge Cases (partial)

---

## Phase 10: Review follow-ups (human gate feedback)

User feedback at the review gate: fix the remaining review findings, hide the Create MO button, warn when the template is missing, sync spec and design to the code the user edited by hand (rich "all MOs done" email template named "Project MO Complete Email Template", `i18n/th.po` Thai labels), then make the code cleaner and easier for humans to read, and review again.

- [X] T035 Sync `specs/011-task-create-mo/spec.md`, `plan.md`, `design.md`, `data-model.md`, `research.md` and `quickstart.md` to the hand-edited code: the email template record is named "Project MO Complete Email Template", has a rich body (project, manager, count and table of done MOs with product and quantity, "View Project in Odoo" link), and `i18n/th.po` ships Thai labels. Business wording only in `spec.md`.
- [X] T036 [P] Hide the Create MO button from users who cannot use it: in `serichai-odoo/serichai_project_mo/views/project_task_views.xml` restrict the button to `groups="project.group_project_user"` (UI only; the server check stays) (review #8).
- [X] T037 [P] Log a warning and skip cleanly when no usable email template exists in `serichai-odoo/serichai_project_mo/models/project_project.py` (`_logger.warning`, flag stays unset) and add a test in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`.
- [X] T038 Narrow the email-check triggers in `serichai-odoo/serichai_project_mo/models/mrp_production.py` so the check (project lock plus counts) runs only when an MO becomes done or cancelled, is unlinked, or changes project, not on every create or write (review #4); add tests.
- [X] T039 Cover compute-only changes in `serichai-odoo/serichai_project_mo/models/mrp_production.py`: a `state` that becomes done or cancel through its compute (design R4) and a `project_id` moved by the BoM compute (review #3) must also run the check and flag reset; prefer one small deferred, per-transaction-deduplicated scheduling helper over scattered calls; add tests (review #3, R4).
- [X] T040 Make the default email template visible and consistent for existing projects (review #9): set it on existing projects at install through `serichai-odoo/serichai_project_mo/data/project_project_data.xml` (idempotent function) and add help text in `serichai-odoo/serichai_project_mo/views/project_project_views.xml` / `models/project_project.py` saying that an empty field uses the default template; add a test.
- [X] T041 Readability pass over `serichai-odoo/serichai_project_mo/` (models, wizard, views, tests): split long methods into small named helpers, remove duplication (for example the two notification dicts in the wizard), remove stale comments (for example the mention of restricted roles), keep Odoo 19 conventions and class order, add short docstrings where intent is not obvious, keep behavior unchanged.
- [X] T042 [P] Complete the translations: export `serichai-odoo/serichai_project_mo/i18n/serichai_project_mo.pot` and add the missing msgids to `serichai-odoo/serichai_project_mo/i18n/th.po`, keeping the existing Thai strings verbatim and leaving a msgstr empty where a safe translation is not obvious.
- [X] T043 Run the module gate (`-u serichai_project_mo` on the throwaway database) and fix failures.

- [X] T044 Make the all-MOs-done check never roll back or veto a user's MO change (review #1): in `serichai-odoo/serichai_project_mo/models/project_project.py`, when the project row is locked by another transaction do not raise `SerializationFailure`; keep the business write and guarantee a later re-check (for example a queued job/cron trigger that re-runs `_check_all_mos_done` for the skipped projects); add tests in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`.
- [X] T045 Remove the double handling and the copied `@api.depends` in `serichai-odoo/serichai_project_mo/models/mrp_production.py` (review #3, #5): one small place decides "state became done/cancel" and "project changed", used by `write` and the compute paths alike; the `_compute_state` and `_compute_project_id` hooks must not duplicate core's dependency list (for example hook the recomputed values after `super()` through a method that does not redeclare `@api.depends`, or another clean mechanism verified against Odoo 19) and must also cover an MO created directly in done state; add tests.
- [X] T046 Re-sync `specs/011-task-create-mo/design.md`, `plan.md`, `research.md`, `quickstart.md`, `spec.md` (only if behavior wording changes) and the email bullet of `/home/odoo/serichai-odoo/CLAUDE.md` to the final T044/T045 design, then run the module gate.

- [X] T047 Suppress the upgrade email: in `serichai-odoo/serichai_project_mo/data/project_project_data.xml` (install-time function next to the default-template assignment) and `serichai-odoo/serichai_project_mo/models/project_project.py`, set `mo_done_mail_sent = True` at install for projects that already have non-cancelled MOs that are all done, so the first cron run sends nothing for them; add a test in `serichai-odoo/serichai_project_mo/tests/test_create_mo_from_task.py`.
- [X] T048 Small cleanups: in `serichai-odoo/serichai_project_mo/models/mrp_production.py` compare `mo.project_id.id or None` against the SQL snapshot (no spurious project-change branch) with a test; add a Thai translation for the email subject in `serichai-odoo/serichai_project_mo/i18n/th.po` (and the `.pot`) keeping the existing strings verbatim.
- [X] T049 Format the MO quantity in the email table of `serichai-odoo/serichai_project_mo/data/project_project_data.xml` with the usual number formatting for the recipient's language/UoM precision instead of raw values like `1.0` (touch only that cell of the user's hand-edited template), add a test that renders the mail, then re-sync `specs/011-task-create-mo/design.md`, `quickstart.md`, `spec.md` (business wording only if needed) and the `CLAUDE.md` email bullet, and run the module gate.

- [X] T050 Make T040 and T047 effective on the live upgrade path (`-u`, where Odoo skips `<function>` tags in noupdate data files): bump the version in `serichai-odoo/serichai_project_mo/__manifest__.py` (keep its CRLF line endings) and add `serichai-odoo/serichai_project_mo/migrations/<new-version>/post-migration.py` that calls the existing install-time functions (`_set_default_mo_done_mail_template` and `_mark_completed_projects_as_notified`, both idempotent), so existing projects get the default template and already-complete projects are not notified retroactively; keep the install-time `<function>` calls for fresh installs; test the migration function on fixtures; re-sync `specs/011-task-create-mo/design.md`, `quickstart.md`, `plan.md` and the `CLAUDE.md` email bullet.
