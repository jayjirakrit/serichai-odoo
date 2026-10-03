# Quickstart: Validating Multi-Rate Overtime Calculation

Prerequisites: repo `.venv` activated, `serichai-db` reachable, `run_odoo.sh` (or a manual
`odoo-bin` invocation) updated to include `serichai_hr_attendance` on `--addons-path`
alongside the other custom addons.

## 1. Install the module

```bash
source .venv/bin/activate
cd odoo
python3 odoo-bin \
  --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-db -i serichai_hr_attendance --stop-after-init
```

Expect no errors. This confirms:
- The addon installs cleanly depending only on `hr_attendance`.
- The 8 default `hr.attendance.ot.rule` records load (data/hr_attendance_ot_rule_data.xml, spec FR-004).
- The `post_init_hook` backfill runs against any pre-existing `hr.attendance` records without error (spec FR-020 / SC-005 — see `research.md` Decision 6).

## 2. Run the automated test suite

```bash
python3 odoo-bin \
  --addons-path=addons,../muk_web_theme,../serichai-odoo \
  -d serichai-db --test-enable --stop-after-init -u serichai_hr_attendance
```

Expect `tests/test_ot_rule_engine.py`, `tests/test_ot_backfill.py`, and `tests/test_ot_export.py`
to pass — see `contracts/compute-engine.md`'s Verification contract for exactly what each
scenario asserts (12 scenarios covering both wage types, both day types, overnight splitting,
the unpaid gaps, sub-30-minute rounding, missing wage type, and open attendance).

## 3. Manual end-to-end check

1. Start the server normally: `./run_odoo.sh` (after the addons-path update from Prerequisites).
2. Log in as an HR Officer/Manager user.
3. **Configure a wage type** (User Story 1 setup): Employees → open a test employee → set
   "Wage Type" to Daily Paid. Repeat for a second test employee with Monthly Paid.
4. **Review the default rules** (User Story 2): Attendances → Overtime Rules (top-level, alongside Configuration & Reporting — not nested inside Configuration, which is Manager-only).
   Confirm the 8 default rows are visible, grouped by wage type/day type, each showing its
   time window and pay category.
5. **Create attendance records** (User Story 1) for each test employee covering:
   - A plain weekday shift (e.g., 08:00–17:00).
   - A weekday shift into the evening OT window (e.g., 08:00–20:00).
   - A Sunday shift (e.g., 08:00–18:00).
   For each, open the record and confirm the Normal / OT 1.5x / OT 2x hours match
   `contracts/compute-engine.md`'s Verification contract.
6. **Check the list view** (FR-016/FR-017): Attendances list, confirm the new columns appear
   immediately after "Worked Extra Hours", `normal_hours` is visible by default and the other
   two + Day Type are available via the optional-columns toggle. Group by Date:Month then
   Employee (existing behavior) and confirm correct summed subtotals per group.
7. **Check the pivot view** (FR-018): open "OT Analysis" from the Attendances menu; confirm rows
   are Employee → Day Type and measures are the three hour buckets, with correct totals.
8. **Check export** (FR-019): from the attendance list, select a few records → Export → confirm
   Normal Hours, OT 1.5x Hours, OT 2x Hours, and Day Type appear in the field picker for both
   CSV and Excel export, and the downloaded file contains correct values.
9. **Edit a rule** (User Story 2): change the Daily Paid weekday OT 1.5x rule's start time from
   18:00 to 19:00, save. Create a new attendance record for a Daily Paid employee working
   08:00–20:00 and confirm the OT 1.5x total now reflects the updated boundary (1 hour instead
   of 2), with no code change or restart involved.
10. **Edge cases**: create/check an attendance with no check-out yet (confirm zero/blank
    hours, no error); clear a test employee's Wage Type and create an attendance for them
    (confirm all hours land in Normal, no error, and a warning appears in the server log).

## Expected outcome

Matches spec Success Criteria SC-001–SC-006: every attendance record with a wage type shows an
automatic, correct three-way hour split (including 30-minute-rounding and the intentional
unpaid gaps); rule edits take effect immediately with no deployment; the split is visible,
groupable, pivotable, and exportable; historical records are backfilled; and no record —
including open or missing-wage-type ones — errors or blocks saving.
