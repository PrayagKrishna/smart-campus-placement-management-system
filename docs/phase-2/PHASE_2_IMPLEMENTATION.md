# Phase 2 — Application Implementation

Project: Smart Campus Placement Management System
Course: BACSE202 Database Systems · Fall Semester 2026–27
Phase 1 (database design and DDL) is complete and its schema is unchanged.

---

## 1. Phase 2 objectives

Phase 1 produced a normalised 13 table MySQL schema and the DDL that creates it.
It deliberately left two classes of rule unimplemented, because a MySQL `CHECK`
constraint may only read columns of the row being written:

* **Tier 2** rules T1–T10, which read another table or another row.
* **Tier 3** application logic: screening, ranking, reporting.

Phase 2 turns that schema into a working system:

1. Real MySQL connectivity from a Python backend.
2. Realistic, internally consistent demo data.
3. A REST API over the locked schema.
4. A browser dashboard that uses that API.
5. The Tier 2 and Tier 3 rules, enforced in the service layer.
6. Relational reporting queries.
7. Error handling and transaction safety.
8. Automated tests against the real database.

### What did not change

The Phase 1 schema is locked. No table, column, primary key, foreign key,
`UNIQUE`, `CHECK` or `ENUM` was added, renamed, relaxed or removed. No trigger
and no view was created. The backend **reflects** the live tables at runtime
rather than re-declaring them, so the application cannot drift from the DDL in
`database/`. The Phase 1 report is untouched.

---

## 2. Architecture

```
Browser  ──HTTP──▶  Vite dev server (5173)  ──proxy──▶  FastAPI (8000)  ──▶  MySQL 8.0.46
   React + TypeScript                                    SQLAlchemy 2.0 Core
                                                         PyMySQL
```

| Layer | Location | Responsibility |
|---|---|---|
| Configuration | `backend/app/config.py` | Reads the environment. Builds the connection URL. Never holds a credential. |
| Database access | `backend/app/db.py` | Engine, lazy schema reflection, one transaction per request, small query helpers. |
| Validation | `backend/app/schemas.py` | Pydantic request models mirroring the Phase 1 `CHECK` and `ENUM` domains, plus response models. |
| Business rules | `backend/app/rules.py` | The Tier 2 and Tier 3 rules, with the documented project policies. |
| Error translation | `backend/app/errors.py` | MySQL error numbers to HTTP status codes. No trace ever reaches a client. |
| HTTP routes | `backend/app/routers/` | `meta`, `students`, `drives`, `workflow`, `reports`. |
| Reporting SQL | `backend/app/routers/reports.py` | Thirteen named, parameterised queries. |
| Demo data | `backend/seed.py` | Idempotent seed, plus a scoped reset. |
| Tests | `backend/tests/` | Integration tests against the real database. |
| Frontend | `frontend/src/` | React 18, TypeScript, Vite. Thirteen screens. |

### Why the schema is reflected, not declared

`MetaData.reflect()` reads the live `smart_campus_placement` tables on first
use. There is no ORM model file that could disagree with `02_create_tables.sql`.
If a column were renamed in the database, the application would fail loudly
rather than silently write to a stale definition. Reflection is lazy, so the
process still starts and `/api/health` still answers when MySQL is down.

---

## 3. Database connectivity

| Item | Value |
|---|---|
| Server | MySQL 8.0.46-0ubuntu0.24.04.4 |
| Database | `smart_campus_placement` |
| Engine / charset | InnoDB · `utf8mb4` |
| Account | `campus_app@localhost` (database scoped, no global privileges) |
| Driver | PyMySQL 1.2.3 via SQLAlchemy 2.0.54 |
| Tables reflected | 13 of 13 |

### Credential handling

No password appears in source code, in a committed file, in a log line, in an
API response or in the frontend bundle.

Configuration comes from the environment or `backend/.env`, which is ignored by
git. `backend/.env.example` is committed and contains an **empty**
`DB_PASSWORD`.

