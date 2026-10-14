# Test Results — Phase 2

All results below were produced by running the commands shown. Nothing here is
estimated or reproduced from memory.

| Item | Value |
|---|---|
| Date run | 14 October 2026 |
| Database | MySQL 8.0.46-0ubuntu0.24.04.4, `smart_campus_placement` |
| Backend | Python 3.12.3, FastAPI 0.143.1, SQLAlchemy 2.0.54, PyMySQL 1.2.3 |
| Frontend | Node 24.14.0, React 18.3.1, TypeScript 5.6.3, Vite 5.4.11 |
| Test runner | pytest 9.1.1 |

---

## 1. Automated test suite

### How isolation works

These are real integration tests against the real database. Each test runs
inside one transaction that is rolled back afterwards, and the FastAPI
`get_conn` dependency is overridden so the route handler receives that same
connection. Every write a test makes disappears when the test finishes.

Nothing is dropped. Nothing is truncated. No foreign key check is disabled. The
seeded demo row counts were identical before and after the suite ran, which is
shown in section 2.

### Command

```bash
cd backend && .venv/bin/python -m pytest -v
```

### Result

```
67 passed, 1 warning in 0.96s
```

The one warning is a Starlette deprecation notice about the `httpx` test client,
not a failure.

### Every test, with its outcome

```
test_database_connection_succeeds PASSED              [  1%]
test_all_thirteen_phase_one_tables_are_present PASSED [  2%]
test_list_students_is_paginated PASSED                [  4%]
test_pagination_offset_returns_different_rows PASSED  [  5%]
test_get_student_detail PASSED                        [  7%]
test_get_missing_student_returns_404 PASSED           [  8%]
test_list_and_get_job_drive PASSED                    [ 10%]
test_student_filters PASSED                           [ 11%]
test_create_student PASSED                            [ 13%]
test_invalid_cgpa_rejected PASSED                     [ 14%]
test_negative_backlogs_rejected PASSED                [ 16%]
test_duplicate_reg_no_rejected PASSED                 [ 17%]
test_unknown_department_rejected PASSED               [ 19%]
test_valid_application_submission PASSED              [ 20%]
test_duplicate_application_rejected PASSED            [ 22%]
test_ineligible_student_rejected_on_cgpa PASSED       [ 23%]
test_ineligible_student_rejected_on_backlogs PASSED   [ 25%]
test_ineligible_student_rejected_on_batch_year PASSED [ 26%]
test_application_after_deadline_rejected PASSED       [ 28%]
test_application_from_ineligible_department_rejected PASSED [ 29%]
test_application_to_drive_that_is_not_open_rejected PASSED [ 31%]
test_placed_student_blocked_when_not_allowed PASSED   [ 32%]
test_placed_student_allowed_when_drive_permits_it PASSED [ 34%]
test_drive_without_criteria_has_no_academic_gate PASSED [ 35%]
test_drive_without_eligible_departments_is_open_to_all PASSED [ 37%]
test_eligible_students_query_matches_per_student_check PASSED [ 38%]
test_drive_status_cannot_move_backwards PASSED        [ 40%]
test_drive_status_forward_transition_allowed PASSED   [ 41%]
test_drive_deadline_after_drive_date_rejected PASSED  [ 43%]
test_create_interview PASSED                          [ 44%]
test_interview_score_above_max_score_rejected PASSED  [ 46%]
test_duplicate_interview_round_rejected PASSED        [ 47%]
test_offline_interview_without_venue_rejected PASSED  [ 49%]
test_interview_before_application_date_rejected PASSED [ 50%]
test_interview_for_unknown_application_rejected PASSED [ 52%]
test_create_offer_marks_application_selected PASSED   [ 53%]
test_duplicate_offer_rejected PASSED                  [ 55%]
test_offer_joining_date_before_offer_date_rejected PASSED [ 56%]
test_zero_ctc_offer_rejected PASSED                   [ 58%]
test_placement_against_non_accepted_offer_rejected PASSED [ 59%]
test_placement_against_accepted_offer_succeeds PASSED [ 61%]
test_duplicate_placement_rejected PASSED              [ 62%]
test_bad_academic_year_format_rejected PASSED         [ 64%]
test_accepted_offer_cannot_be_downgraded_while_placed PASSED [ 65%]
test_student_skill_lifecycle PASSED                   [ 67%]
test_invalid_proficiency_rejected PASSED              [ 68%]
test_skill_match_reports_coverage PASSED              [ 70%]
test_dashboard_aggregation_matches_direct_sql PASSED  [ 71%]
test_dashboard_reacts_to_a_new_row PASSED             [ 73%]
test_every_report_runs[applications-by-company] PASSED [ 74%]
test_every_report_runs[interview-progress] PASSED     [ 76%]
test_every_report_runs[offers-by-status] PASSED       [ 77%]
test_every_report_runs[placements-by-batch] PASSED    [ 79%]
test_every_report_runs[placements-by-department] PASSED [ 80%]
test_every_report_runs[placements-by-company] PASSED  [ 82%]
test_every_report_runs[students-without-applications] PASSED [ 83%]
test_every_report_runs[applications-without-interviews] PASSED [ 85%]
test_every_report_runs[drives-without-applications] PASSED [ 86%]
test_every_report_runs[accepted-offers-not-verified] PASSED [ 88%]
test_every_report_runs[skill-demand] PASSED           [ 89%]
test_every_report_runs[top-offers] PASSED             [ 91%]
test_every_report_runs[application-funnel] PASSED     [ 92%]
test_unknown_report_returns_404 PASSED                [ 94%]
test_accepted_offers_not_verified_report_is_consistent PASSED [ 95%]
test_errors_never_leak_internals PASSED               [ 97%]
test_unknown_field_is_rejected PASSED                 [ 98%]
test_empty_patch_rejected PASSED                      [100%]
```

