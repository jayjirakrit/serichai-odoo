# Quickstart: Validating Expanded Task Access for Product Development

## Prerequisites

- Odoo running against `serichai-db` with `serichai_project_security` installed/upgraded
  (`-u serichai_project_security`), per repo root `CLAUDE.md` run instructions.
- A `project.project` record to pin (e.g. an existing or newly created "Product Development"
  project) and at least one `project.task` inside it, plus at least one task in a different
  project.
- Two users: one with only `group_project_task_list_only`, one plain internal user (control).

## 1. Pin the project (administrator)

1. Log in as an administrator, go to **Settings → (Serichai Project Security section)**.
2. Set the new "Expanded-Access Project" field to the project to pin, save.
3. Confirm: `ir.config_parameter` key `serichai_project_security.expanded_access_project_id`
   now holds that project's id (`Settings → Technical → System Parameters`, or
   `env['ir.config_parameter'].sudo().get_param('serichai_project_security.expanded_access_project_id')`
   in an Odoo shell).

## 2. Restricted user — expanded project

Log in (or impersonate) as the `group_project_task_list_only` user.

1. Open the new **"Product Development"** menu entry under the Project app.
   - **Expected**: only tasks belonging to the pinned project are listed.
2. Click a task row.
   - **Expected**: the full task form opens (not blocked).
3. Edit a field (e.g. change stage or description) and save.
   - **Expected**: save succeeds.
4. Attempt to create a new task from this view/list, and attempt to delete an existing one.
   - **Expected**: both refused (create/unlink stay out of scope everywhere).

## 3. Restricted user — every other project

Still as the restricted user:

1. Open the existing **"All Tasks"** menu entry.
   - **Expected**: tasks from all projects still listed (subject to the existing stage filter),
     including the pinned project's tasks.
2. Click a row belonging to a project other than the pinned one.
   - **Expected**: no form opens (row click is inert, same as before this feature).
3. Via the Odoo shell (or an RPC call) as this user, attempt to `write()` a field on a task in a
   non-pinned project.
   - **Expected**: `AccessError`.
4. Repeat step 3 for a task in the pinned project.
   - **Expected**: write succeeds — matches step 2.3 above, confirming the boundary is the
     project, not the entry point used to reach the record.

## 4. Regression — everything else unchanged

As the restricted user, re-run the pre-existing checks (now covered by
`tests/test_access_restriction.py`):

- Hidden menus (`Projects`, `Reporting`, `Configuration`) stay hidden.
- The Tags column stays hidden on the "All Tasks" list.
- "All Tasks" remains the default landing menu.

As the control (plain project) user: confirm nothing changed — full form access, all menus,
Tags column visible, on every project including the pinned one.

## 5. Automated tests

```bash
source .venv/bin/activate
cd odoo
python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo,../serichai_inventory \
  -d serichai-db --test-enable --stop-after-init -u serichai_project_security
```

Expect the updated `test_access_restriction.py` suite to cover: write allowed inside the pinned
project, write denied outside it, create/unlink denied everywhere, and all pre-existing menu /
column / landing-page assertions still passing unchanged.