When `DB_PASSWORD` is empty, the application passes `read_default_file` to the
MySQL driver, so the **driver** reads the local option file (`~/.my.cnf`) in the
same way the `mysql` command line client does. The application never opens,
copies, prints or commits that file. Set `DB_PASSWORD` instead if you prefer an
explicit environment variable.

The browser never receives a credential. In development the frontend calls a
relative `/api` path, which the Vite dev server proxies to the backend.

### Health endpoint

`GET /api/health` reports API liveness and database reachability **separately**,
so a database failure can be told apart from the service being down:

```json
{"api":"ok","database":"ok","database_name":"smart_campus_placement",
 "mysql_version":"8.0.46-0ubuntu0.24.04.4","table_count":13,"detail":null}
```

If any of the 13 Phase 1 tables were missing, `detail` would name them.

---

## 4. Data population

`backend/seed.py` creates realistic demo data. Every company and student is
fictional. No real student personal data is used.

### Repeatability

Each row is matched on its **natural key** (`dept_code`, `skill_name`,
`company_name`, `reg_no`, the drive's `(company_id, job_title, drive_date)`, and
the composite keys of the bridge tables). Running the script again updates
instead of duplicating. There is no `DROP TABLE`, no `TRUNCATE`, and foreign key
checks are never disabled. Running the seed three times in a row produced
identical row counts.

### Internal consistency

Applications are generated only for students who genuinely satisfy the drive's
criteria, so the seeded data obeys the same rules the API enforces. Application
dates never fall after a drive's deadline. Offers are issued only to applicants
who cleared every round. A placement record is written only for an accepted
offer whose joining date has already passed.

### Seeded volumes

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

The data deliberately covers the awkward cases:

* One drive has **no** `eligibility_criteria` row, exercising the optional
  one-to-one relationship and policy P1 below.
* One drive has **no** `drive_eligible_department` rows, exercising policy P2.
* Drives exist in the `Upcoming`, `Open`, `Closed`, `Completed` and `Cancelled`
  states.
* Applications exist in all five reachable statuses.
* Offers exist in all five statuses: `Offered`, `Accepted`, `Declined`,
  `Expired`, `Revoked`.
* Some accepted offers have no verified placement yet, which is a real
  operational state, not an error.

### Resetting demo data

```bash
.venv/bin/python seed.py --reset
```

This deletes **only** the departments, skills, companies and students named in
`seed.py`, children first. If a row you created yourself references demo data, a
`RESTRICT` foreign key stops the delete and the script reports it rather than
removing your work. `--summary` prints current row counts without writing.

---

## 5. Implemented API endpoints

52 endpoints. Interactive documentation is generated from the code at
`http://127.0.0.1:8000/docs`. The full table is in
[`API_REFERENCE.md`](API_REFERENCE.md).

| Area | Endpoints | Notes |
|---|---|---|
| Meta | 2 | Health, dashboard aggregation |
| Students & departments | 10 | Search, filter, create, update, skills |
| Skills catalogue | 2 | List and detail |
| Companies | 4 | List, detail with drives, create, update |
| Job drives | 14 | Search, detail, criteria, eligible departments and skills, eligibility evaluation |
| Applications | 5 | Submit with full rule checking, list, detail, status |
| Interviews | 4 | Schedule rounds, record results |
| Offers | 5 | Issue, list, detail, update status |
| Placements | 4 | Record and query verified joinings |
| Reports | 2 | Index plus a named report runner |

### Response conventions

Every list endpoint returns `{items, total, limit, offset}`. Errors return
`{"detail": "..."}`, and a rule violation adds `{"reasons": [...]}` so the
caller can show the user exactly what failed.

| Situation | Status |
|---|---|
| Created | 201 |
| Deleted | 204 |
| Referenced row missing | 404 |
| Business rule violated, duplicate key, foreign key violation | 409 |
| Input failed validation or a database `CHECK` | 422 |
| Database unreachable | 503 |

No exception trace, SQL statement or connection string is ever returned to a
client. A test asserts this.

---

## 6. Implemented frontend modules

