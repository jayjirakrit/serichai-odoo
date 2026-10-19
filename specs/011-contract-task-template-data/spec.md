# Feature Specification: Contract Task Template Data

**Feature Branch**: `011-contract-task-template-data`

**Created**: 2026-10-20

**Status**: Implemented

**Input**: "Create template data for the task template, focused on task_properties, similar to the 'Template Contract' record."

## Background

The "Serichai Contract" project, its property definitions and the "Template Contract" template task existed only in one database. A new database had none of them, so contract tasks could not be created from the template there.

## User Scenarios & Testing

### User Story 1 - New database ships the contract template (P1)

On a fresh database, after the addon is installed, planners find the project "Serichai Contract" with the 21 contract properties (sections, contract number, value, dates, applicant, agency, bidding details, product SKUs), the stage "กำลังจะประมูล", and a template task "Template Contract". "Create from template" produces an ordinary task whose properties and defaults are copied.

**Acceptance Scenarios**:
1. **Given** a fresh database, **When** the addon is installed, **Then** the project, stage and template task exist and the template is marked as a template.
2. **Given** the template, **When** a task is created from it, **Then** it is not a template and carries the default values for "ยื่นในนาม" and "หน่วยงาน".

### User Story 2 - Existing database is not duplicated (P1)

On a database that already has a hand-made "Serichai Contract" project, stage and template, installing the addon reuses them.

**Acceptance Scenarios**:
1. **Given** an existing project, stage and template with those names, **When** the addon is installed, **Then** there is still exactly one of each, and the template keeps its id and existing values.

## Requirements

- **FR-001**: Property names, Thai labels, suffixes, selection options and folded sections match the source record exactly (other addons find properties by label).
- **FR-002**: The shipped records are `noupdate`, so later upgrades never overwrite user edits.
- **FR-003**: Installing adopts existing records by name instead of creating duplicates.
- **FR-004**: Database-specific data (tags, assignee, followers, tokens, dates) is not shipped.

## Known limits

- On first install over existing records, the project's property definitions are replaced by the shipped 21. Properties added by hand that are not in the shipped list are lost. Compare before installing on a live database.
- Load order: the addon depends only on `project`, so Odoo loads it before `sale_timesheet`. On a database that already has `sale_timesheet`, creating the project then fails on the NOT NULL `billing_type` column (the default is not registered yet). Workaround used on `serichai-db`: `ALTER TABLE project_project ALTER COLUMN billing_type SET DEFAULT 'not_billable'` before the upgrade, and `DROP DEFAULT` after. The same applies to any new database that installs `sale_timesheet` before this addon.
