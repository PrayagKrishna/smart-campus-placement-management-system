"""Business rules that no CHECK constraint can express.

Phase 1 documented these as Tier 2 / Tier 3 rules in ``database/README.md``
because a MySQL CHECK may only read columns of the row being written. They are
enforced here, in the service layer, so they apply to every caller of the API
and not only to the frontend.

Documented project policies, stated explicitly rather than left implicit:

P1. A drive with **no** ``eligibility_criteria`` row has **no academic gate**.
    It is treated as "criteria not defined", never as "all cut-offs are zero".
    The API reports ``criteria_defined: false`` so a caller can tell the two
    cases apart. Department and deadline rules still apply.

P2. A drive with **no** ``drive_eligible_department`` rows is open to every
    department. Once at least one row exists, the drive is restricted to the
    listed departments only.

P3. "Already placed" means the student holds an offer with status
    ``Accepted``, or a verified ``placement_record``. This is what
    ``allow_placed_students = FALSE`` blocks.

P4. A student may only apply while ``drive_status = 'Open'``.

P5. ``drive_status`` moves forward only, along the transitions in
    ``DRIVE_STATUS_TRANSITIONS``.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Connection, and_, func, or_, select

from .db import exists, fetch_all, fetch_one, get_by_pk, t

# P5 — allowed forward moves for drive_status (Tier 2 rule T8).
DRIVE_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "Upcoming": {"Open", "Cancelled"},
    "Open": {"Closed", "Cancelled"},
    "Closed": {"Completed", "Cancelled"},
    "Completed": set(),
    "Cancelled": set(),
}

PROFICIENCY_RANK = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}


class RuleViolation(Exception):
    """A business rule rejected the operation. Mapped to HTTP 409."""

    def __init__(self, message: str, reasons: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.reasons = reasons or []


class NotFound(Exception):
    """A referenced row does not exist. Mapped to HTTP 404."""


def require(conn: Connection, table: str, pk_col: str, pk_val: Any) -> dict[str, Any]:
    row = get_by_pk(conn, table, pk_col, pk_val)
    if row is None:
        raise NotFound(f"{table} {pk_col}={pk_val} not found")
    return row


# --- eligibility ----------------------------------------------------------


def is_student_placed(conn: Connection, student_id: int) -> bool:
    """P3 — an Accepted offer or a verified placement counts as placed."""
    app_t, offer_t, pr_t = t("application"), t("offer"), t("placement_record")
    stmt = (
        select(func.count())
        .select_from(
            offer_t.join(app_t, app_t.c.application_id == offer_t.c.application_id)
            .outerjoin(pr_t, pr_t.c.offer_id == offer_t.c.offer_id)
        )
        .where(
            and_(
                app_t.c.student_id == student_id,
                or_(
                    offer_t.c.offer_status == "Accepted",
                    pr_t.c.placement_id.isnot(None),
                ),
            )
        )
    )
    return int(conn.execute(stmt).scalar_one()) > 0


def eligible_department_ids(conn: Connection, drive_id: int) -> list[int]:
    ded = t("drive_eligible_department")
    rows = conn.execute(
        select(ded.c.dept_id).where(ded.c.drive_id == drive_id)
    ).fetchall()
    return [int(r[0]) for r in rows]


def _check(name: str, required: Any, actual: Any, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "required": _plain(required),
        "actual": _plain(actual),
        "passed": passed,
    }


def _plain(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def evaluate_eligibility(
    conn: Connection,
    student_id: int,
    drive_id: int,
    *,
    enforce_drive_status: bool = True,
    on_date: date | None = None,
) -> dict[str, Any]:
    """Full eligibility report for one student against one drive.

    Returns every individual check, not just a boolean, so the frontend can
    explain *why* a student was rejected.
    """
    student = require(conn, "student", "student_id", student_id)
    drive = require(conn, "job_drive", "drive_id", drive_id)
    today = on_date or date.today()

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []

    # P4 — drive must be open for applications.
    if enforce_drive_status:
        ok = drive["drive_status"] == "Open"
        checks.append(_check("drive_status", "Open", drive["drive_status"], ok))
        if not ok:
            reasons.append(
                f"Drive status is '{drive['drive_status']}', applications are "
                "only accepted while the status is 'Open'."
            )

    # T2 — application deadline.
    deadline = drive["apply_deadline"]
    ok = today <= deadline
    checks.append(_check("apply_deadline", f"on or before {deadline}", today, ok))
    if not ok:
        reasons.append(f"Application deadline passed on {deadline}.")

    # T4 / P2 — department restriction.
    dept_ids = eligible_department_ids(conn, drive_id)
    department_restricted = bool(dept_ids)
    if department_restricted:
        ok = int(student["dept_id"]) in dept_ids
        checks.append(_check("eligible_department", dept_ids, student["dept_id"], ok))
        if not ok:
            reasons.append(
                "Student's department is not in the drive's eligible department list."
            )

    # T3 / T5 / P1 — academic criteria.
    criteria = get_by_pk(conn, "eligibility_criteria", "drive_id", drive_id)
    criteria_defined = criteria is not None

    if criteria_defined:
        assert criteria is not None
        pairs = [
            ("min_cgpa", student["cgpa"], criteria["min_cgpa"], "CGPA"),
            ("min_tenth_pct", student["tenth_pct"], criteria["min_tenth_pct"], "10th percentage"),
            ("min_twelfth_pct", student["twelfth_pct"], criteria["min_twelfth_pct"], "12th percentage"),
        ]
        for key, actual, minimum, label in pairs:
            if actual is None:
                ok = Decimal(minimum) <= 0
                if not ok:
                    reasons.append(
                        f"{label} is not recorded for this student, but the drive "
                        f"requires at least {minimum}."
                    )
            else:
                ok = Decimal(actual) >= Decimal(minimum)
                if not ok:
                    reasons.append(f"{label} {actual} is below the required {minimum}.")
            checks.append(_check(key, minimum, actual, ok))

        ok = int(student["active_backlogs"]) <= int(criteria["max_backlogs"])
        checks.append(
            _check("max_backlogs", criteria["max_backlogs"], student["active_backlogs"], ok)
        )
        if not ok:
            reasons.append(
                f"Student has {student['active_backlogs']} active backlogs, the "
                f"drive allows at most {criteria['max_backlogs']}."
            )

        ok = int(student["batch_year"]) == int(criteria["eligible_batch_year"])
        checks.append(
            _check("eligible_batch_year", criteria["eligible_batch_year"], student["batch_year"], ok)
        )
        if not ok:
            reasons.append(
                f"Drive is open to batch {criteria['eligible_batch_year']} only, "
                f"student is batch {student['batch_year']}."
            )

        if not criteria["allow_placed_students"]:
            placed = is_student_placed(conn, student_id)
            ok = not placed
            checks.append(_check("allow_placed_students", "not already placed", placed, ok))
            if not ok:
                reasons.append(
                    "Student already holds an accepted offer or a verified "
                    "placement, and this drive does not allow placed students."
                )
    else:
        # P1 — reported, never silently treated as zero cut-offs.
        checks.append(
            _check("eligibility_criteria", "optional", "not defined for this drive", True)
        )

    # Duplicate application (also guarded by uq_application_student_drive).
    already = exists(conn, "application", student_id=student_id, drive_id=drive_id)
    checks.append(_check("duplicate_application", "no existing application", already, not already))
    if already:
        reasons.append("Student has already applied to this drive.")

    return {
        "student_id": student_id,
        "drive_id": drive_id,
        "eligible": not reasons,
        "criteria_defined": criteria_defined,
        "department_restricted": department_restricted,
        "reasons": reasons,
        "checks": checks,
    }


def assert_can_apply(conn: Connection, student_id: int, drive_id: int) -> None:
    report = evaluate_eligibility(conn, student_id, drive_id)
    if not report["eligible"]:
        raise RuleViolation(
            "Student is not eligible to apply to this drive.", report["reasons"]
        )


# --- drive status ---------------------------------------------------------


def assert_drive_status_transition(current: str, new: str) -> None:
    if current == new:
        return
    allowed = DRIVE_STATUS_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise RuleViolation(
            f"Drive status cannot move from '{current}' to '{new}'. "
            f"Allowed from '{current}': {sorted(allowed) or 'none (terminal state)'}."
        )


# --- interview -----------------------------------------------------------


def assert_interview_ok(
    conn: Connection,
    application_id: int,
    scheduled_at: datetime | None,
    score: Decimal | None,
    max_score: Decimal | None,
    *,
    round_no: int | None = None,
    interview_id: int | None = None,
) -> None:
    application = require(conn, "application", "application_id", application_id)

    # T7 — an interview cannot predate the application.
    if scheduled_at is not None and scheduled_at < application["applied_on"]:
        raise RuleViolation(
            f"Interview is scheduled at {scheduled_at}, which is before the "
            f"application date {application['applied_on']}."
        )

    # Mirrors chk_interview_score_max so the caller gets a clear 409, not a 3819.
    if score is not None and max_score is not None and score > max_score:
        raise RuleViolation(f"Score {score} exceeds the maximum score {max_score}.")
    if score is not None and max_score is None:
        raise RuleViolation("A score cannot be recorded without a maximum score.")

    # Mirrors uq_interview_app_round.
    if round_no is not None:
        iv = t("interview")
        stmt = select(func.count()).select_from(iv).where(
            and_(iv.c.application_id == application_id, iv.c.round_no == round_no)
        )
        if interview_id is not None:
            stmt = stmt.where(iv.c.interview_id != interview_id)
        if int(conn.execute(stmt).scalar_one()) > 0:
            raise RuleViolation(
                f"Round {round_no} already exists for application {application_id}."
            )


# --- offer ---------------------------------------------------------------


def assert_offer_ok(conn: Connection, application_id: int) -> None:
    require(conn, "application", "application_id", application_id)
    # T10 / one-offer policy, also guarded by uq_offer_application.
    if exists(conn, "offer", application_id=application_id):
        raise RuleViolation(
            f"Application {application_id} already has an offer. "
            "Exactly one offer per application is allowed."
        )


def mark_application_selected(conn: Connection, application_id: int) -> None:
    """T6 — issuing an offer moves the application to 'Selected'.

    Runs in the caller's transaction, so the offer and the status change commit
    or roll back together.
    """
    app_t = t("application")
    conn.execute(
        app_t.update()
        .where(app_t.c.application_id == application_id)
        .values(application_status="Selected")
    )


# --- placement record ----------------------------------------------------


def assert_placement_ok(conn: Connection, offer_id: int) -> dict[str, Any]:
    offer = require(conn, "offer", "offer_id", offer_id)
    # T1 — a placement may only be recorded against an accepted offer.
    if offer["offer_status"] != "Accepted":
        raise RuleViolation(
            f"Offer {offer_id} has status '{offer['offer_status']}'. A placement "
            "record may only be created against an 'Accepted' offer."
        )
    # Also guarded by uq_placement_offer.
    if exists(conn, "placement_record", offer_id=offer_id):
        raise RuleViolation(f"Offer {offer_id} already has a verified placement record.")
    return offer


# --- skill matching ------------------------------------------------------


def skill_match(conn: Connection, student_id: int, drive_id: int) -> dict[str, Any]:
    """How well a student's skills cover a drive's required skills."""
    drs, ss, sk = t("drive_required_skill"), t("student_skill"), t("skill")
    required = fetch_all(
        conn,
        select(
            drs.c.skill_id,
            sk.c.skill_name,
            drs.c.is_mandatory,
            drs.c.min_proficiency,
            ss.c.proficiency_level,
        )
        .select_from(
            drs.join(sk, sk.c.skill_id == drs.c.skill_id).outerjoin(
                ss,
                and_(ss.c.skill_id == drs.c.skill_id, ss.c.student_id == student_id),
            )
        )
        .where(drs.c.drive_id == drive_id)
        .order_by(drs.c.is_mandatory.desc(), sk.c.skill_name),
    )
    for row in required:
        held = row["proficiency_level"]
        row["held"] = held is not None
        row["meets_proficiency"] = bool(
            held is not None
            and PROFICIENCY_RANK[held] >= PROFICIENCY_RANK[row["min_proficiency"]]
        )
    mandatory = [r for r in required if r["is_mandatory"]]
    return {
        "student_id": student_id,
        "drive_id": drive_id,
        "required_count": len(required),
        "matched_count": sum(1 for r in required if r["meets_proficiency"]),
        "mandatory_count": len(mandatory),
        "mandatory_matched": sum(1 for r in mandatory if r["meets_proficiency"]),
        "all_mandatory_met": all(r["meets_proficiency"] for r in mandatory),
        "skills": required,
    }


def fetch_one_or_none(conn: Connection, stmt: Any) -> dict[str, Any] | None:
    return fetch_one(conn, stmt)
