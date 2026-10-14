# API Reference — Phase 2

Base URL: `http://127.0.0.1:8000/api`
Interactive version, generated from the code: `http://127.0.0.1:8000/docs`

All request and response bodies are JSON.

---

## Conventions

### Pagination

Every list endpoint accepts `limit` and `offset` and returns:

```json
{ "items": [ ... ], "total": 64, "limit": 25, "offset": 0 }
```

`total` is the count **before** `limit` and `offset` are applied.

### Status codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 204 | Deleted, no body |
| 404 | A referenced record does not exist |
| 409 | A business rule was violated, or a `UNIQUE` / `FOREIGN KEY` constraint rejected the write |
| 422 | Input failed validation, or a database `CHECK` constraint rejected the value |
| 503 | The database is unreachable |

### Errors

```json
{ "detail": "Student is not eligible to apply to this drive.",
  "reasons": [ "CGPA 6.10 is below the required 8.00.",
               "Student has 3 active backlogs, the drive allows at most 2." ] }
```

`reasons` is present on business rule rejections so a caller can show the user
exactly what failed. No exception trace, SQL statement or connection string is
ever returned.

---

## Endpoints


### Health and dashboard

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/dashboard` | Aggregate counts for the dashboard | — |
| `GET` | `/api/health` | API and database health | — |

### Students and departments

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/departments` | List Departments | — |
| `GET` | `/api/departments/{dept_id}` | Get Department | — |
| `GET` | `/api/students` | Search and filter students | `q`, `dept_id`, `batch_year`, `min_cgpa`, `max_cgpa`, `max_backlogs`, `placed`, `sort`, `order`, `limit`, `offset` |
| `POST` | `/api/students` | Create Student | — |
| `GET` | `/api/students/{student_id}` | Student detail with skills and outcome | — |
| `PATCH` | `/api/students/{student_id}` | Update Student | — |
| `GET` | `/api/students/{student_id}/skills` | List Student Skills | — |
| `POST` | `/api/students/{student_id}/skills` | Add Student Skill | — |
| `PATCH` | `/api/students/{student_id}/skills/{skill_id}` | Update Student Skill | — |
| `DELETE` | `/api/students/{student_id}/skills/{skill_id}` | Remove Student Skill | — |

### Skills catalogue

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/skills` | List Skills | `category`, `q` |
| `GET` | `/api/skills/{skill_id}` | Get Skill | — |

### Companies

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/companies` | List Companies | `q`, `industry`, `city`, `limit`, `offset` |
| `POST` | `/api/companies` | Create Company | — |
| `GET` | `/api/companies/{company_id}` | Company with its drives | — |
| `PATCH` | `/api/companies/{company_id}` | Update Company | — |

### Job drives and eligibility

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/drive-status-transitions` | The documented status policy | — |
| `GET` | `/api/drives` | Search and filter drives | `q`, `company_id`, `dept_id`, `drive_status`, `job_type`, `batch_year`, `min_ctc`, `max_ctc`, `sort`, `order`, `limit`, `offset` |
| `POST` | `/api/drives` | Create Drive | — |
| `GET` | `/api/drives/{drive_id}` | Drive detail with eligibility setup | — |
| `PATCH` | `/api/drives/{drive_id}` | Update Drive | — |
| `POST` | `/api/drives/{drive_id}/departments/{dept_id}` | Add Eligible Department | — |
| `DELETE` | `/api/drives/{drive_id}/departments/{dept_id}` | Remove Eligible Department | — |
| `GET` | `/api/drives/{drive_id}/eligibility-criteria` | Criteria row, or null when the drive defines none | — |
| `PUT` | `/api/drives/{drive_id}/eligibility-criteria` | Create or replace the drive's criteria | — |
| `GET` | `/api/drives/{drive_id}/eligibility/{student_id}` | Why one student is or is not eligible | — |
| `GET` | `/api/drives/{drive_id}/eligible-students` | Students who satisfy the drive's criteria | `include_skill_match`, `limit`, `offset` |
| `GET` | `/api/drives/{drive_id}/skill-match/{student_id}` | Skill coverage for one student | — |
| `POST` | `/api/drives/{drive_id}/skills` | Add Required Skill | — |
| `DELETE` | `/api/drives/{drive_id}/skills/{skill_id}` | Remove Required Skill | — |

### Applications

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/applications` | List Applications | `student_id`, `drive_id`, `company_id`, `dept_id`, `application_status`, `limit`, `offset` |
| `POST` | `/api/applications` | Submit an application (full eligibility check) | — |
| `GET` | `/api/applications/{application_id}` | Application with interviews and offer | — |
| `PATCH` | `/api/applications/{application_id}` | Update Application Status | — |
| `GET` | `/api/applications/{application_id}/eligibility` | Re-run the eligibility report for an existing application | — |

