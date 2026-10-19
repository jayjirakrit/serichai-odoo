# Quickstart: validating 010-project-configuration

## 1. Automated tests (dedicated throwaway DB)

Do not run the tests against `serichai-db`. Ask the user for the test database name at
implementation time (shown below as `<test_db>`). Run from `odoo/`:

```bash
../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d <test_db> \
  --without-demo=all --no-http --test-enable --stop-after-init \
  -i serichai_project_configuration --test-tags /serichai_project_configuration
```

Expected: 0 failed, 0 errors, and no warnings during install. The check
`grep -rn "serichai_project_access\|_get_project_access" serichai_project_configuration/` must return
nothing (FR-001). Spec 009's own tests are unchanged. If 009 is installed on the test DB, its suite
still passes (`--test-tags /serichai_project_access`).

## 2. Deploy on `serichai-db` (run by the user, after review)

```bash
../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db \
  --stop-after-init -i serichai_project_configuration
```

- `serichai_project_access` does not need to be upgraded: it is not changed.
- Afterwards the user may run the constitution gate `-u serichai_project_configuration` with
  `--test-enable` against `serichai-db`. The tests write test records and roll them back.

## 3. Manual walkthrough (DB copy, as admin unless stated)

1. In a project, add a **Decimal** task property labelled `มูลค่าโครงการ`. Create these tasks:
   - A: 60,000,000, deadline next month
   - B: 40,000,000, deadline tomorrow
   - C: no value, deadline next week
   - D: 70,000,000, no deadline

   All Tasks (list) shows the order A, D, B, C (US1 independent test). Star C (priority): the order
   becomes C, A, D, B, because the priority star comes before the high-value sort. Unstar C again.
2. Open the project kanban. The same order applies in each stage column. Drag B above A and reload:
   B returns below A (known limitation).
3. Click the Deadline header and the list re-sorts. Reopen All Tasks: the default order is back
   (FR-011).
4. The "Project Value" column is shown and can be hidden. The "High Value" filter leaves only A and D.
5. In a second project, add a **Text** property labelled ` มูลค่าโครงการ ` (with spaces) and a task
   with `60,000,000`: it is high-value. Change the value to `abc`: the task saves, with value 0,
   sorted by deadline.
6. Move task A to a project without the property: at once it has value 0 and is not high-value.
7. Rename the property in project 1. The flags of untouched tasks stay as they were. The Project
   Value column already shows 0 (known limitation). Click **Recalculate high-value flag**: they leave
   the top.
8. Settings > Project > Task Sorting (a hint under the button says to recalculate after changes):
   - Set 30,000,000 and Save: B is not yet high-value. Click **Recalculate high-value flag**: it is.
   - Set 0, Save, and reopen Settings: it shows 0. After Recalculate, every task with a positive
     value is high-value.
   - Set `abc` through System Parameters and click **Recalculate high-value flag**: 50,000,000 is
     used, with no error.
9. Log in as a non-admin project user: there is no Task Sorting block.

## 4. User who cannot see the property (spec 009 installed, US6)

1. Project > Configuration > Project Access Group: create a department with a Read line on
   project 1 that hides the property `มูลค่าโครงการ`. Add a test user to its group.
2. As that user, hard refresh and open All Tasks.
   - The list loads without error, in the same order as for an admin (high-value first after
     priority).
   - The Project Value column shows 0 for project 1 tasks.
   - The High Value filter is offered and works (accepted).
3. Negative check, in a shell as that user: `read(['project_value'])` and an export of
   `project_value` return 0 for project 1 tasks, with no error.
4. Add a second line on project 2 that hides nothing. Project 2 amounts are shown in the column.

## 5. Install on a production copy (US5, SC-006)

Install on a restored copy (the section 2 command). Without editing anything, high-value tasks are at
the top of All Tasks. The portal task list and the Contract MO report keep their previous order
(SC-008).
