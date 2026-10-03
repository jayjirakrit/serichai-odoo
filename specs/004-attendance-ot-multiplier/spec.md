# Feature Specification: Multi-Rate Overtime Calculation for Attendance (serichai_hr_attendance)

**Feature Branch**: `004-attendance-ot-multiplier`

**Created**: 2026-09-04

**Status**: Draft

**Input**: User description: "Multi-Rate Overtime Calculation for Odoo 19 HR Attendance — a custom addon `serichai_hr_attendance` extending `hr_attendance` to split every attendance record's worked time into three pay categories (Normal, OT 1.5x, OT 2x), driven by employee wage type (Daily/Monthly Paid) and day type (weekday vs. Sunday/Holiday), using a configurable, UI-editable ruleset rather than hardcoded time windows."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic pay-category split on every attendance record (Priority: P1)

A payroll/HR staff member reviews an employee's attendance record and needs to know, without doing any manual math, how many of the worked hours count as Normal pay, how many count as 1.5x overtime, and how many count as 2x overtime — with the split determined automatically by the employee's wage type (Daily Paid or Monthly Paid) and by whether the work happened on a weekday or a Sunday/public holiday.

**Why this priority**: This is the core value of the feature. Without automatic, correct hour-bucketing, payroll staff must recompute every attendance record by hand, which is exactly what this feature exists to eliminate.

**Independent Test**: Create attendance records covering a normal weekday shift, a weekday shift that runs into the evening overtime window, and a Sunday shift, for both a Daily Paid and a Monthly Paid employee. Confirm each record shows the correct Normal / OT 1.5x / OT 2x hour split without any manual entry.

**Acceptance Scenarios**:

1. **Given** a Daily Paid employee clocks in and out entirely within Monday–Saturday 08:00–17:00, **When** the attendance record is saved, **Then** all worked hours are categorized as Normal pay and OT 1.5x/OT 2x are zero.
2. **Given** a Daily Paid employee works Monday–Saturday from 08:00 to 20:00, **When** the attendance record is saved, **Then** hours from 08:00–17:00 are Normal, hours from 18:00–20:00 are OT 1.5x, and the 17:00–18:00 gap is not counted in any bucket.
3. **Given** a Monthly Paid employee works a Sunday from 08:00 to 18:00, **When** the attendance record is saved, **Then** hours from 08:00–16:30 are Normal and hours from 16:30–18:00 are OT 2x.
4. **Given** an attendance record's check-in or check-out time changes, or the employee's wage type changes, **When** the record is saved, **Then** the Normal/OT 1.5x/OT 2x hours are automatically recalculated.

---

### User Story 2 - Configure pay-rate windows without code changes (Priority: P2)

An HR Manager needs to adjust when overtime starts, add a new pay window, or correct an existing time boundary (for example, because a new labor agreement changes the evening overtime start time) without asking a developer to change code or deploy a new version of the module.

**Why this priority**: The business explicitly requires the rules to be data, not hardcoded logic, so that rule changes are a configuration task rather than a development task. This is what makes the feature maintainable long-term, but it depends on User Story 1's computation engine already existing.

**Independent Test**: As an HR Manager, open the Overtime Rules configuration screen, edit the time boundary of an existing rule (or add a new one), save, and confirm that newly computed (or recomputed) attendance records reflect the change — with no code deployment involved.

**Acceptance Scenarios**:

1. **Given** an HR Manager opens the Overtime Rules configuration screen, **When** they view the list, **Then** they see the pay-rate windows grouped by wage type and day type, each with its time range and pay category.
2. **Given** an HR Manager edits a rule's start or end time and saves, **When** a new attendance record is created that overlaps the updated window, **Then** the computed hours reflect the updated boundary.
3. **Given** a regular employee (not an HR Officer/Manager) attempts to open the Overtime Rules configuration screen, **When** they try, **Then** they are denied edit access consistent with existing HR Attendance security roles.

---

### User Story 3 - Review and export pay-category totals for payroll (Priority: P3)

