# Contract: OT compute engine (`hr.attendance` helper methods)

This addon has no HTTP/API surface. Its contract is the behavior of the compute method and
its three helper methods on `hr.attendance`, the shape of `hr.attendance.ot.rule` records they
read, and the view/export surfaces that expose the results. Downstream work (tasks.md, tests,
manual verification) should validate against the tables below rather than against
implementation prose.

## Method contract: `hr.attendance._compute_ot_hours()`

| Aspect | Contract |
|---|---|
| Trigger | `@api.depends('check_in', 'check_out', 'employee_id.wage_type')` — recomputes on check-in, check-out, or employee wage-type change (spec FR-007) |
| Writes | `day_type`, `normal_hours`, `overtime_150_hours`, `overtime_200_hours` on `self` |
| Open attendance (`check_out` falsy) | All four fields set to their empty/zero value; no error (spec FR-008) |
| No `employee_id.wage_type` set | `normal_hours` = full worked duration (rounded per FR-006); `overtime_150_hours` = `overtime_200_hours` = 0; a warning is logged; no error (spec FR-013) |
| Overnight shift | Internally split at each local midnight crossed; each segment matched against its own calendar date's day type; `day_type` field itself stores the **check-in date's** day type (research.md Decision 3) |
| Rounding | Each of the three totals is rounded down to the nearest 0.5 (30 minutes); a same-category remainder under 0.5 is dropped, never rounded up (spec FR-006) |
| No double counting | Across all matched rules for a segment, each minute contributes to at most one of the three buckets (spec FR-009/FR-010) |
| Company scoping | Only `hr.attendance.ot.rule` records where `company_id` matches `employee_id.company_id` are considered (spec FR-014) |

## Helper contract: `hr.attendance._get_day_type(date, employee)`

| Aspect | Contract |
|---|---|
| Input | `date`: a `date` (one calendar day); `employee`: `hr.employee` recordset (single record) |
| Return | `'weekday'` or `'sunday_holiday'` |
| Sunday | Always `'sunday_holiday'`, regardless of holiday calendar |
| Public holiday | `'sunday_holiday'` if `date` falls within any `resource.calendar.leaves` record with empty `resource_id` on `employee.resource_calendar_id` (research.md Decision 2) |
| Otherwise | `'weekday'` |

## Helper contract: `hr.attendance._interval_overlap(seg_start_hour, seg_end_hour, rule_from, rule_to)`

| Aspect | Contract |
|---|---|
| Input | Four floats in `[0, 24]`, local clock time, all within one calendar date |
| Return | Hours (float) of overlap between `[seg_start_hour, seg_end_hour)` and `[rule_from, rule_to)` |
| No overlap | Returns `0.0` |

## Helper contract: `hr.attendance._hours_outside(seg_start_hour, seg_end_hour, claimed_windows)`

| Aspect | Contract |
|---|---|
| Input | Segment time range plus a list of `(from, to)` windows to treat as covered — a general "time not in any of these windows" primitive |
| Return | Hours (float) of the segment not covered by any window in `claimed_windows` |
| Used by | Rule Precedence step 2 (data-model.md): called with a **single** window — the group's outer boundary, `[min(time_from), max(time_to)]` across every rule in the `wage_type`/`day_type` group — so it returns only time before or after that boundary, never an internal gap between two rules' windows. Feeds only the lowest-`sequence` `catch_outside` rule, if any. |

## View contract: `hr_attendance.view_attendance_tree` (inherited)

| Aspect | Contract |
|---|---|
| Inherited view | `hr_attendance.view_attendance_tree` |
| Insertion point | Immediately after the `overtime_hours` field (UI label "Worked Extra Hours"), before `validated_overtime_hours` (research.md Decision 4) |
| Adds | `normal_hours` (`widget="float_time"`, `optional="show"`, `sum="Total"`), `overtime_150_hours` (`widget="float_time"`, `optional="show"`, `sum="Total"`), `overtime_200_hours` (`widget="float_time"`, `optional="show"`, `sum="Total"`), `day_type` (`optional="hide"`) |
| Grouping | Existing groupby behavior (e.g. Date:Month > Employee) is untouched; Odoo's list view sums grouped totals automatically for any field with `sum=` — no custom aggregation code needed (spec FR-017) |

