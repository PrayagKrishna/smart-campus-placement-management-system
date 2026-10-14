"""Integration tests for the Phase 2 API, against the real MySQL schema.

Each test runs inside a transaction that is rolled back, so the seeded demo
data is never modified. See ``conftest.py``.
"""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db import EXPECTED_TABLES, metadata, t
from tests.conftest import API


# --- connectivity and schema --------------------------------------------


def test_database_connection_succeeds(client):
    body = client.get(f"{API}/health").json()
    assert body["api"] == "ok"
    assert body["database"] == "ok"
    assert body["database_name"] == "smart_campus_placement"
    assert body["mysql_version"].startswith("8.")


def test_all_thirteen_phase_one_tables_are_present():
    assert EXPECTED_TABLES <= set(metadata().tables)
    assert len(EXPECTED_TABLES) == 13


# --- retrieval ----------------------------------------------------------


def test_list_students_is_paginated(client):
    body = client.get(f"{API}/students?limit=5").json()
    assert body["limit"] == 5
    assert len(body["items"]) <= 5
    assert body["total"] >= len(body["items"])


def test_pagination_offset_returns_different_rows(client):
    first = client.get(f"{API}/students?limit=3&offset=0").json()["items"]
    second = client.get(f"{API}/students?limit=3&offset=3").json()["items"]
    assert [r["student_id"] for r in first] != [r["student_id"] for r in second]


def test_get_student_detail(client, make):
    dept = make.department()
    student_id = make.student(dept)
    body = client.get(f"{API}/students/{student_id}").json()
    assert body["student_id"] == student_id
    assert body["dept_id"] == dept
    assert body["dept_name"].startswith("Test Department")
    assert body["skills"] == []
    assert body["applications"] == []
    assert body["is_placed"] is False


def test_get_missing_student_returns_404(client):
    assert client.get(f"{API}/students/99999999").status_code == 404


def test_list_and_get_job_drive(client, make):
    company = make.company()
    drive = make.drive(company)
    make.criteria(drive)
    body = client.get(f"{API}/drives/{drive}").json()
    assert body["drive_id"] == drive
    assert body["company_id"] == company
    assert body["eligibility_criteria"]["drive_id"] == drive
    assert client.get(f"{API}/drives?limit=1").json()["total"] >= 1


def test_student_filters(client, make):
    dept = make.department()
    make.student(dept, cgpa="9.50", backlogs=0)
    make.student(dept, cgpa="5.50", backlogs=3)
    high = client.get(f"{API}/students?dept_id={dept}&min_cgpa=9").json()
    assert high["total"] == 1
    clean = client.get(f"{API}/students?dept_id={dept}&max_backlogs=0").json()
    assert clean["total"] == 1


# --- create and validate -------------------------------------------------


def test_create_student(client, make):
    dept = make.department()
    payload = {
        "reg_no": "TAPI0001",
        "first_name": "Api",
        "last_name": "Created",
        "email": "api.created@test.example",
        "dept_id": dept,
        "batch_year": 2026,
        "cgpa": "8.10",
    }
    response = client.post(f"{API}/students", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["reg_no"] == "TAPI0001"


def test_invalid_cgpa_rejected(client, make):
    dept = make.department()
    response = client.post(
        f"{API}/students",
        json={
            "reg_no": "TAPI0002",
            "first_name": "Bad",
            "email": "bad.cgpa@test.example",
            "dept_id": dept,
            "batch_year": 2026,
            "cgpa": "11.50",
        },
    )
    assert response.status_code == 422


def test_negative_backlogs_rejected(client, make):
    dept = make.department()
    response = client.post(
        f"{API}/students",
        json={
            "reg_no": "TAPI0003",
            "first_name": "Bad",
            "email": "bad.backlogs@test.example",
            "dept_id": dept,
            "batch_year": 2026,
            "active_backlogs": -1,
        },
    )
    assert response.status_code == 422


def test_duplicate_reg_no_rejected(client, make):
    dept = make.department()
    body = {
        "reg_no": "TAPI0004",
        "first_name": "First",
        "email": "first.dup@test.example",
        "dept_id": dept,
        "batch_year": 2026,
    }
    assert client.post(f"{API}/students", json=body).status_code == 201
    body["email"] = "second.dup@test.example"
    clash = client.post(f"{API}/students", json=body)
    assert clash.status_code == 409
    assert "uq_student_reg_no" in clash.json()["detail"]


def test_unknown_department_rejected(client):
    response = client.post(
        f"{API}/students",
        json={
            "reg_no": "TAPI0005",
            "first_name": "Orphan",
            "email": "orphan@test.example",
            "dept_id": 99999999,
            "batch_year": 2026,
        },
    )
    assert response.status_code == 404


# --- application rules ---------------------------------------------------


def test_valid_application_submission(client, make):
    student, drive = make.open_drive_for()
    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": drive}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["student_id"] == student
    assert body["drive_id"] == drive
    assert body["application_status"] == "Applied"


def test_duplicate_application_rejected(client, make):
    student, drive = make.open_drive_for()
    payload = {"student_id": student, "drive_id": drive}
    assert client.post(f"{API}/applications", json=payload).status_code == 201
    clash = client.post(f"{API}/applications", json=payload)
    assert clash.status_code == 409
    assert "already applied" in " ".join(clash.json()["reasons"]).lower()


def test_ineligible_student_rejected_on_cgpa(client, make):
    dept = make.department()
    company = make.company()
    drive = make.drive(company)
    make.criteria(drive, min_cgpa="8.00")
    make.eligible_dept(drive, dept)
    student = make.student(dept, cgpa="6.00")
    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": drive}
    )
    assert response.status_code == 409
    assert any("CGPA" in r for r in response.json()["reasons"])


