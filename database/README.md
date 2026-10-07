# Database Scripts — Smart Campus Placement Management System

Course: BACSE202 Database Systems · Phase 1 (Database Design and Table Creation)

## Target environment

| Item | Value |
|---|---|
| DBMS | MySQL Community Edition, 8.0.16 or later |
| Engine | InnoDB (required — MyISAM silently ignores `FOREIGN KEY`) |
| Character set | `utf8mb4`, collation `utf8mb4_0900_ai_ci` |
| Schema name | `smart_campus_placement` |

`CHECK` constraints are only **enforced** from MySQL 8.0.16. Earlier versions
parse them and ignore them silently.

## Run order

```
01_create_database.sql    -- CREATE DATABASE + print server facts
02_create_tables.sql      -- 13 tables: PK, UNIQUE, NOT NULL, DEFAULT, ENUM, CHECK
03_constraints.sql        -- 14 named FOREIGN KEY constraints
04_verify.sql             -- evidence queries for the Phase 1 report
```

From a shell:

```bash
mysql -u root -p < 01_create_database.sql
mysql -u root -p < 02_create_tables.sql
mysql -u root -p < 03_constraints.sql
mysql -u root -p < 04_verify.sql
```

Scripts 02 and 03 are re-runnable. Script 02 drops the 13 tables in reverse
dependency order before creating them.

## Why foreign keys live in a separate file

`02` holds every constraint a table can enforce **on its own**. `03` holds
**referential** integrity. Splitting them means table creation order never
blocks a rerun, and every foreign key gets an explicit, greppable name.

## Constraint enforcement strategy

A `CHECK` constraint in MySQL may read **only columns of the row being
written**. No subquery, no other table, no other row, no non-deterministic
function. That boundary decides which tier each business rule belongs to.

### Tier 1 — enforced by DDL in Phase 1 ✅

| Kind | Where |
|---|---|
| `PRIMARY KEY` | all 13 tables |
| `FOREIGN KEY` + `ON DELETE` / `ON UPDATE` | 14 constraints in `03` |
| `UNIQUE` single column | `department.dept_code`, `department.dept_name`, `student.reg_no`, `student.email`, `student.phone`, `company.company_name`, `company.hr_email`, `skill.skill_name`, `offer.application_id`, `placement_record.offer_id` |
| `UNIQUE` composite | `job_drive(company_id, job_title, drive_date)`, `application(student_id, drive_id)`, `interview(application_id, round_no)` |
| `NOT NULL` | every mandatory attribute |
| `DEFAULT` | timestamps, statuses, `cgpa`, `active_backlogs`, `num_openings`, `allow_placed_students`, `is_mandatory`, `verified_on` |
| `ENUM` domains | 11 columns |
| `CHECK` numeric range | cgpa 0–10, percentages 0–100, backlogs ≥ 0, ctc > 0, openings > 0, round_no > 0, scores |
| `CHECK` same-row date order | `apply_deadline <= drive_date`, `expected_joining_date >= offer_date` |
| `CHECK` same-row cross-column | `score <= max_score`, offline round must name a venue |
| `CHECK` format | `academic_year` matches `YYYY-YYYY` |

### Tier 2 — needs a TRIGGER, deferred to Phase 2 ⚠️

Each rule reads another table or another row, so no `CHECK` can express it.

| # | Rule |
|---|---|
| T1 | A `placement_record` may exist only if its `offer.offer_status = 'Accepted'` |
| T2 | `application.applied_on <= job_drive.apply_deadline` |
| T3 | Applicant must satisfy `eligibility_criteria` (cgpa, backlogs, percentages, batch year) |
| T4 | Applicant's `dept_id` must appear in `drive_eligible_department` for that drive |
| T5 | If `allow_placed_students = FALSE`, block already placed applicants |
| T6 | Set `application_status = 'Selected'` when an `offer` row is inserted |
| T7 | `interview.scheduled_at >= application.applied_on` |
| T8 | `drive_status` must not move backwards (`Completed` → `Open` is illegal) |
| T9 | `company_employee_code` unique within one company |
| T10 | At most one `Accepted` offer per student per academic year, if policy requires |

Known limit: a trigger validates at write time only. It cannot retroactively
validate existing rows, and MySQL triggers cannot be deferred to the end of a
transaction. So T1 and T6 guard the normal path but are not formal invariants
the way a `FOREIGN KEY` is.

### Tier 3 — application / business logic, Phase 2 🧠

Screening students against drives · skill-match ranking · round advancement ·
offer expiry · one-offer policy · role based access · resume upload ·
notifications · audit trail · placement statistics (built as **views**, which
also replace every derived column deliberately not stored:
`is_placed`, `age`, `total_applicants`, `students_hired`, `current_round`).

## Table creation order

Derived from the foreign key graph, which is acyclic:

```
level 0 : department, skill, company
level 1 : student, job_drive
level 2 : eligibility_criteria, drive_eligible_department,
          student_skill, drive_required_skill, application
level 3 : interview, offer
level 4 : placement_record
```

Drop order is the exact reverse.