## View contract: new pivot view + "OT Analysis" menu

| Aspect | Contract |
|---|---|
| Model | `hr.attendance` |
| Rows | `employee_id`, `day_type` |
| Measures | `normal_hours`, `overtime_150_hours`, `overtime_200_hours` |
| Menu | New menu item under the Attendances app, labeled "OT Analysis" (spec FR-018) |

## Export contract (verification only — no new code)

| Aspect | Contract |
|---|---|
| Mechanism | Odoo's standard export wizard already lists every stored field on a model; no custom export code is added |
| Verification | An automated test opens the export wizard's field list for `hr.attendance` and asserts `normal_hours`, `overtime_150_hours`, `overtime_200_hours`, and `day_type` are present and selectable (spec FR-019) |

## Security contract: `hr.attendance.ot.rule`

| Aspect | Contract |
|---|---|
| `group_hr_attendance_manager` | Full CRUD (create/read/write/unlink) |
| `group_hr_attendance_officer` | Full CRUD (create/read/write/unlink) — opened up from core's own read-only `hr.attendance.overtime.rule` pattern, per explicit user decision |
| Other users | No access |
| Multi-company | A record rule restricts visibility to rules whose `company_id` is in the current user's allowed companies, mirroring `hr_attendance_rule_employee_company` |

## Verification contract (how to check compliance)

For a Daily Paid employee (`wage_type = 'daily'`) and a Monthly Paid employee (`wage_type = 'monthly'`), each on a calendar with no custom holidays configured beyond the default rule data:

1. `check_in` Mon 08:00 → `check_out` Mon 17:00, Daily Paid → `normal_hours == 9.0`, both OT buckets `== 0.0`.
2. `check_in` Mon 08:00 → `check_out` Mon 20:00, Daily Paid → `normal_hours == 9.0` (08:00–17:00), `overtime_150_hours == 2.0` (18:00–20:00), 17:00–18:00 gap uncounted, `overtime_200_hours == 0.0`.
3. `check_in` Mon 06:00 → `check_out` Mon 23:00, Daily Paid → time before 08:00 and after 22:00 is `overtime_150_hours` (catch-outside), `normal_hours == 9.0`.
4. `check_in` Sun 08:00 → `check_out` Sun 12:00, Daily Paid → `normal_hours == 4.0`, both OT buckets `== 0.0`.
5. `check_in` Sun 08:00 → `check_out` Sun 13:00, Daily Paid → `normal_hours == 4.0`, 12:00–12:30 gap uncounted, `overtime_200_hours == 0.5` (12:30–13:00).
6. `check_in` Sun 12:30 → `check_out` Sun 16:30, Daily Paid → `overtime_200_hours == 4.0`.
7. `check_in` Sun 08:00 → `check_out` Sun 18:00, Monthly Paid → `normal_hours == 8.5` (08:00–16:30), `overtime_200_hours == 1.5` (16:30–18:00).
8. Same shifts as #2 and #7 but on a non-Sunday date flagged as a public holiday (via a `resource.calendar.leaves` record with empty `resource_id` covering that date) → identical results to the Sunday cases, for both wage types.
9. `check_in` Sat 22:00 → `check_out` Sun 07:00 (overnight, Daily Paid) → the 22:00–24:00 Saturday portion and the 00:00–07:00 Sunday portion are each evaluated under their own date's rules and summed; `day_type` on the record stores `'weekday'` (the check-in date).
10. An attendance record whose `employee_id.wage_type` is unset → no error; `normal_hours` equals the full worked duration (rounded), both OT buckets `== 0.0`, and a warning is logged.
11. `check_in` Mon 18:00 → `check_out` Mon 18:20 (Daily Paid, 20 minutes of OT150 window) → `overtime_150_hours == 0.0` (sub-30-minute remainder dropped, FR-006).
12. An attendance record with `check_out` unset → all four fields are `0.0`/empty; saving does not error.