A payroll/HR staff member needs to see totals of Normal, OT 1.5x, and OT 2x hours across many employees and a date range — in the attendance list, summarized in a pivot table, and exported to a spreadsheet — to feed an external or future payroll process.

**Why this priority**: This makes the computed data usable for real payroll work. It depends on User Stories 1 and 2 already producing correct, configurable hour splits; without those, this reporting layer would just be displaying wrong numbers faster.

**Independent Test**: With a mix of attendance records already showing computed hour splits, group the attendance list by month and employee and confirm correct subtotals; open a pivot summary by employee and day type; export a selection of records and confirm the new hour fields are present in the exported file.

**Acceptance Scenarios**:

1. **Given** attendance records with computed Normal/OT 1.5x/OT 2x hours, **When** the attendance list is grouped by month and then by employee (existing behavior), **Then** each group shows correct summed totals for all three hour categories.
2. **Given** attendance records across multiple employees and day types, **When** the payroll summary view is opened, **Then** it shows total Normal/OT 1.5x/OT 2x hours broken down by employee and by day type.
3. **Given** a set of attendance records, **When** a staff member exports them to a spreadsheet (CSV or Excel), **Then** Normal Hours, OT 1.5x Hours, OT 2x Hours, and Day Type are available as selectable export columns and contain correct values in the exported file.

---

### Edge Cases