def test_ineligible_student_rejected_on_backlogs(client, make):
    student, drive = make.open_drive_for(backlogs=5)
    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": drive}
    )
    assert response.status_code == 409
    assert any("backlog" in r.lower() for r in response.json()["reasons"])


def test_ineligible_student_rejected_on_batch_year(client, make):
    student, drive = make.open_drive_for(batch_year=2027)
    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": drive}
    )
    assert response.status_code == 409
    assert any("batch" in r.lower() for r in response.json()["reasons"])


def test_application_after_deadline_rejected(client, make):
    dept = make.department()
    company = make.company()
    drive = make.drive(company, deadline_offset=-5, drive_offset=-1)
    make.criteria(drive)
    make.eligible_dept(drive, dept)
    student = make.student(dept)
    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": drive}
    )
    assert response.status_code == 409
    assert any("deadline" in r.lower() for r in response.json()["reasons"])


def test_application_from_ineligible_department_rejected(client, make):
    allowed_dept = make.department()
    other_dept = make.department()
    company = make.company()
    drive = make.drive(company)
    make.criteria(drive)
    make.eligible_dept(drive, allowed_dept)
    outsider = make.student(other_dept)
    response = client.post(
        f"{API}/applications", json={"student_id": outsider, "drive_id": drive}
    )
    assert response.status_code == 409
    assert any("department" in r.lower() for r in response.json()["reasons"])


def test_application_to_drive_that_is_not_open_rejected(client, make):
    dept = make.department()
    company = make.company()
    drive = make.drive(company, status="Upcoming")
    make.criteria(drive)
    make.eligible_dept(drive, dept)
    student = make.student(dept)
    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": drive}
    )
    assert response.status_code == 409
    assert any("status" in r.lower() for r in response.json()["reasons"])


def test_placed_student_blocked_when_not_allowed(client, make):
    dept = make.department()
    company = make.company()

    first = make.drive(company)
    make.criteria(first)
    make.eligible_dept(first, dept)
    student = make.student(dept)
    application = make.application(student, first)
    make.offer(application, status="Accepted")

    second = make.drive(company)
    make.criteria(second, allow_placed=False)
    make.eligible_dept(second, dept)

    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": second}
    )
    assert response.status_code == 409
    assert any("already" in r.lower() for r in response.json()["reasons"])


def test_placed_student_allowed_when_drive_permits_it(client, make):
    dept = make.department()
    company = make.company()

    first = make.drive(company)
    make.criteria(first)
    make.eligible_dept(first, dept)
    student = make.student(dept)
    make.offer(make.application(student, first), status="Accepted")

    second = make.drive(company)
    make.criteria(second, allow_placed=True)
    make.eligible_dept(second, dept)

    response = client.post(
        f"{API}/applications", json={"student_id": student, "drive_id": second}
    )
    assert response.status_code == 201, response.text