### Interviews

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/interviews` | List Interviews | `application_id`, `result`, `round_type`, `limit`, `offset` |
| `POST` | `/api/interviews` | Create Interview | — |
| `GET` | `/api/interviews/{interview_id}` | Get Interview | — |
| `PATCH` | `/api/interviews/{interview_id}` | Update Interview | — |

### Offers

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/applications/{application_id}/offer` | The one offer for an application | — |
| `GET` | `/api/offers` | List Offers | `offer_status`, `company_id`, `student_id`, `unverified_only`, `limit`, `offset` |
| `POST` | `/api/offers` | Issue an offer | — |
| `GET` | `/api/offers/{offer_id}` | Get Offer | — |
| `PATCH` | `/api/offers/{offer_id}` | Update Offer | — |

### Verified placements

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/placements` | List Placements | `academic_year`, `dept_id`, `batch_year`, `company_id`, `limit`, `offset` |
| `POST` | `/api/placements` | Record a verified joining (accepted offers only) | — |
| `GET` | `/api/placements/{placement_id}` | Get Placement | — |
| `PATCH` | `/api/placements/{placement_id}` | Update Placement | — |

### Reports

| Method | Path | Description | Query parameters |
|---|---|---|---|
| `GET` | `/api/reports` | List the available reports | — |
| `GET` | `/api/reports/{name}` | Run one named report | `limit`, `offset` |

---

## Notable endpoints

### `GET /api/health`

Reports API liveness and database reachability separately, so a database
failure can be told apart from the service being down.

```json
{ "api": "ok", "database": "ok", "database_name": "smart_campus_placement",
  "mysql_version": "8.0.46-0ubuntu0.24.04.4", "table_count": 13, "detail": null }
```

`detail` names any missing Phase 1 table.

### `POST /api/applications`

Runs the full eligibility check before writing anything. Rejects with 409 and a
`reasons` list when the drive is not `Open`, the deadline has passed, the
student's department is not eligible, an academic cut-off is not met, the
student is already placed and the drive does not allow that, or the student has
already applied.

```json
{ "student_id": 82, "drive_id": 34 }
```

### `GET /api/drives/{drive_id}/eligibility/{student_id}`

Returns every rule that was checked, with required and actual values, so the
caller can explain a rejection rather than just report it.

```json
{ "student_id": 82, "drive_id": 34, "eligible": false,
  "criteria_defined": true, "department_restricted": true,
  "reasons": [ "Student has 3 active backlogs, the drive allows at most 2." ],
  "checks": [ { "name": "min_cgpa", "required": 6.5, "actual": 6.87, "passed": true } ] }
```

`criteria_defined: false` means the drive has no `eligibility_criteria` row, so
no academic gate applies. It never means the cut-offs are zero.

### `GET /api/drives/{drive_id}/eligible-students`

Evaluates the whole student table in one SQL statement rather than calling the
per student check in a loop. Students who already applied are excluded. The
response carries `criteria_defined` and `department_restricted` alongside the
usual pagination envelope.

### `POST /api/offers`

Creates the offer and sets `application.application_status` to `Selected` in the
same transaction, so the two can never disagree. At most one offer per
application, enforced by `uq_offer_application`.

### `POST /api/placements`

Allowed only when the offer's status is already `Accepted`. An accepted offer is
not automatically a verified placement: a placement record is a joining
confirmed by a named verifier. At most one per offer.

### `GET /api/reports/{name}`

Runs one of the 13 named queries. `GET /api/reports` lists them with
descriptions. Each query is a fixed statement; only `LIMIT` and `OFFSET` are
bound as parameters.

### `GET /api/drive-status-transitions`

The documented `drive_status` policy, served from the same constant the API
enforces.

```json
{ "Upcoming": ["Cancelled", "Open"], "Open": ["Cancelled", "Closed"],
  "Closed": ["Cancelled", "Completed"], "Completed": [], "Cancelled": [] }
```

