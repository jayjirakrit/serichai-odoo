# Phase 1 Data Model: Multi-Rate Overtime Calculation for Attendance

## New model: `hr.attendance.ot.rule`

One record = one configurable pay-rate window. Seeded with the 8 default rules from spec FR-004; fully editable/creatable through the UI (User Story 2) by HR Officer/Manager roles.

| Field | Type | Notes |
|---|---|---|
| `name` | Char, required | Free-text label, e.g. "Daily Paid – Weekday – Normal" |
| `wage_type` | Selection: `daily`, `monthly`, required | Which employee wage type this rule applies to |
| `day_type` | Selection: `weekday`, `sunday_holiday`, required | Which day type this rule applies to |
| `sequence` | Integer, default 10 | Evaluation order within the same `wage_type`/`day_type` group (see Precedence below) |
| `time_from` | Float, widget `float_time`, 0–24 | Window start (local clock time) |
| `time_to` | Float, widget `float_time`, 0–24 | Window end (local clock time); may equal 24.0 to mean midnight |
| `pay_type` | Selection: `normal`, `ot150`, `ot200`, required | Which bucket this window's overlap is added to |
| `catch_outside` | Boolean, default False | If true, this rule also absorbs worked time in its `wage_type`/`day_type` group that falls outside every *explicitly bounded* (non-catch-outside) rule's window |
| `company_id` | Many2one `res.company`, default `env.company` | Multi-company scoping (FR-014) |
| `active` | Boolean, default True | Standard archive flag |

