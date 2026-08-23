# Quickstart: Validating Task Property Group Visibility

Prerequisites: repo `.venv` activated, `serichai-db` reachable, `serichai_project_security` addon upgraded with this feature's changes.

## 1. Install / upgrade the module

```bash
source .venv/bin/activate
cd odoo
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory \
  -d serichai-db -u serichai_project_security --stop-after-init
```

Expect no errors; confirms the new model, views, menu, and access rows load cleanly.

## 2. Run the automated test suite

```bash
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory \
  -d serichai-db --test-enable --stop-after-init -u serichai_project_security
```

Expect all tests in `tests/test_access_restriction.py` (pre-existing) and the new
`tests/test_task_property_access.py` to pass — see `contracts/module-interface.md`'s
Verification contract for exactly what the new tests assert.

## 3. Manual end-to-end check

1. Start the server normally: `./run_odoo.sh`
2. Log in as an Administrator / Project Manager user.
3. On any project, add a task property (Properties widget on a task form) labeled, e.g., `Client Budget`.
4. Navigate to **Project → Configuration → Task Property Access** (new menu this feature adds) and create a rule: `property_string = "Client Budget"`, `group_ids = [Finance group]` (create/pick a test group if none exists).
5. Confirm the rule as an Administrator: reopen the task — `Client Budget` is still visible (Administrator group membership isn't required, only membership in one of `group_ids`, but Administrators typically hold broad groups — if not in the Finance group, this step should instead be checked with a Finance-group test user per step 6).
6. Log in as (or impersonate, e.g. via a second browser/incognito session) a user who **is** in the Finance group: open the same task — `Client Budget` is visible with its value.
7. Log in as a user who is **not** in the Finance group but has normal task access: open the same task (form view, then also the task list view with the Properties column, if configured) — confirm `Client Budget` does not appear anywhere, while every other property on the task still does.
8. Delete or deactivate the rule; reopen the task as the non-Finance user again — confirm `Client Budget` is now visible again, with no server restart.

## Expected outcome

Matches spec Success Criteria SC-002/SC-003/SC-004: restricted property is invisible outside its permitted groups across all views, fully visible to permitted users, and every unrestricted property and every user/task with no rules configured shows zero behavior change.