def test_drive_without_criteria_has_no_academic_gate(client, make):
    """Policy P1 — missing criteria is reported, never read as zero cut-offs."""
    dept = make.department()
    company = make.company()
    drive = make.drive(company)
    make.eligible_dept(drive, dept)
    weak_student = make.student(dept, cgpa="4.00", backlogs=7, batch_year=2027)

    report = client.get(f"{API}/drives/{drive}/eligibility/{weak_student}").json()
    assert report["criteria_defined"] is False
    assert report["eligible"] is True

    assert client.get(f"{API}/drives/{drive}/eligibility-criteria").json() is None
    assert client.post(
        f"{API}/applications", json={"student_id": weak_student, "drive_id": drive}
    ).status_code == 201


def test_drive_without_eligible_departments_is_open_to_all(client, make):
    """Policy P2."""
    dept = make.department()
    company = make.company()
    drive = make.drive(company)
    make.criteria(drive)
    student = make.student(dept)
    report = client.get(f"{API}/drives/{drive}/eligibility/{student}").json()
    assert report["department_restricted"] is False
    assert report["eligible"] is True


def test_eligible_students_query_matches_per_student_check(client, make):
    """The set based SQL query must agree with the row by row evaluation."""
    dept = make.department()
    company = make.company()
    drive = make.drive(company)
    make.criteria(drive, min_cgpa="8.00")
    make.eligible_dept(drive, dept)
    good = make.student(dept, cgpa="9.20")
    bad = make.student(dept, cgpa="6.10")

    listed = {
        row["student_id"]
        for row in client.get(f"{API}/drives/{drive}/eligible-students?limit=500").json()["items"]
    }
    assert good in listed
    assert bad not in listed
    assert client.get(f"{API}/drives/{drive}/eligibility/{good}").json()["eligible"] is True
    assert client.get(f"{API}/drives/{drive}/eligibility/{bad}").json()["eligible"] is False


# --- drive status policy -------------------------------------------------


def test_drive_status_cannot_move_backwards(client, make):
    company = make.company()
    drive = make.drive(company, status="Completed")
    response = client.patch(f"{API}/drives/{drive}", json={"drive_status": "Open"})
    assert response.status_code == 409
    assert "cannot move" in response.json()["detail"]


def test_drive_status_forward_transition_allowed(client, make):
    company = make.company()
    drive = make.drive(company, status="Upcoming")
    response = client.patch(f"{API}/drives/{drive}", json={"drive_status": "Open"})
    assert response.status_code == 200
    assert response.json()["drive_status"] == "Open"


def test_drive_deadline_after_drive_date_rejected(client, make):
    company = make.company()
    today = date.today()
    response = client.post(
        f"{API}/drives",
        json={
            "company_id": company,
            "job_title": "Bad Dates Role",
            "ctc_lpa": "10.00",
            "apply_deadline": str(today + timedelta(days=20)),
            "drive_date": str(today + timedelta(days=5)),
        },
    )
    assert response.status_code == 409


# --- interview rules -----------------------------------------------------


def _interview_payload(application_id: int, **extra):
    body = {
        "application_id": application_id,
        "round_no": 1,
        "round_type": "Technical Interview",
        "mode": "Online",
        "scheduled_at": (datetime.now() + timedelta(days=2)).isoformat(timespec="seconds"),
    }
    body.update(extra)
    return body


def test_create_interview(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    response = client.post(f"{API}/interviews", json=_interview_payload(application))
    assert response.status_code == 201, response.text
    assert response.json()["round_no"] == 1


def test_interview_score_above_max_score_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    response = client.post(
        f"{API}/interviews",
        json=_interview_payload(application, score="95.00", max_score="50.00"),
    )
    assert response.status_code == 409
    assert "exceeds" in response.json()["detail"]


def test_duplicate_interview_round_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    assert client.post(f"{API}/interviews", json=_interview_payload(application)).status_code == 201
    clash = client.post(f"{API}/interviews", json=_interview_payload(application))
    assert clash.status_code == 409
    assert "already exists" in clash.json()["detail"]


def test_offline_interview_without_venue_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    response = client.post(
        f"{API}/interviews", json=_interview_payload(application, mode="Offline")
    )
    assert response.status_code == 409
    assert "venue" in response.json()["detail"].lower()


def test_interview_before_application_date_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive, applied_on=datetime.now())
    response = client.post(
        f"{API}/interviews",
        json=_interview_payload(
            application,
            scheduled_at=(datetime.now() - timedelta(days=30)).isoformat(timespec="seconds"),
        ),
    )
    assert response.status_code == 409
    assert "before the application" in response.json()["detail"]


def test_interview_for_unknown_application_rejected(client):
    response = client.post(f"{API}/interviews", json=_interview_payload(99999999))
    assert response.status_code == 404