**Validation rules**:
- `time_from < time_to` for a normal (non-wraparound) window; the default data never needs a window crossing midnight, so wraparound windows are not supported by this model — an `time_to <= time_from` combination is rejected with a `ValidationError` (a rule can't validly express "window ends before/at when it starts" here; overnight coverage comes from the record-level midnight-split in the compute engine, not from the rule window itself).
- At most one `catch_outside` rule is *expected* per (`wage_type`, `day_type`, `company_id`) combination in the default data; multiple are technically allowed (not blocked by a constraint) and resolved by sequence per the Precedence rule below (FR-009), so misconfiguration doesn't error, it just follows a defined, documented order.

**Precedence / no-double-count rule** (FR-009, FR-010, spec Edge Cases → "Overlapping rule windows"):
1. For a given attendance segment (one calendar date's portion of a shift) and its `wage_type`/`day_type`, **every** matching rule — catch-outside or not — first claims its own overlap via `_interval_overlap(segment, rule.time_from, rule.time_to)`, added to that rule's `pay_type` bucket. A rule's `catch_outside` flag does not affect its own explicit window; it only adds the extra behavior in step 2.
2. If any `catch_outside`-flagged rule exists for that `wage_type`/`day_type`, compute the group's **outer boundary** — `min(time_from)` to `max(time_to)` across *every* rule in the group (not just the catch-outside one) — and pass it as a single window to `_hours_outside(segment, [(boundary_from, boundary_to)])`. Whatever segment time falls outside that boundary (before `boundary_from` or after `boundary_to`) is added to the **lowest-`sequence`** `catch_outside` rule's bucket.
3. Time that falls *between* two rules' windows but still *inside* the group's outer boundary (e.g., the weekday 17:00–18:00 gap, which sits inside the 08:00–22:00 boundary) is **not** swept by step 2 — it is left unpaid, exactly like the Daily-Sunday/Holiday 12:00–12:30 gap. This is what makes both "gap" edge cases behave consistently from one shared mechanism, without hardcoding either gap.
4. If no `catch_outside` rule exists for the group at all (e.g., Daily Paid + Sunday/Holiday in the default data), nothing beyond each rule's own explicit window is ever counted — all boundary and inter-window gaps are dropped, per FR-011.
5. No worked minute is ever added to more than one bucket (each rule's explicit window and the single boundary sweep are evaluated independently per bucket, and the boundary sweep only fires on time no rule's explicit window already claimed).

## Default rule data (FR-004)

| wage_type | day_type | time_from | time_to | pay_type | catch_outside |
|---|---|---|---|---|---|
| daily | weekday | 08:00 | 17:00 | normal | False |
| daily | weekday | 18:00 | 22:00 | ot150 | True |
| daily | sunday_holiday | 08:00 | 12:00 | normal | False |
| daily | sunday_holiday | 12:30 | 16:30 | ot200 | False |
| monthly | weekday | 08:00 | 17:00 | normal | False |
| monthly | weekday | 18:00 | 22:00 | ot150 | True |
| monthly | sunday_holiday | 08:00 | 16:30 | normal | False |
| monthly | sunday_holiday | 16:30 | 24:00 | ot200 | True |

(For `daily` + `sunday_holiday`, no rule is `catch_outside`, which is what makes the 12:00–12:30 gap — and anything before 08:00 or after 16:30 — intentionally unpaid, per spec Edge Cases.)

## Extended model: `hr.employee`

| Field | Type | Notes |
|---|---|---|
| `wage_type` | Selection: `daily` (Daily Paid), `monthly` (Monthly Paid); no default | Left unset by default so the "no wage type" fallback path (FR-013) is reachable and must be handled, not just theoretical |

## Extended model: `hr.attendance`

| Field | Type | Notes |
|---|---|---|
| `day_type` | Selection: `weekday`, `sunday_holiday`; compute, store, aggregator N/A (Selection) | Derived from the **check-in date** (see research.md Decision 3); depends on `check_in`, `employee_id` |
| `normal_hours` | Float, compute, store, `aggregator="sum"`, widget `float_time` | Sum of this record's Normal-bucket hours, rounded per FR-006 |
| `overtime_150_hours` | Float, compute, store, `aggregator="sum"`, widget `float_time` | Sum of this record's OT 1.5x-bucket hours, rounded per FR-006 |
| `overtime_200_hours` | Float, compute, store, `aggregator="sum"`, widget `float_time` | Sum of this record's OT 2x-bucket hours, rounded per FR-006 |

**Compute dependencies**: `@api.depends('check_in', 'check_out', 'employee_id.wage_type')` on the single compute method producing all four fields together (FR-006, FR-007 of spec — recompute on check-in/check-out/wage-type change).

**Compute algorithm** (`_compute_ot_hours`, using helpers `_get_day_type()`, `_interval_overlap()`, `_hours_outside()`):

1. If `check_out` is empty (open attendance), set all four fields to their zero/default value and return (FR-008/FR-009 of spec's edge cases) — no rule lookup needed.
2. Split `[check_in, check_out]` into one segment per calendar date crossed, in the employee's timezone (research.md Decision 3 / spec Edge Cases → "Overnight shifts").
3. For the record's stored `day_type`, use the day type of the **first** segment (the check-in date).
4. If `employee_id.wage_type` is not set: set `normal_hours` to the full worked duration (rounded per FR-006) and both OT buckets to 0; log a warning; skip rule lookup (FR-013).
5. Otherwise, for each segment: determine its own day type via `_get_day_type(date, employee)`; fetch active `hr.attendance.ot.rule` records for `(employee.wage_type, segment.day_type, employee.company_id)` ordered by `sequence`; apply the Precedence algorithm above, accumulating hours per `pay_type` across all segments.
6. Round each of the three accumulated totals down to the nearest 0.5 (FR-006) and write to `normal_hours` / `overtime_150_hours` / `overtime_200_hours`.

**Helper contracts**:
- `_get_day_type(date, employee)` → `'weekday' | 'sunday_holiday'`. Sunday → `sunday_holiday`. Otherwise, `sunday_holiday` if `date` falls within any of `employee.resource_calendar_id.global_leave_ids` (`resource.calendar.leaves` rows with empty `resource_id` — research.md Decision 2), else `weekday`.
- `_interval_overlap(seg_start_hour, seg_end_hour, rule_from, rule_to)` → hours of overlap between the segment's local time-of-day range and the rule's `[time_from, time_to)` window, within that one calendar date.
- `_hours_outside(seg_start_hour, seg_end_hour, claimed_windows)` → hours of the segment not covered by any window in `claimed_windows` (the non-catch-outside rules already matched for that segment's `wage_type`/`day_type`).

## State / lifecycle notes

- No new state machine. These fields are purely derived (compute+store) from existing `hr.attendance` lifecycle fields (`check_in`, `check_out`) and `hr.employee.wage_type`; they carry no independent lifecycle of their own.
- Historical records: backfilled once via `post_init_hook` (research.md Decision 6); after that, ordinary recompute triggers (field changes) keep them current — no ongoing cron is needed.