React 18 with TypeScript, built by Vite. Thirteen screens, every one reading
live API data. There are no hardcoded arrays standing in for database rows.

| # | Screen | Route | What it does |
|---|---|---|---|
| 1 | Dashboard | `/` | Aggregate totals, status breakdowns, pipeline funnel, database state |
| 2 | Students | `/students` | Search and six filters, pagination, registration form |
| 3 | Student detail | `/students/:id` | Record, skills with add/edit/remove, applications, placement outcome |
| 4 | Companies | `/companies` | List with drive counts, create form |
| 5 | Company detail | `/companies/:id` | Contact details and the company's drives |
| 6 | Job drives | `/drives` | Six filters, pagination, create form |
| 7 | Drive detail | `/drives/:id` | Criteria, eligible departments, required skills, eligible students, applications, status transitions |
| 8 | Eligibility check | `/drives/:id/check/:studentId` | Every rule with required versus actual, plus skill coverage |
| 9 | Skills | `/skills` | Catalogue with demand versus student supply |
| 10 | Applications | `/applications` | Filters, pagination, submission form |
| 11 | Application detail | `/applications/:id` | Interview rounds, offer, placement, status actions |
| 12 | Interviews | `/interviews` | All rounds across applications, filters |
| 13 | Offers | `/offers` | Filters including "accepted but not verified" |
| 14 | Verified placements | `/placements` | Filters by academic year, department and batch |
| 15 | Reports | `/reports` | Runs any of the 13 named queries |

Loading, empty, success and error states are handled on every screen. Forms show
the backend's own rejection reasons rather than a generic failure message. The
layout is responsive and collapses to a menu button below 860 pixels. Colours
are defined as tokens and redefined for dark mode.

There is no authentication, because the assignment does not require one and a
fake login would prove nothing.

---

## 7. Business rules implemented

All rules are enforced in the **service layer**, so they apply to any caller,
including a direct API client. They are not frontend-only checks.

| Phase 1 rule | Where | Status |
|---|---|---|
| T1 — a placement record requires an `Accepted` offer | `rules.assert_placement_ok` | Implemented and tested |
| T2 — an application cannot be submitted after the deadline | `rules.evaluate_eligibility` | Implemented and tested |
| T3 — the applicant must satisfy the academic criteria | `rules.evaluate_eligibility` | Implemented and tested |
| T4 — the applicant's department must be eligible | `rules.evaluate_eligibility` | Implemented and tested |
| T5 — `allow_placed_students = FALSE` blocks placed applicants | `rules.evaluate_eligibility` | Implemented and tested |
| T6 — issuing an offer sets the application to `Selected` | `rules.mark_application_selected` | Implemented and tested |
| T7 — an interview cannot predate its application | `rules.assert_interview_ok` | Implemented and tested |
| T8 — `drive_status` may not move backwards | `rules.assert_drive_status_transition` | Implemented and tested |
| T9 — `company_employee_code` unique within one company | — | **Not implemented.** See section 12. |
| T10 — at most one offer per application | `rules.assert_offer_ok` plus `uq_offer_application` | Implemented and tested |

Additional rules enforced: a student may not apply twice to the same drive; an
offer may not have more than one placement record; an interview score may not
exceed its maximum score; a round number is unique within an application; an
offline round must name a venue; an accepted offer that already has a verified
placement cannot be downgraded.

### Documented project policies

Phase 1 left some cases open. They are decided here explicitly, not silently.

**P1 — a drive with no `eligibility_criteria` row has no academic gate.**
`eligibility_criteria` is an optional one-to-one dependent entity, so a drive may
legitimately have no row. Such a drive is reported as `criteria_defined: false`.
It is **not** treated as "all cut-offs are zero", because those are different
facts and a caller must be able to tell them apart. Department and deadline
rules still apply. The drive detail screen states this in plain words.

**P2 — a drive with no `drive_eligible_department` rows is open to every
department.** Once at least one row exists, the drive is restricted to the
listed departments only.

**P3 — "already placed" means the student holds an offer with status
`Accepted`, or a verified `placement_record`.** This is what
`allow_placed_students = FALSE` blocks.