# --- offer rules ---------------------------------------------------------


def _offer_payload(application_id: int, **extra):
    body = {
        "application_id": application_id,
        "offer_date": str(date.today()),
        "role_title": "Software Engineer",
        "offered_ctc_lpa": "12.00",
    }
    body.update(extra)
    return body


def test_create_offer_marks_application_selected(client, make):
    """Rule T6, in the same transaction as the insert."""
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    response = client.post(f"{API}/offers", json=_offer_payload(application))
    assert response.status_code == 201, response.text
    assert (
        client.get(f"{API}/applications/{application}").json()["application_status"]
        == "Selected"
    )


def test_duplicate_offer_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    assert client.post(f"{API}/offers", json=_offer_payload(application)).status_code == 201
    clash = client.post(f"{API}/offers", json=_offer_payload(application))
    assert clash.status_code == 409
    assert "already has an offer" in clash.json()["detail"]


def test_offer_joining_date_before_offer_date_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    response = client.post(
        f"{API}/offers",
        json=_offer_payload(
            application, expected_joining_date=str(date.today() - timedelta(days=10))
        ),
    )
    assert response.status_code in (409, 422)


def test_zero_ctc_offer_rejected(client, make):
    student, drive = make.open_drive_for()
    application = make.application(student, drive)
    response = client.post(
        f"{API}/offers", json=_offer_payload(application, offered_ctc_lpa="0.00")
    )
    assert response.status_code == 422


# --- placement record rules ---------------------------------------------


def _placement_payload(offer_id: int, **extra):
    body = {
        "offer_id": offer_id,
        "academic_year": "2026-2027",
        "verified_by": "Placement Cell",
    }
    body.update(extra)
    return body


def test_placement_against_non_accepted_offer_rejected(client, make):
    student, drive = make.open_drive_for()
    offer = make.offer(make.application(student, drive), status="Offered")
    response = client.post(f"{API}/placements", json=_placement_payload(offer))
    assert response.status_code == 409
    assert "Accepted" in response.json()["detail"]


def test_placement_against_accepted_offer_succeeds(client, make):
    student, drive = make.open_drive_for()
    offer = make.offer(make.application(student, drive), status="Accepted")
    response = client.post(f"{API}/placements", json=_placement_payload(offer))
    assert response.status_code == 201, response.text
    assert response.json()["offer_id"] == offer


def test_duplicate_placement_rejected(client, make):
    student, drive = make.open_drive_for()
    offer = make.offer(make.application(student, drive), status="Accepted")
    assert client.post(f"{API}/placements", json=_placement_payload(offer)).status_code == 201
    clash = client.post(f"{API}/placements", json=_placement_payload(offer))
    assert clash.status_code == 409
    assert "already has a verified placement" in clash.json()["detail"]


def test_bad_academic_year_format_rejected(client, make):
    student, drive = make.open_drive_for()
    offer = make.offer(make.application(student, drive), status="Accepted")
    response = client.post(
        f"{API}/placements", json=_placement_payload(offer, academic_year="2026/27")
    )
    assert response.status_code == 422


def test_accepted_offer_cannot_be_downgraded_while_placed(client, make):
    student, drive = make.open_drive_for()
    offer = make.offer(make.application(student, drive), status="Accepted")
    make.placement(offer)
    response = client.patch(f"{API}/offers/{offer}", json={"offer_status": "Revoked"})
    assert response.status_code == 409


# --- student skills (composite primary key) ------------------------------


def test_student_skill_lifecycle(client, make):
    dept = make.department()
    student = make.student(dept)
    skill = make.skill()

    created = client.post(
        f"{API}/students/{student}/skills",
        json={"skill_id": skill, "proficiency_level": "Beginner"},
    )
    assert created.status_code == 201, created.text

    clash = client.post(
        f"{API}/students/{student}/skills", json={"skill_id": skill}
    )
    assert clash.status_code == 409

    updated = client.patch(
        f"{API}/students/{student}/skills/{skill}",
        json={"proficiency_level": "Advanced"},
    )
    assert updated.status_code == 200
    assert updated.json()["proficiency_level"] == "Advanced"

    listed = client.get(f"{API}/students/{student}/skills").json()
    assert [r["skill_id"] for r in listed] == [skill]

    assert client.delete(f"{API}/students/{student}/skills/{skill}").status_code == 204
    assert client.get(f"{API}/students/{student}/skills").json() == []
    assert client.delete(f"{API}/students/{student}/skills/{skill}").status_code == 404