- **Weekday inter-window gap**: For Monday–Saturday shifts, worked time between the end of the Normal window (17:00) and the start of the OT 1.5x window (18:00) is **not counted in any pay bucket** — it is treated the same as the intentional Sunday/Holiday unpaid gap. Only time before the start of the overall weekday range (08:00) or after its end (22:00) is swept into OT 1.5x.
- **Sunday/Holiday unpaid gap (Daily Paid)**: Worked time between 12:00 and 12:30 on a Sunday/Holiday for a Daily Paid employee is intentionally excluded from every pay bucket. Time before 08:00, between 12:00–12:30, or after 16:30 on a Sunday/Holiday is also uncounted for Daily Paid employees (no catch-all rule exists for this combination).
- **Overnight shifts**: When a shift crosses midnight, each portion of the shift is evaluated against the day type of the calendar date it actually falls on. Hours worked before midnight use the day type of the check-in date; hours worked at or after midnight use the day type of the check-out date. Example: a shift from Saturday 23:00 to Sunday 07:00 evaluates the 23:00–24:00 portion under weekday rules and the 00:00–07:00 portion under Sunday/Holiday rules.
- **Open attendance (no check-out yet)**: An attendance record with no check-out time yet must show zero (or blank) hours in all three pay-category fields rather than causing an error, and must recompute correctly once checked out.
- **Overlapping rule windows**: If two configured rules for the same wage type and day type have overlapping time windows, each minute of worked time is counted in only one pay bucket — never double-counted. Explicitly time-bounded rules are applied first; a "catches everything else" rule only picks up time not already claimed by a bounded rule. If more than one "catches everything else" rule exists for the same wage type and day type, the one with the lowest sequence number claims the remaining time.
- **Sub-30-minute remainder**: Any amount of time within a single pay category that is less than 30 minutes is dropped, not rounded up — e.g., an employee who works exactly 20 minutes into the OT 1.5x window earns 0 hours of OT 1.5x for that portion, while 30 minutes or more rounds down to the nearest half hour (e.g., 50 minutes counts as 0.5 hours, not 1 hour).
- **Public holiday on a weekday**: A public holiday that falls on a day other than Sunday (e.g., a Wednesday) is treated identically to a Sunday for pay-rule purposes, for both wage types.
- **Employee with no wage type set**: The system must not error. It falls back to treating all worked hours on that record as Normal pay (zero overtime) and records a warning for follow-up, since no wage-type-specific rules can be determined.
- **Multi-company boundary**: Overtime rules and computed hours are scoped per company; an employee's attendance is only matched against overtime rules belonging to the same company.
- **Historical records**: Existing attendance records created before this feature is installed are backfilled with computed pay-category values rather than being left blank indefinitely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow each employee to be classified with a wage type of either "Daily Paid" or "Monthly Paid."
- **FR-002**: System MUST determine, for every attendance record, whether the work falls on a "weekday" (Monday–Saturday, not a public holiday) or on "Sunday/Holiday" (any Sunday, or any date recognized as a public holiday for the employee's work schedule).
- **FR-003**: System MUST provide a configurable set of pay-rate rules (time window, pay category, and which wage type/day type combination it applies to) that authorized staff can view, add, edit, and deactivate through the user interface, with no code changes required to take effect.
- **FR-004**: System MUST pre-load the following default pay-rate rules on installation:

  | Wage Type | Day Type | Time Window | Pay Category | Notes |
  |---|---|---|---|---|
  | Daily Paid | Weekday | 08:00–17:00 | Normal | |
  | Daily Paid | Weekday | 18:00–22:00 | OT 1.5x | Also catches time before 08:00 or after 22:00 |
  | Daily Paid | Sunday/Holiday | 08:00–12:00 | Normal | |
  | Daily Paid | Sunday/Holiday | 12:30–16:30 | OT 2x | 12:00–12:30 is an intentional unpaid gap; no catch-all for this combination |
  | Monthly Paid | Weekday | 08:00–17:00 | Normal | |
  | Monthly Paid | Weekday | 18:00–22:00 | OT 1.5x | Also catches time before 08:00 or after 22:00 |
  | Monthly Paid | Sunday/Holiday | 08:00–16:30 | Normal | |
  | Monthly Paid | Sunday/Holiday | 16:30–24:00 | OT 2x | Also catches any Sunday/Holiday time outside the defined windows |

- **FR-005**: System MUST compute, for every attendance record, the number of hours worked in each of three categories — Normal, OT 1.5x, OT 2x — based on the employee's wage type, the record's day type(s), and the applicable pay-rate rules.
- **FR-006**: System MUST round each pay category's computed total for an attendance record down to the nearest 30-minute increment; a partial amount of less than 30 minutes within a category MUST be dropped rather than rounded up (e.g., 1 hour 47 minutes of OT 1.5x time is recorded as 1.5 hours, not 2 hours; 14 minutes of OT 1.5x time is recorded as 0 hours).
- **FR-007**: System MUST recompute an attendance record's pay-category hours whenever its check-in time, check-out time, or the employee's wage type changes.
- **FR-008**: System MUST split an overnight attendance record (check-out on a later calendar date than check-in) so that each portion of the shift is evaluated against the day type of the calendar date it actually occurs on.
- **FR-009**: System MUST leave an attendance record's pay-category hours at zero (not an error) when the record has no check-out time yet, and MUST recompute them correctly once a check-out time is recorded.
- **FR-010**: System MUST ensure no worked minute is counted in more than one pay category when multiple rules for the same wage type and day type have overlapping or catch-all time windows; explicitly time-bounded rules take precedence over "catches everything else" rules, and among multiple catch-all rules for the same combination, the lowest-sequence one applies.
- **FR-011**: System MUST leave any worked time that falls outside every applicable rule's window — and is not claimed by a catch-all rule — uncounted in all three pay categories (e.g., the Sunday/Holiday 12:00–12:30 gap for Daily Paid, and the weekday 17:00–18:00 gap for both wage types).
- **FR-012**: System MUST treat a public holiday that falls on a non-Sunday weekday identically to a Sunday for the purposes of day-type classification and rule matching, for both wage types.
- **FR-013**: System MUST NOT error when an employee has no wage type set; in that case it MUST treat all of that record's worked hours as Normal pay and record a warning for staff to follow up.
- **FR-014**: System MUST scope overtime rules and computed hours to the company the employee belongs to, so an employee is only ever matched against rules from their own company.
- **FR-015**: System MUST restrict creating, editing, or deactivating pay-rate rules to HR Officer/Manager-level roles, consistent with existing HR Attendance security roles; other users MAY view but not edit rules to the extent existing Attendance security already allows.
- **FR-016**: Attendance list views MUST display the day type and the three computed pay-category hour totals as columns, positioned immediately after the existing extra-hours column, with the two overtime columns and day type hidden by default (user-toggleable) and the Normal-hours column shown by default.
- **FR-017**: Grouping the attendance list by existing dimensions (e.g., month, then employee) MUST show correct summed subtotals for all three pay-category columns at each group level.
- **FR-018**: System MUST provide a payroll summary view showing Normal, OT 1.5x, and OT 2x hour totals broken down by employee and by day type, reachable from the Attendances area of the application.
- **FR-019**: The three computed pay-category hour fields and the day-type field MUST be available as selectable columns in the standard record export (both spreadsheet and delimited-file formats).
- **FR-020**: System MUST backfill computed pay-category values for attendance records that already existed before this feature was installed, so historical data is not left blank.

### Key Entities

- **Employee Wage Type**: A classification on each employee (Daily Paid or Monthly Paid) that determines which set of pay-rate rules applies to their attendance.
- **Day Type**: A per-attendance classification (Weekday or Sunday/Holiday) derived from the attendance date, the day of week, and the employee's public holiday calendar.
- **Overtime Rule**: A configurable record defining a time window, the pay category it belongs to (Normal, OT 1.5x, OT 2x), which wage type and day type it applies to, its evaluation order relative to other rules, whether it acts as a "catch everything else" rule, and the company it belongs to.
- **Attendance Record**: An individual clock-in/clock-out record for an employee, extended with its computed day type and its three computed pay-category hour totals.
- **Public Holiday Calendar**: The existing reference of dates recognized as public holidays for an employee's work schedule, used to determine day type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of attendance records for employees with a wage type set are automatically split into Normal/OT 1.5x/OT 2x hours with no manual data entry.
- **SC-002**: An HR Manager can change an overtime time boundary or add a new rule and see it take effect on newly computed attendance records within the same working session, with zero code changes or deployments involved.
- **SC-003**: Across a representative set of test scenarios (plain weekday shift, weekday shift into evening overtime, weekday shift crossing the inter-window gap, Sunday shift within normal hours, Sunday shift crossing the unpaid gap, Sunday shift into 2x overtime, Monthly-paid Sunday shift crossing into 2x overtime, holiday-on-a-weekday, overnight shift, a shift with a sub-30-minute overtime remainder, and an employee with no wage type), the computed hour split matches the expected manual calculation exactly (including 30-minute-increment rounding), with zero variance.
- **SC-004**: Payroll staff can produce a correct Normal/OT 1.5x/OT 2x hours summary for any employee or date range using the existing list, grouping, pivot, and export tools, without needing any additional manual calculation.
- **SC-005**: 100% of attendance records that existed prior to installing this feature show correct, non-blank computed pay-category values after installation completes.
- **SC-006**: Zero attendance records — including open (no check-out) records and records for employees with no wage type — cause an error or block saving.

## Assumptions

- "HR Officer/Manager-level roles" refers to the access levels already defined by the existing HR Attendance module; this feature reuses those roles rather than introducing new ones.
- The public holiday calendar used to determine "Holiday" day type is the one already linked to the employee's working schedule elsewhere in the system; this feature does not introduce a separate holiday calendar.
- Backfilling historical attendance records happens automatically as part of installing/upgrading the module, without requiring a separate manual step from staff.
- Kiosk-mode-created attendance records are computed the same way as attendance records created through any other channel; no separate behavior is required.
- Each pay category's total is rounded down to the nearest 30-minute increment per FR-006; this rounding is applied to each category's total on the attendance record (not to the record's overall worked time before categorization).
- This feature produces the computed hour totals only; it does not perform any actual payroll pay-run calculation, which remains out of scope (no Payroll app exists in this Odoo edition).
