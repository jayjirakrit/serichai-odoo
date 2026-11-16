# Quickstart: Create MOs from a Task

## Run the gate

```bash
cd /home/odoo/serichai-odoo/odoo
../.venv/bin/python3 odoo-bin --addons-path=addons,../muk_web_theme,../serichai-odoo -d serichai-db \
  --test-enable --stop-after-init -u serichai_project_mo --test-tags /serichai_project_mo
```
`project_mrp` and `mail` install automatically as dependencies on first update. Expect no warnings.
Known unrelated failure: `TestContractMoReport.test_render_empty_task` (fails on untouched HEAD).
Use a throwaway database (for example a copy named `serichai-test-011`) rather than the live one.

## Manual check (UI)

1. As a Project user: open a task in a project; the Manufacturing Orders tab has no Create MO button. Add 3 Finish Goods.
2. Press **Create MO**; Confirm with no assignee refused; pick one, Confirm: 3 Draft MOs, project and task set, assignee set.
   (A user who cannot read Manufacturing Orders sees an "N Manufacturing Orders created" toast instead of the list.)
3. Press again: "nothing new" notice. Cancel one MO, press again: one new MO.
4. Add a product without BoM: dialog warns, still creates.
5. Task without project / without Finish Goods (use server action or RPC): clear error.
6. Project form (Settings tab, Manufacturing group): the template field shows "Project MO Complete Email Template"
   (existing projects get it at install). Set a project manager, mark all non-cancelled MOs done: one queued email in
   Settings > Technical > Emails, appearing when the action completes (not during the MO write). Open it: it shows the project,
   the manager, "N done", a table of MOs with product and quantity, and a "View Project in Odoo" button. Create another MO,
   finish it: second email. Quantities read like `1.00 Units`, not `1.0`. Projects already complete when the module was installed or upgraded are not emailed retroactively (the `19.0.1.1.1` post-migration runs on `-u`).
7. As a project user without Manufacturing rights who can edit the task: Create MO works; as a user who cannot edit the task, the server refuses (try via RPC
   `project.task.action_open_create_mo_wizard`).
8. Double-click Confirm and, in two browser sessions, confirm at once: one set of MOs (second user may see "try again").
   Likewise finish two MOs of the same project in two sessions: exactly one email (in the rare simultaneous case a locked project is skipped and may get no email until its next MO change; there is no recheck cron).
9. Thai labels: switch the user language to Thai; the task form shows "สินค้าผลิต" (Finish Goods), the button "สร้างใบสั่งผลิต",
   and the dialog Assignee "ผู้รับผิดชอบ". Some texts (errors, template field label) still show English; that is expected.
