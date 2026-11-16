# Quality Report: 011-task-create-mo

**Verdict: PASS WITH NOTES** (delta review of the final code: T047-T050 install/upgrade setup, quantity format, Thai subject, version 1.1.1)

## Acceptance criteria

| ID | Result | Evidence |
|---|---|---|
| US1 (1-6) button, dialog, assignee required, create, cancel, notice | met | `project_task_views.xml` (`invisible="not finish_goods_ids"`, group `project.group_project_user`); wizard `required=True`; `test_wizard_assignee_required`, `test_create_one_mo_per_finish_good`. Button visibility is view-level only, with no UI test |
| US2 (1-4) no duplicates | met | `test_rerun_creates_nothing`, `test_added_product_creates_one`, `test_cancelled_mo_is_recreated`, `test_manual_link_counts_as_coverage`, `test_sequential_confirms_no_duplicates`. The concurrent case relies on `lock_for_update` plus a task write (`project_task.py:_create_mos_from_finish_goods`) and has no automated test (T018, manual) |
| US3 (1-3) errors, BoM warning | met | `test_wizard_open_without_finish_goods`, `..._without_project`, `test_warning_names_only_bomless_products`, `test_confirm_with_warning_still_creates` |
| US4 (1-7) email | met | `test_mail_after_last_mo_done`, `test_open_mo_no_mail`, `test_all_cancelled_no_mail`, `test_repeated_check_sends_once`, `test_new_mo_starts_new_batch`, `test_no_manager_no_mail_and_flag_unset`, `test_default_template`, `test_chosen_template_used`, `test_missing_template_logs_warning_and_leaves_flag_unset` |
| US5 (1-4) rights | met | `test_project_user_without_mrp_rights`, `test_user_without_task_write_refused`, `test_trigger_user_without_mail_rights`; `check_access('write')` runs before `sudo()` |
| FR-001..008, 010..017, 019..020 | met | tests above; FR-009 and FR-018 intentionally removed |
| FR-021..023 (compute hooks, deferred check, template) | met | `test_state_change_by_compute_triggers_check`, `test_project_changed_by_bom_compute_resets_flag_and_checks`, `test_one_check_per_project_per_transaction` |
| SC-002 | met in tests | the concurrent case needs T018 (manual) |

## Gates

- `odoo-bin -d serichai-test-011 -u serichai_project_mo --test-enable --test-tags /serichai_project_mo` -> 58 tests (as reported by the implementing agent after the cron removal; not re-run by the reviewer), 1 failed. The failure is `TestContractMoReport.test_render_empty_task`, known, pre-existing, fails on untouched HEAD. All 011 tests pass; the gate is red only because of that test.
- `th.po` parses with polib (51 entries, 0 fuzzy, 43% translated). `msgfmt` is not installed.
- Manual T018, T029 and T032 (two-session concurrency, real email, end-to-end quickstart) are not done. They are human-only steps.

## Findings

### Critical / Major
none