### Coverage of the rules the assignment asked to test

| Required test | Test name | Result |
|---|---|---|
| Successful database connection | `test_database_connection_succeeds` | Passed |
| Student retrieval | `test_get_student_detail`, `test_list_students_is_paginated` | Passed |
| Job drive retrieval | `test_list_and_get_job_drive` | Passed |
| Valid application submission | `test_valid_application_submission` | Passed |
| Duplicate application rejection | `test_duplicate_application_rejected` | Passed |
| Ineligible student rejection | `test_ineligible_student_rejected_on_cgpa`, `..._on_backlogs`, `..._on_batch_year` | Passed |
| Application after deadline rejection | `test_application_after_deadline_rejected` | Passed |
| Invalid department rejection | `test_application_from_ineligible_department_rejected`, `test_unknown_department_rejected` | Passed |
| Invalid CGPA rejection | `test_invalid_cgpa_rejected` | Passed |
| Invalid interview score rejection | `test_interview_score_above_max_score_rejected` | Passed |
| Duplicate interview round rejection | `test_duplicate_interview_round_rejected` | Passed |
| Duplicate offer rejection | `test_duplicate_offer_rejected` | Passed |
| Placement against a non-accepted offer rejection | `test_placement_against_non_accepted_offer_rejected` | Passed |
| Duplicate placement rejection | `test_duplicate_placement_rejected` | Passed |
| Dashboard aggregation correctness | `test_dashboard_aggregation_matches_direct_sql`, `test_dashboard_reacts_to_a_new_row` | Passed |

---

## 2. Demo data unchanged by the test run

```bash
cd backend && .venv/bin/python seed.py --summary
```

Identical before and after `pytest`:

| Table | Rows |
|---|---|
| `department` | 6 |
| `skill` | 20 |
| `company` | 10 |
| `student` | 40 |
| `student_skill` | 207 |
| `job_drive` | 14 |
| `eligibility_criteria` | 13 |
| `drive_eligible_department` | 34 |
| `drive_required_skill` | 26 |
| `application` | 64 |
| `interview` | 156 |
| `offer` | 11 |
| `placement_record` | 5 |

## 3. Seed script is repeatable

The seed was run three times in succession. Row counts were identical after each
run, confirming the natural key matching works and nothing duplicates.

The scoped reset was also exercised: `seed.py --reset` removed exactly the demo
rows (7 placements, 20 offers, 259 interviews, 86 applications, 30 required
skills, 41 eligible departments, 16 criteria, 207 student skills, 17 drives, 40
students, 10 companies, 20 skills, 6 departments from an earlier data set),
leaving all 13 tables at 0 rows, after which a clean seed was loaded.

---

## 4. Manual API verification

Every endpoint was called against the running server. All returned the expected
status code.

### Endpoint sweep

25 base endpoints, 13 report endpoints, 12 filter and pagination combinations
and 4 deliberate 404s were exercised. Representative results:

| Endpoint | Status | Rows returned |
|---|---|---|
| `GET /api/health` | 200 | — |
| `GET /api/dashboard` | 200 | — |
| `GET /api/students` | 200 | total 40 |
| `GET /api/drives` | 200 | total 14 |
| `GET /api/applications` | 200 | total 64 |
| `GET /api/interviews` | 200 | total 156 |
| `GET /api/offers` | 200 | total 11 |
| `GET /api/placements` | 200 | total 5 |
| `GET /api/reports/applications-by-company` | 200 | 14 rows |
| `GET /api/reports/interview-progress` | 200 | 51 rows |
| `GET /api/reports/offers-by-status` | 200 | 5 rows |
| `GET /api/reports/students-without-applications` | 200 | 9 rows |
| `GET /api/reports/drives-without-applications` | 200 | 1 row |
| `GET /api/reports/accepted-offers-not-verified` | 200 | 1 row |
| `GET /api/students/99999` | 404 | — |
| `GET /api/reports/not-a-report` | 404 | — |

### Filters and pagination

