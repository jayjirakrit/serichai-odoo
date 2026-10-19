# Quality report: 010 project configuration (scope: full, area odoo)

**Verdict: PASS WITH NOTES** (no critical or major findings; re-verified after follow-ups T029-T033)

## Acceptance criteria

| ID | Result | Evidence |
|---|---|---|
| FR-001 depends only on project, 009 untouched | met | `__manifest__.py` depends `['project']`; no serichai reference in production code (grep); git status shows only the new addon and specs untracked; nothing under odoo/, muk_web_theme/, serichai_project_access newer than spec.md |
| FR-002/003/004 value parsing | met | `project_task.py:22-34` `parse_amount`, `is_value_property`; tests `test_parse_amount`, `test_char_property_flag`, `test_label_match_across_projects`, `test_duplicate_label_first_wins` |
| FR-005 strictly greater | met | `project_task.py:55`; `test_float_flag_and_threshold` (exactly 50M false) |
| FR-006 recompute only on own property / project change | met | `@api.depends('task_properties','project_id')` (no definition dependency); `test_definition_change_needs_recompute`, `test_move_between_projects`, `test_edit_value_updates_flag`, `test_settings_save_then_recalculate` (threshold change not automatic) |
| FR-007 never blocks, debug-only logging with task id | met | specific excepts, `_logger.debug(..., task.id)` at `project_task.py:57`, `:81`; `test_bad_task_does_not_stop_batch`, `test_denied_read_gives_zero_without_error` |
| FR-008/009 default order | met | `project_task_views.xml:7,24` order `priority desc, is_high_value desc, state, date_deadline asc, id desc` (matches spec FR-008/009, design, plan, data-model, research); `test_order_*`, `test_no_property_anywhere_order` |
| FR-010 order elsewhere unchanged | met (M1 fixed) | model `_order` untouched; portal base list `project_task_view_tree_main_base` not inherited; `test_model_order_and_portal_list_untouched` |
| FR-011 column re-sort | met | default_order is a view default only |
| FR-012 Project Value column optional=show | met | `project_task_views.xml:10`; `test_high_value_filter_and_view_arch` |
| FR-013 High Value filter | met | `project_task_views.xml:36` |
| FR-014 threshold incl. 0, fallbacks | met | `_get_high_value_threshold` (`:90-97`), `get_values`/`set_values` using repr so 0 is stored as "0.0"; `test_threshold_fallbacks`, `test_threshold_zero_is_real` |
| FR-015 recalculation, batches, one failure does not stop | met | `_recompute_high_value` (`:100-108`), `action_serichai_recompute_high_value`; the setting text tells the admin to run it (`res_config_settings_views.xml`); `test_recompute_batches_and_archived` |
| FR-016 admin only | met | block `groups="base.group_system"`, explicit `has_group` check in the action; `test_non_admin_cannot_recalculate` |
| FR-017 install in portions, succeeds without property | met | pre_init creates the column, post_init calls `_recompute_high_value`; `test_post_init_hook*`, `test_pre_init_hook_idempotent`; install ran clean |
| FR-018/019 hidden property, no leak | met | `project_value` goes through `read()`, so a hook on read zeroes it; AccessError gives 0; `test_hidden_property_gives_zero`, `test_denied_read_gives_zero_without_error` (read is simulated, see M2) |
| FR-020 no access weakening | met | no new model or ACL needed; sudo uses are commented and expose only a number or a flag |
| US1..US6, SC-001..SC-009 | met | covered by the tests above. SC-008 (portal) is checked structurally by the view test. SC-005/SC-006 and the live walkthrough (T026) are for the human reviewer, as agreed |

## Gates

- `odoo-bin -d serichai-test --test-enable -u serichai_project_configuration,serichai_project_access --test-tags /serichai_project_configuration,/serichai_project_access` → pass: "0 failed, 0 error(s) of 116 tests" (40 configuration + 76 access); no addon warnings
- Install/update without addon warnings → pass
- serichai_project_access re-run together with the configuration addon (76 tests, pass)
- Constitution gate used the throwaway DB `serichai-test`, not `serichai-db`, as instructed

## Findings

### Critical / Major
none

### Minor
Fixed and verified (delta): M1 (milestone/templates list and kanban views restore core order `priority desc, sequence, state, date_deadline asc, id desc` and drop project_value; test at `test_budget_sort.py:153-156`), M3, M4 (tests strengthened), M6 (pylint line removed). Also verified: `is_high_value` column created as boolean (`hooks.py:7`, `test_pre_init_hook_new_column_defaults_false`). Main views (`project_task_view_tree_base`, `view_task_kanban`, and the My/All/Default-project kanbans that inherit it) keep the new order.

Open, accepted notes:
- M2 · odoo · `tests/test_budget_sort.py` (US6) · hidden-property behaviour is simulated by patching `read`; no test uses the real serichai_project_access rules. Accepted by the dispatcher.
- M5 · odoo · `models/res_config_settings.py:19-23` · Settings save pins the threshold as an explicit value. Harmless. Accepted.
- T026 (manual UI walkthrough) remains open for the human. Known limits: kanban drag-and-drop, column not sortable, Recalculate needed after threshold/definition change, hidden users may infer high-value.

## Scrutiny notes (all checked, no defect)
- `_compute_is_high_value`: reads the threshold once per batch, uses specific excepts, logs only at debug with the task id, and the stored compute runs as superuser, so every user gets the same flag. Tasks without a project or with an empty value give False.
- `_recompute_high_value`: `active_test=False` and `sudo` are commented; `add_to_compute` → `flush_recordset` → `invalidate_recordset` per batch is correct. There is no commit, so it is safe inside the install hook.
- Threshold: 0 is honoured; negative, nan, inf, letters and empty fall back to 50,000,000 silently.
- Views: the kanban and the list (`view_task_tree2`) both resolve to the new `default_order`. The portal base list is untouched, the filter is placed before `open_tasks`, and the column has `optional="show"`.
- Translated strings use `self.env._` with literals only. There is no i18n folder, which is consistent with the sibling addons.