def test_invalid_proficiency_rejected(client, make):
    dept = make.department()
    student = make.student(dept)
    skill = make.skill()
    response = client.post(
        f"{API}/students/{student}/skills",
        json={"skill_id": skill, "proficiency_level": "Expert"},
    )
    assert response.status_code == 422


def test_skill_match_reports_coverage(client, make):
    dept = make.department()
    company = make.company()
    drive = make.drive(company)
    student = make.student(dept)
    skill_a, skill_b = make.skill(), make.skill()
    client.post(f"{API}/drives/{drive}/skills", json={"skill_id": skill_a, "min_proficiency": "Beginner"})
    client.post(f"{API}/drives/{drive}/skills", json={"skill_id": skill_b, "min_proficiency": "Advanced"})
    client.post(f"{API}/students/{student}/skills", json={"skill_id": skill_a, "proficiency_level": "Advanced"})

    body = client.get(f"{API}/drives/{drive}/skill-match/{student}").json()
    assert body["required_count"] == 2
    assert body["matched_count"] == 1
    assert body["all_mandatory_met"] is False


# --- dashboard and reports ----------------------------------------------


def test_dashboard_aggregation_matches_direct_sql(client, conn):
    totals = client.get(f"{API}/dashboard").json()["totals"]
    for key, table in [
        ("students", "student"),
        ("companies", "company"),
        ("job_drives", "job_drive"),
        ("applications", "application"),
        ("interviews", "interview"),
        ("offers_issued", "offer"),
        ("verified_placements", "placement_record"),
    ]:
        expected = int(conn.execute(select(func.count()).select_from(t(table))).scalar_one())
        assert totals[key] == expected, key

    offer = t("offer")
    accepted = int(
        conn.execute(
            select(func.count()).select_from(offer).where(offer.c.offer_status == "Accepted")
        ).scalar_one()
    )
    assert totals["offers_accepted"] == accepted


def test_dashboard_reacts_to_a_new_row(client, make):
    before = client.get(f"{API}/dashboard").json()["totals"]["students"]
    make.student(make.department())
    after = client.get(f"{API}/dashboard").json()["totals"]["students"]
    assert after == before + 1


@pytest.mark.parametrize(
    "name",
    [
        "applications-by-company",
        "interview-progress",
        "offers-by-status",
        "placements-by-batch",
        "placements-by-department",
        "placements-by-company",
        "students-without-applications",
        "applications-without-interviews",
        "drives-without-applications",
        "accepted-offers-not-verified",
        "skill-demand",
        "top-offers",
        "application-funnel",
    ],
)
def test_every_report_runs(client, name):
    response = client.get(f"{API}/reports/{name}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == name
    assert isinstance(body["rows"], list)


def test_unknown_report_returns_404(client):
    assert client.get(f"{API}/reports/not-a-report").status_code == 404


def test_accepted_offers_not_verified_report_is_consistent(client, make):
    student, drive = make.open_drive_for()
    offer = make.offer(make.application(student, drive), status="Accepted")
    rows = client.get(f"{API}/reports/accepted-offers-not-verified?limit=1000").json()["rows"]
    assert offer in [r["offer_id"] for r in rows]
    make.placement(offer)
    rows = client.get(f"{API}/reports/accepted-offers-not-verified?limit=1000").json()["rows"]
    assert offer not in [r["offer_id"] for r in rows]


# --- error hygiene -------------------------------------------------------


def test_errors_never_leak_internals(client, make):
    dept = make.department()
    body = {
        "reg_no": "TLEAK001",
        "first_name": "Leak",
        "email": "leak@test.example",
        "dept_id": dept,
        "batch_year": 2026,
    }
    assert client.post(f"{API}/students", json=body).status_code == 201
    body["email"] = "leak2@test.example"
    text = client.post(f"{API}/students", json=body).text.lower()
    for forbidden in ("traceback", "insert into", "pymysql", "password", "sqlalchemy"):
        assert forbidden not in text


def test_unknown_field_is_rejected(client, make):
    dept = make.department()
    response = client.post(
        f"{API}/students",
        json={
            "reg_no": "TAPI0099",
            "first_name": "Extra",
            "email": "extra@test.example",
            "dept_id": dept,
            "batch_year": 2026,
            "is_admin": True,
        },
    )
    assert response.status_code == 422


def test_empty_patch_rejected(client, make):
    dept = make.department()
    student = make.student(dept)
    assert client.patch(f"{API}/students/{student}", json={}).status_code == 409