**P4 — applications are accepted only while `drive_status = 'Open'`.**

**P5 — `drive_status` moves forward only**, along these transitions, which are
served at `GET /api/drive-status-transitions`:

```
Upcoming  → Open, Cancelled
Open      → Closed, Cancelled
Closed    → Completed, Cancelled
Completed → (terminal)
Cancelled → (terminal)
```

### Transactions and concurrency

Each request runs inside one transaction, opened by the `get_conn` dependency.
If a handler raises, the whole request rolls back. Issuing an offer writes to
`offer` and updates `application.application_status` in that single transaction,
so the two cannot disagree.

Where two concurrent requests could both pass an application level check, the
database is the real guard: `uq_application_student_drive`,
`uq_offer_application`, `uq_placement_offer` and `uq_interview_app_round` each
make the race impossible, and the resulting error number 1062 is translated to
HTTP 409 with the constraint named. The application level check exists to give a
helpful message, not to be the only defence.

### Triggers

None were created. The assignment specification does not require them and the
service layer with the existing `UNIQUE` constraints covers the same ground with
clearer errors. Phase 1 already recorded the limitation that a trigger validates
at write time only and cannot be deferred to the end of a transaction.

---

## 8. SQL queries and reports

Thirteen named queries are served from `GET /api/reports/{name}`. Each is a
fixed SQL statement; only `LIMIT` and `OFFSET` are bound, as parameters, so no
part of any statement is built from user input.

| Report | What it answers |
|---|---|
| `applications-by-company` | Applications, offers and acceptances per company and drive |
| `interview-progress` | Rounds completed, passed, failed and pending per application, with average score |
| `offers-by-status` | Offer counts with average, minimum and maximum CTC |
| `placements-by-batch` | Verified placements grouped by batch year |
| `placements-by-department` | Placement count and rate per department |
| `placements-by-company` | Hires and average offered CTC per company |
| `students-without-applications` | Students who have not applied anywhere |
| `applications-without-interviews` | Applications with no round scheduled |
| `drives-without-applications` | Drives that attracted nobody |
| `accepted-offers-not-verified` | Accepted offers still awaiting a verified joining |
| `skill-demand` | Skills ranked by drive demand against student supply |
| `top-offers` | Highest offers with the student and company behind each |
| `application-funnel` | The pipeline counted stage by stage |

Students eligible for a drive (`GET /api/drives/{id}/eligible-students`) and
skill matching (`GET /api/drives/{id}/skill-match/{studentId}`) are also set
based SQL, not per row Python loops.

These queries use inner and outer joins, `GROUP BY`, `HAVING`, `COUNT DISTINCT`,
conditional aggregation, `NULLIF` to avoid division by zero, correlated
`NOT IN` subqueries and `UNION ALL`.

**No derived total is stored.** `is_placed`, `total_applicants`,
`students_hired` and `current_round` are all computed at read time, which is
what kept the Phase 1 schema in 3NF. A test asserts that the dashboard totals
match a direct `COUNT(*)` on each table.

Avoiding N+1: the dashboard is a handful of aggregate statements, list endpoints
join their related tables in one statement, and eligibility for a whole cohort
is one query with the criteria pushed into the `WHERE` clause.

No view was created, so the Phase 1 guarantees are untouched.

---

## 9. Testing approach and results

`backend/tests/` holds 67 integration tests that run against the **real**
MySQL database, because the point of Phase 2 is that the application works
against the Phase 1 schema.

Isolation without a throwaway database: each test runs inside one transaction
that is rolled back afterwards, and the FastAPI `get_conn` dependency is
overridden so the route handler receives that same connection. Every write a
test makes disappears when it finishes. Nothing is dropped, nothing is
truncated, and no foreign key check is ever disabled. The seeded demo row counts
were identical before and after the suite ran.

**Result: 67 passed, 0 failed, in 0.96 s.** The per test list and the manual
verification log are in [`TEST_RESULTS.md`](TEST_RESULTS.md).