| Request | Result |
|---|---|
| `GET /api/students?limit=5&offset=10` | 200, 5 items of 40 |
| `GET /api/students?min_cgpa=8&max_backlogs=0` | 200, total 6 |
| `GET /api/students?placed=true` | 200, total 5 |
| `GET /api/drives?drive_status=Open` | 200, total 7 |
| `GET /api/applications?application_status=Selected` | 200, total 11 |
| `GET /api/offers?unverified_only=true` | 200, total 1 |
| `GET /api/interviews?result=Pending` | 200, total 12 |

### Documented policies, checked against real seeded data

| Policy | Check | Result |
|---|---|---|
| P1 — missing criteria is not zero cut-offs | `GET /api/drives/37/eligibility-criteria` | Returned `null`; the eligible-students response carried `criteria_defined: false` and still listed 29 students |
| P2 — no department rows means open to all | Drive 38 has no `drive_eligible_department` rows | `department_restricted: false` |
| T3 / T5 — academic rules reject with reasons | Drive 34 against student `26BCD0002` | `eligible: false`, reasons: 3 active backlogs against a limit of 2, and batch 2026 against an eligible batch of 2027 |

---

## 5. Frontend verification

### Build and type check

```bash
cd frontend && npm run build
```

```
tsc --noEmit  (no errors)
vite v5.4.11 building for production...
✓ 50 modules transformed.
dist/index.html                   0.41 kB │ gzip:  0.28 kB
dist/assets/index-BFp_VqlT.css    7.86 kB │ gzip:  2.38 kB
dist/assets/index-KA-E8faU.js   227.90 kB │ gzip: 68.25 kB
✓ built in 590ms
```

### Dev server and proxy

`npm run dev` served the application on `http://127.0.0.1:5173` (HTTP 200), and
`GET http://127.0.0.1:5173/api/health` returned the live database facts through
the proxy, confirming the browser never needs the backend host or a credential.

### Rendered pages

All 15 routes were loaded in headless Chrome against the live database and
captured to `screenshots/`. Each page rendered real data, not placeholders. Two
display defects were found this way and fixed: the sidebar links were laying out
horizontally, and three badges were reusing unrelated status words. Both fixes
were re-captured.

### Write path verified end to end

A company was created by posting to `http://127.0.0.1:5173/api/companies`, which
is the exact network path the browser's form uses.

| Step | Result |
|---|---|
| `POST /api/companies` through the Vite proxy | `HTTP 201`, `company_id: 231` |
| Row present in MySQL | `SELECT` returned the row with `created_at 2026-10-14 15:17:58` |
| Visible in the rendered UI | Yes — `screenshots/P16_write_verification.png`, "Showing 1–11 of 11" |
| Duplicate name rejected | `HTTP 409`, "Violated constraint: company.uq_company_name" |

The verification row was then deleted, returning the company count to 10, so the
committed demo data matches the seed exactly.

---

## 6. What was and was not verified

| Claim | Status |
|---|---|
| Backend starts and serves | Tested successfully |
| Frontend starts and serves | Tested successfully |
| Database connectivity | Tested successfully |
| Seed script works and repeats safely | Tested successfully |
| Scoped reset works | Tested successfully |
| All 52 API endpoints return expected responses | Tested successfully |
| Database writes persist | Tested successfully |
| Constraints reject invalid data | Tested successfully, with real MySQL error numbers 1062, 1452, 3819 translated to 409 and 422 |
| Frontend displays actual database results | Tested successfully, by rendering all 15 routes |
| Automated tests pass | Tested successfully, 67 of 67 |
| Business rules T1–T8 and T10 | Implemented and tested |
| Business rule T9 | **Not implemented**, see the limitations section of the implementation document |
| React click handlers driven by an automated browser | **Not tested.** The endpoints behind every form are covered by the suite, and one write was verified through the browser's own network path, but no Playwright or Cypress suite clicks the buttons |
| Behaviour under concurrent load | **Not tested.** Correctness relies on the database `UNIQUE` constraints, which make the races impossible, but no load test was run |
| Behaviour at large data volumes | **Not tested.** The data set is 40 students and 14 drives |

---

## 7. Defects found and fixed during this phase

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 1 | A `CHECK` constraint violation returned HTTP 503 "database not available" instead of a client error | MySQL raises error 3819 through SQLAlchemy's `OperationalError`, not `IntegrityError`, so it fell through to the "server unreachable" branch | Moved the error number to HTTP status mapping into one shared table used by both handlers. Caught by `test_offer_joining_date_before_offer_date_rejected` |
| 2 | Sidebar navigation links laid out horizontally and overflowed | Each nav group was a block container whose anchors defaulted to inline | Made each group a column flex container and the anchors `display: block` |
| 3 | Badges showed "Intermediate" for an online interview and "Pass" for a mandatory skill | Status words were reused to borrow badge colours | Added the real words to the tone map and displayed the correct labels |
| 4 | Changing a drive's date left stale demo rows behind | `drive_date` is part of the drive's natural key, so changing it created new rows instead of updating | Used the scoped reset, then reseeded. Documented that a natural key change requires a reset |
