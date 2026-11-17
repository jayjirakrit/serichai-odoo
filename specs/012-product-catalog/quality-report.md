# Quality Report: 012 Product Catalog (amended, US6 / FR-023..034 / SC-009..012)

> **Closed 2026-11-18.** This report predates the no-OWL rework (native views, standard search, photo editing) and was not refreshed; the Python gate was re-run after the rework (24 tests, 0 failed). Browser verification was not performed.

**Verdict: PASS WITH NOTES.** Python gate green. Browser-only checks (tour, hoot, manual walk) could not run here and remain unverified.

## Gates
- `odoo-bin -d serichai-test-012 -u serichai_product_catalog --test-enable --test-tags /serichai_product_catalog` → pass: 0 failed, 0 errors, 24 tests counted (28 in stats), re-run after the toolbar and hero changes, no ERROR lines in the log. Throwaway DB only; serichai-db untouched.
- Tour `test_catalog_tour`, hoot `catalog_toolbar.test.js`, T028/T029/T046/T047 → not run (no headless Chrome or manual walk). Unverified, not failures.

## Acceptance criteria
| ID | Status | Evidence |
|---|---|---|
| US1, FR-001..007, FR-020 | met | kanban, list and search views; `test_search_by_name_reference_barcode`, `test_action_views_load_for_internal_user` |
| US2, FR-009, FR-015, FR-016 | met | form view; `test_form_view_has_spec_first_tab`, `test_open_standard_form_returns_record_action` |
| US3, FR-014, SC-005 | met | `description` split by group (views xml:112-119); `test_manager_can_write_description`, `test_plain_user_cannot_write_description`, `test_get_view_description_editable_per_role` |
| US4, FR-011/012, SC-004 | met | purchase page `groups`; `test_purchase_page_stripped_for_plain_user`, `test_list_export_disabled` |
| US6.1 / FR-023..025 (toolbar, Grid/List, counter) | met by code, behaviour unverified | `catalog_toolbar.js/.xml`, views registered with `display.controlPanel=false`; only the hoot and tour tests exercise it |
| US6.2-6.4 / FR-026..029 (card, list, hover, selected, Back restore) | met by code, visual unverified | scss `.o_selected`, row hover tint; selectedId kept via `useSetupAction.getLocalState`; search restore relies on the standard searchModel |
| US6.5 / FR-031/032 (tiles, pills, vendor table) | met by code | `catalog_tiles_field.js`, vendor list with Lead Time (days), right-aligned numbers in scss |
| US6.6 / FR-034 / SC-011 | met | cost, cost incl. tax and margin fields carry `groups=purchase.group_purchase_user`; `test_cost_fields_denied_for_plain_user`, `test_cost_nodes_per_role`, `test_web_read_form_spec_has_no_cost_for_plain_user` |
| US6.7 / FR-033 (tech table, attribute pills) | met by code | `o_serichai_product_catalog_tech`, `many2many_tags` pill style |
| FR-018 / SC-006 (no fixed colors) | met | `test_scss_has_no_hardcoded_colors`; grep finds only `rgba(var(--bs-primary-rgb), .xx)`; no hex or rgb literals in JS or XML |
| FR-017 | met | `test_standard_product_views_untouched`, `test_catalog_is_browse_only` |
| FR-021 / SC-012 (360/768/1280 px) | partial, static only | media queries at 575.98 and 767.98 px; needs the manual walk |
| FR-022 Thai | met | th.po has 46 msgids, none empty |
| SC-008 / SC-010 (5,000 products) | met for the server side | `test_perf_5000_products`; client update time unverified |
| SC-007 / SC-009 (mock sign-off) | unverified | human review (T047) |

## Security review
- No `sudo()` anywhere in the module. No new ACL, group or controller.
- Cost, cost incl. tax and margin are field-level group-restricted, and the tiles widget reads them only when present in the record data. Kanban and list never request `standard_price`. The form's `web_read` spec for a plain user was tested to carry none of them.
- The Specification is enforced by the ACL, not only by hidden controls. The form has `edit="true"` and the other fields are readonly. This is documented in the view comment.
- Category counts come from `formattedReadGroup` and the category tree from `searchRead` on `product.category` (`parent_of`), both as the caller, so ACL and company rules apply. No cost data is read. Re-checked after the toolbar change: no sudo, no new sensitive field.
- No secrets or PII in code or logs. No new dependencies.

## Findings
- resolved · `catalog_toolbar.js:loadCategories` · parent categories are now pickable and counts are child_of totals (own count plus descendants, ancestors via `parent_of` read as the caller), so they match the facet result. Counts still ignore the active text search (documented in the code comment); acceptable.
- resolved · `catalog_toolbar.js` · search text is flushed on Enter, blur and unmount (guarded against duplicate facets by comparing with the current query value).
- resolved · `catalog_hero_field.xml` · hero image alt is the record name.
- minor · odoo · `specs/009-project-access-matrix/quickstart.md`, `tasks.md` · unrelated edits (script rename `restore_odoo.sh`) bundled in this diff · Surgical principle · move to its own commit or confirm intentional.
- minor · odoo · `tests/test_catalog_tour.py`, `static/tests/catalog_toolbar.test.js` · never executed, so toolbar filtering, Back-restore, selected marking and category sync have no passing automated evidence · FR-023..029 · run T046 where headless Chrome exists.
- minor · odoo · `tasks.md` T028/T029/T046/T047 still open · by design, pending the user.
- note · CLAUDE.md and `.specify/memory/constitution.md` edits are consistent with the implementation (the constitution now calls for the tour and hoot gate). No conflicts found.

STATUS: done
COMPLETED: PASS WITH NOTES; /home/odoo/serichai-odoo/serichai-odoo/specs/012-product-catalog/quality-report.md
FAILED: none
FILES CHANGED: /home/odoo/serichai-odoo/serichai-odoo/specs/012-product-catalog/quality-report.md
VERIFICATION: Python gate on serichai-test-012 (`-u serichai_product_catalog --test-enable --test-tags /serichai_product_catalog`) → pass, 0 failed, 0 errors
VERIFICATION: tour, hoot, manual walk T028/T029/T046/T047 → not run (no headless Chrome / manual)
ASSUMPTIONS / DEVIATIONS: none
OPEN QUESTIONS: 1. Should the unrelated 009 doc edits be split from the 012 commit? 2. Should the category counts follow the current search?