---

## 10. Setup and execution

### Prerequisites

MySQL 8.0.16 or later with the Phase 1 schema already created by the scripts in
`database/`, Python 3.12 or later, and Node.js 20 or later.

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env     # then set DB_USER, and DB_PASSWORD if you use one

.venv/bin/python seed.py                 # load the demo data
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
.venv/bin/python -m pytest -v
```

### Local URLs

| What | URL |
|---|---|
| Application | http://127.0.0.1:5173 |
| API root | http://127.0.0.1:8000/api |
| Interactive API documentation | http://127.0.0.1:8000/docs |
| Alternative API documentation | http://127.0.0.1:8000/redoc |
| Health check | http://127.0.0.1:8000/api/health |

---

## 11. Screenshots

All images in `screenshots/` were captured from the running application against
the live database. None is a mock-up.

| File | Screen |
|---|---|
| `P01_dashboard.png` | Dashboard with live totals |
| `P02_students.png` | Student list with filters and pagination |
| `P03_student_detail.png` | Student record, skills, applications |
| `P04_companies.png` | Company list |
| `P05_company_detail.png` | Company with its drives |
| `P06_drives.png` | Drive list with filters |
| `P07_drive_detail.png` | Drive with the "no criteria defined" policy notice |
| `P08_eligibility_check.png` | Every eligibility rule, required versus actual |
| `P09_skills.png` | Skill demand against supply |
| `P10_applications.png` | Application list |
| `P11_application_detail.png` | Interview rounds, offer, placement state |
| `P12_interviews.png` | All interview rounds |
| `P13_offers.png` | Offers with status filters |
| `P14_placements.png` | Verified placements |
| `P15_reports.png` | Report runner |
| `P16_write_verification.png` | A row written through the browser's own network path, visible in the UI |
| `P17_api_docs.png` | The generated OpenAPI documentation |

`P16` was produced by posting a company through the Vite proxy, confirming the
row in MySQL, and rendering the list. That verification row was deleted
afterwards, so the committed demo data matches the seed exactly.

---

## 12. Known limitations and pending work

1. **Rule T9 is not implemented.** `company_employee_code` is not checked for
   uniqueness within a company. It needs a scoped uniqueness check that the
   current schema does not express, and no Phase 2 screen depends on it.
2. **The React click handlers were not driven by an automated browser.** Every
   form posts to an endpoint that the 67 tests cover, and one write was verified
   end to end through the browser's own network path (`P16`), but there is no
   Playwright or Cypress suite clicking the buttons. A frontend end to end suite
   is the obvious next addition.
3. **No authentication or authorisation.** Any caller can reach any endpoint.
   This is deliberate for a local academic build; a real deployment would need
   role based access for the placement officer, the student and the recruiter.
4. **No `DELETE` endpoint for the main entities.** Only the two bridge table
   links (student skill, drive skill, eligible department) can be removed. The
   `RESTRICT` foreign keys make deleting a student or a company a policy
   decision rather than a technical one.
5. **No pagination on `GET /api/departments` and `GET /api/skills`.** Both are
   small reference lists.
6. **Offer expiry is not automatic.** An offer whose date has passed stays
   `Offered` until somebody changes it. A scheduled job would be needed.
7. **The dashboard recomputes every total on each request.** Correct, and fast
   at this data volume, but it would need caching or a materialised summary at a
   much larger scale.
8. **Interview rounds are not enforced to be contiguous.** Round 3 can be created
   without round 2. The schema permits it and no rule forbids it.

---

## 13. Next steps toward Phase 3

1. Role based access: placement officer, student and recruiter views over the
   same API.
2. A browser end to end test suite covering the form interactions.
3. Student self service: profile editing, resume upload, application tracking.
4. Notifications when a drive opens, a round is scheduled or an offer is issued.
5. Exporting the reports to CSV or PDF for the placement office.
6. An audit trail of status changes, which would need a new table and therefore
   an explicit schema decision rather than a silent one.
7. Deployment packaging and a production configuration with a proper secret
   store.
