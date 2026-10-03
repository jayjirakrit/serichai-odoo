# Attendance Multi-Rate Overtime (`hr_attendance_ot_multiplier`)

Splits every `hr.attendance` record's worked time into three pay categories —
**Normal**, **OT 1.5x**, and **OT 2x** — computed automatically from the
employee's wage type and the day the work happened on. The pay-rate time
windows are configuration data, not code, so HR staff can add or change a
rule from the UI without a developer or a deployment.

This addon only extends `hr_attendance`/`hr.employee` (via `_inherit`). It
does not modify any vendored `odoo/` core file, and it does not replace or
interfere with core's own overtime-approval fields (`overtime_hours`,
`validated_overtime_hours`) or its `hr.attendance.overtime.rule` engine —
those keep working exactly as before, in parallel.

## Core concepts

- **Wage Type** (`hr.employee.wage_type`): `Daily Paid` or `Monthly Paid`.
  Set on the employee's form (HR Settings tab, next to Employee Type). If
  left unset, all of that employee's worked hours are recorded as Normal
  pay (0 overtime) and a warning is logged — attendance never errors just
  because a wage type hasn't been set yet.
- **Day Type**: `Weekday` (Mon–Sat, not a public holiday) or
  `Sunday/Holiday` (any Sunday, or a date covered by a company/calendar-wide
  `resource.calendar.leaves` record — Odoo's existing mechanism for public
  holidays). Stored on each attendance record (from the check-in date); an
  overnight shift is still split and evaluated per calendar date internally,
  even though the record shows one label.
- **Overtime Rule** (`hr.attendance.ot.rule`): one configurable time window
  — Attendances → Overtime Rules (top-level, next to Configuration/Reporting,
  visible and fully editable by both HR Officers and Managers).

## The 8 default rules

| Wage Type | Day Type | Window | Pay Category | Notes |
|---|---|---|---|---|
| Daily Paid | Weekday | 08:00–17:00 | Normal | |
| Daily Paid | Weekday | 18:00–22:00 | OT 1.5x | Catch-outside: also covers time before 08:00 or after 22:00 |
| Daily Paid | Sunday/Holiday | 08:00–12:00 | Normal | |
| Daily Paid | Sunday/Holiday | 12:30–16:30 | OT 2x | No catch-outside rule for this group — the 12:00–12:30 gap, and anything before 08:00 or after 16:30, is intentionally unpaid |
| Monthly Paid | Weekday | 08:00–17:00 | Normal | |
| Monthly Paid | Weekday | 18:00–22:00 | OT 1.5x | Catch-outside: also covers time before 08:00 or after 22:00 |
| Monthly Paid | Sunday/Holiday | 08:00–16:30 | Normal | |
| Monthly Paid | Sunday/Holiday | 16:30–24:00 | OT 2x | Catch-outside: also covers time before 08:00 |

## Adding or changing a rule — no code required

1. Go to **Attendances → Overtime Rules**.
2. Click **New**, or open an existing rule.
3. Set:
   - **Wage Type** / **Day Type** — which group of employees/days this rule applies to.
   - **From** / **To** — the local clock-time window (24h format).
   - **Pay Type** — which bucket (Normal / OT 1.5x / OT 2x) this window's hours go into.
   - **Catch Outside** — check this if the rule should *also* absorb worked
     time in its wage-type/day-type group that falls **outside the outer
     boundary** of every rule in that group (the earliest start to the
     latest end). It does **not** sweep up gaps *between* two rules' own
     windows — see "How catch-outside actually works" below.
   - **Sequence** — evaluation order among rules in the same group; matters
     only when more than one rule in a group is flagged Catch Outside (the
     lowest sequence one wins).
4. Save. The next time an attendance record's check-in/check-out/employee
   wage type changes (or a new one is created), it's evaluated against the
   current rules — no restart, no code change, no reinstall.

Deactivate a rule instead of deleting it if you might need it again later
(the **Active** field on the form; inactive rules simply stop being matched).

### How catch-outside actually works

Every rule's own window always counts, whether or not it's flagged
catch-outside. The flag adds one extra thing: time in that wage-type/day-type
group that falls **before the earliest rule's start or after the latest
rule's end** (the group's "outer boundary") is added to the lowest-sequence
catch-outside rule's bucket. Time that falls **between** two rules — inside
the boundary but not inside any rule's own window — is left unpaid, exactly
like the Daily Paid Sunday/Holiday 12:00–12:30 gap. This is why the default
Weekday rules (Normal ends 17:00, OT 1.5x starts 18:00) leave 17:00–18:00
unpaid rather than treating it as overtime — the gap is inside the group's
08:00–22:00 boundary, not outside it.

If a group has no catch-outside rule at all (the default Daily Paid +
Sunday/Holiday combination), nothing beyond each rule's own window is ever
counted — everything else that day is unpaid.

## Where to see the results

- **Attendance list** (Attendances → main list): Normal Hours, OT 1.5x Hours,
  OT 2x Hours, and Day Type appear right after "Worked Extra Hours" (Day
  Type and the two overtime columns are hidden by default — use the column
  toggle to show them). Existing grouping (e.g. Date:Month, then Employee)
  shows correct totals per group.
- **OT Analysis** (Attendances → Reporting → OT Analysis): a pivot table by
  Employee and Day Type, measuring all three buckets.
- **Export**: all four fields are standard stored fields, so they're
  selectable in Odoo's normal Export wizard (CSV and Excel) like any other
  attendance field.

## Historical data

Installing this module backfills the four new fields on every attendance
record that already existed (in batches, so it doesn't do one huge
operation) — you don't need to touch old records by hand.

## Multi-company

Both the rules and the computed hours respect company boundaries — an
employee is only ever matched against overtime rules belonging to their own
company.