### Minor
1. `i18n/th.po` · odoo · The subject is now translated (T048). The rich email `body_html` still has no Thai translation, so the email body renders in English for a Thai-language manager (45% translated, 51 entries, 0 fuzzy, parses with polib). Suggested fix: translate the body, or document it as English-only. Spec ref: none.
2. `views/project_task_views.xml:10-11` · odoo · The diff adds `type="object" name="action_view_mrp_productions"` to the existing smart button. This is a collateral fix for an unwired button. It is documented in CLAUDE.md, so it is acceptable, but it is outside the 011 scope. Surgical principle: note only.
3. Concurrency (changed) · odoo · `_check_all_mos_done` never raises on a lock miss: it logs at info level and skips the locked project (the recheck cron was removed at the user's request). Trade-off: if two sibling MOs finish at the same instant and each sees the other as open, that project gets no email until its next MO change (design R8). The flag re-read after the row lock plus the flag claim still prevent a double mail. A real two-session race is only covered by T018 (manual).
4. `project_project.py:_run_scheduled_all_mos_done_check` · odoo · The pending set is popped before the check runs. If the check raises, a retry re-schedules it, because the data is per-transaction. This is correct, no action needed.
5. `ir.model.access.csv` · odoo · The wizard ACL is `project.group_project_user` only, with full CRUD on a transient model. This matches FR-017. The restricted role from `serichai_project_security` is out of scope.
6. `project_task.py:_create_mos_from_finish_goods` · odoo · The assignee is not validated server-side against MRP users (the code comment says so). This matches core behaviour, so there is no action needed.
7. `mrp_production.py:_on_tracked_fields_changed` · odoo · Fixed (T048): `mo.project_id.id or None` now matches the SQL snapshot. Resolved.
8. `_write_multi` hook · odoo · The snapshot SQL is parameterised (`WHERE id IN %s` with a tuple of ints), selects three columns by id, has no user input, and is needed to read the pre-write DB values (the ORM cache is already updated). It runs one query per write batch and is skipped when neither tracked field is in `vals_list`. It bypasses record rules, which is intended. It covers `write()` and the flush of computed stored fields, so single-field writes are included. Direct `_write` calls and raw SQL in core would bypass it, but no such path exists for these fields. No issue.
9. Upgrade path · odoo · The retroactive-mail risk is handled (T047, T050): `_mark_completed_projects_as_notified` flags already-complete projects (idempotent, tested by `test_upgrade_migration` and the mark test). The migration `migrations/19.0.1.1.1/post-migration.py` follows Odoo's loading order (`post` runs after data load). Databases that already installed the earlier cron keep a leftover scheduled action "Project: re-check all MOs done"; delete it by hand.
10. (superseded) The earlier finding about the recheck cron window no longer applies: the cron was removed.

## Security review
- `check_access('write')` as the real user runs before every `sudo()` path (open and confirm). Each `sudo` has a justification comment.
- `create_uid` stays the real user because `sudo()` keeps the uid.
- The wizard BoM lookup is sudo and exposes only product names. The flag reset and the check use sudo (FR-020), and the mail is queued with `force_send=False`.
- Email template: all dynamic values go through `t-out` (escaped) and are null-safe (`user_id.name or ...`, `object.name or '-'`). `partner_to` uses `object.user_id.partner_id.id`, and the check skips projects without a manager. The `t-attf-href` uses `get_base_url()`, so there is no user-controlled URL. The XML is valid, since the module loaded and the render tests pass. The template body is read through the test-covered `test_default_template`, which renders it, but no test inspects the rendered HTML for the MO table. Minor, with no action.
- There are no injection, file handling or secrets issues. The added dependencies, `project_mrp` and `mail`, are core.

## Conformance, readability, docs
- The code splits into small helpers (`_snapshot`, `_on_tracked_fields_changed`, `_all_mos_done`, `_send_mo_done_mail`). No dead code was found.
- `/home/odoo/serichai-odoo/CLAUDE.md` matches the final behaviour (deferred precommit check, compute hooks, template, th.po, `type = 'consu'`).
- Manifest version is 1.1.1 (HEAD has 1.0.0; the working tree was 1.1.0 before T050, so the bump is by the 011 work, not an outside edit). The manifest keeps CRLF, except the new `data/project_project_data.xml` line, which has LF only (mixed endings, cosmetic; the data file itself is LF with no CR). Fix by adding CRLF to that line.
- The email template quantity cell now uses `t-options` float with `decimal_precision` `Product Unit` (`test_mail_quantity_is_formatted`, 2 digits). I could not diff the rest of the template against the user's original, because no copy of it exists in git or the specs. The remaining markup reads as one structure and its render tests pass. Please confirm with the user's source.
- No stale statements found in CLAUDE.md or the 011 docs (no Serialization, no 1.0.0 and no `mail_template.xml`). CLAUDE.md describes the install and upgrade setup (the post-migration). No unused imports in the migration. A pyflakes check was not run (not installed).
- `data/project_project_data.xml` (rich template body with `t-out`/`t-foreach`) and `i18n/th.po` are intact and parse. The email subject still has no Thai translation (finding 1).
- `spec.md`, `plan.md`, `design.md` and `quickstart.md` agree with the code on the points I checked (FR-021..023, deferred check).
- No Buy Goods field exists (`test_no_buy_goods_field`).

## Pending (human)
- T018 (concurrent confirm and concurrent last-MO done), T029 (real email delivery) and T032 (quickstart end-to-end).
