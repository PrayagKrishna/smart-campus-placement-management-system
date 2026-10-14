"""The placement workflow: application to interview to offer to placement."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Connection, func, select

from ..db import (
    fetch_all,
    fetch_one,
    get_conn,
    insert_returning_id,
    paginate,
    t,
    update_by_pk,
)
from ..rules import (
    NotFound,
    RuleViolation,
    assert_can_apply,
    assert_interview_ok,
    assert_offer_ok,
    assert_placement_ok,
    evaluate_eligibility,
    mark_application_selected,
    require,
)
from ..schemas import (
    ApplicationCreate,
    ApplicationStatusUpdate,
    InterviewCreate,
    InterviewOut,
    InterviewUpdate,
    OfferCreate,
    OfferUpdate,
    Page,
    PlacementCreate,
    PlacementUpdate,
)

applications_router = APIRouter(tags=["applications"])
interviews_router = APIRouter(tags=["interviews"])
offers_router = APIRouter(tags=["offers"])
placements_router = APIRouter(tags=["placements"])

Conn = Annotated[Connection, Depends(get_conn)]

def _student_name() -> Any:
    s = t("student")
    return func.trim(func.concat(s.c.first_name, " ", func.coalesce(s.c.last_name, ""))).label(
        "student_name"
    )


# --- applications --------------------------------------------------------


def _application_select() -> Any:
    a, s, jd, c = t("application"), t("student"), t("job_drive"), t("company")
    return select(
        a,
        s.c.reg_no,
        _student_name(),
        s.c.dept_id,
        jd.c.job_title,
        jd.c.ctc_lpa,
        jd.c.drive_status,
        c.c.company_id,
        c.c.company_name,
    ).select_from(
        a.join(s, s.c.student_id == a.c.student_id)
        .join(jd, jd.c.drive_id == a.c.drive_id)
        .join(c, c.c.company_id == jd.c.company_id)
    )


@applications_router.get("/applications", response_model=Page)
def list_applications(
    conn: Conn,
    student_id: int | None = None,
    drive_id: int | None = None,
    company_id: int | None = None,
    dept_id: int | None = None,
    application_status: str | None = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    a, s, jd = t("application"), t("student"), t("job_drive")
    stmt = _application_select()
    if student_id is not None:
        stmt = stmt.where(a.c.student_id == student_id)
    if drive_id is not None:
        stmt = stmt.where(a.c.drive_id == drive_id)
    if company_id is not None:
        stmt = stmt.where(jd.c.company_id == company_id)
    if dept_id is not None:
        stmt = stmt.where(s.c.dept_id == dept_id)
    if application_status:
        stmt = stmt.where(a.c.application_status == application_status)
    return paginate(conn, stmt.order_by(a.c.applied_on.desc()), limit, offset)


@applications_router.get(
    "/applications/{application_id}", summary="Application with interviews and offer"
)
def get_application(application_id: int, conn: Conn) -> dict[str, Any]:
    a = t("application")
    row = fetch_one(conn, _application_select().where(a.c.application_id == application_id))
    if row is None:
        raise NotFound(f"application application_id={application_id} not found")
    iv, offer, pr = t("interview"), t("offer"), t("placement_record")
    interviews = fetch_all(
        conn, select(iv).where(iv.c.application_id == application_id).order_by(iv.c.round_no)
    )
    offer_row = fetch_one(conn, select(offer).where(offer.c.application_id == application_id))
    placement = None
    if offer_row:
        placement = fetch_one(
            conn, select(pr).where(pr.c.offer_id == offer_row["offer_id"])
        )
    return {**row, "interviews": interviews, "offer": offer_row, "placement": placement}


@applications_router.post(
    "/applications",
    status_code=status.HTTP_201_CREATED,
    summary="Submit an application (full eligibility check)",
)
def create_application(payload: ApplicationCreate, conn: Conn) -> dict[str, Any]:
    """Every rule is checked here, so a direct API client cannot bypass them.

    The duplicate guard is also a UNIQUE constraint, so two concurrent
    requests cannot both succeed.
    """
    assert_can_apply(conn, payload.student_id, payload.drive_id)
    new_id = insert_returning_id(conn, "application", payload.model_dump(exclude_none=True))
    return get_application(new_id, conn)


@applications_router.patch("/applications/{application_id}")
def update_application_status(
    application_id: int, payload: ApplicationStatusUpdate, conn: Conn
) -> dict[str, Any]:
    require(conn, "application", "application_id", application_id)
    update_by_pk(
        conn, "application", "application_id", application_id,
        payload.model_dump(exclude_unset=True),
    )
    return get_application(application_id, conn)


@applications_router.get(
    "/applications/{application_id}/eligibility",
    summary="Re-run the eligibility report for an existing application",
)
def application_eligibility(application_id: int, conn: Conn) -> dict[str, Any]:
    app_row = require(conn, "application", "application_id", application_id)
    return evaluate_eligibility(
        conn,
        int(app_row["student_id"]),
        int(app_row["drive_id"]),
        enforce_drive_status=False,
    )


# --- interviews ----------------------------------------------------------


@interviews_router.get("/interviews", response_model=Page)
def list_interviews(
    conn: Conn,
    application_id: int | None = None,
    result: str | None = None,
    round_type: str | None = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    iv, a, s, jd, c = t("interview"), t("application"), t("student"), t("job_drive"), t("company")
    stmt = select(
        iv, s.c.reg_no, _student_name(), jd.c.job_title, c.c.company_name
    ).select_from(
        iv.join(a, a.c.application_id == iv.c.application_id)
        .join(s, s.c.student_id == a.c.student_id)
        .join(jd, jd.c.drive_id == a.c.drive_id)
        .join(c, c.c.company_id == jd.c.company_id)
    )
    if application_id is not None:
        stmt = stmt.where(iv.c.application_id == application_id)
    if result:
        stmt = stmt.where(iv.c.result == result)
    if round_type:
        stmt = stmt.where(iv.c.round_type == round_type)
    return paginate(conn, stmt.order_by(iv.c.scheduled_at.desc()), limit, offset)


@interviews_router.get("/interviews/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: int, conn: Conn) -> dict[str, Any]:
    return require(conn, "interview", "interview_id", interview_id)


@interviews_router.post(
    "/interviews", status_code=status.HTTP_201_CREATED, response_model=InterviewOut
)
def create_interview(payload: InterviewCreate, conn: Conn) -> dict[str, Any]:
    assert_interview_ok(
        conn,
        payload.application_id,
        payload.scheduled_at,
        payload.score,
        payload.max_score,
        round_no=payload.round_no,
    )
    if payload.mode == "Offline" and not payload.venue:
        raise RuleViolation("An offline interview round must name a venue.")
    new_id = insert_returning_id(conn, "interview", payload.model_dump(exclude_none=True))
    return require(conn, "interview", "interview_id", new_id)


@interviews_router.patch("/interviews/{interview_id}", response_model=InterviewOut)
def update_interview(
    interview_id: int, payload: InterviewUpdate, conn: Conn
) -> dict[str, Any]:
    current = require(conn, "interview", "interview_id", interview_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolation("No fields supplied to update.")
    merged = {**current, **data}
    assert_interview_ok(
        conn,
        int(current["application_id"]),
        merged["scheduled_at"],
        merged["score"],
        merged["max_score"],
        interview_id=interview_id,
    )
    if merged["mode"] == "Offline" and not merged["venue"]:
        raise RuleViolation("An offline interview round must name a venue.")
    update_by_pk(conn, "interview", "interview_id", interview_id, data)
    return require(conn, "interview", "interview_id", interview_id)


# --- offers --------------------------------------------------------------


def _offer_select() -> Any:
    offer, a, s, jd, c = t("offer"), t("application"), t("student"), t("job_drive"), t("company")
    return select(
        offer,
        a.c.student_id,
        a.c.drive_id,
        s.c.reg_no,
        _student_name(),
        s.c.dept_id,
        jd.c.job_title,
        c.c.company_id,
        c.c.company_name,
    ).select_from(
        offer.join(a, a.c.application_id == offer.c.application_id)
        .join(s, s.c.student_id == a.c.student_id)
        .join(jd, jd.c.drive_id == a.c.drive_id)
        .join(c, c.c.company_id == jd.c.company_id)
    )


@offers_router.get("/offers", response_model=Page)
def list_offers(
    conn: Conn,
    offer_status: str | None = None,
    company_id: int | None = None,
    student_id: int | None = None,
    unverified_only: bool = Query(
        False, description="Accepted offers with no verified placement yet"
    ),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    offer, a, jd, pr = t("offer"), t("application"), t("job_drive"), t("placement_record")
    stmt = _offer_select()
    if offer_status:
        stmt = stmt.where(offer.c.offer_status == offer_status)
    if company_id is not None:
        stmt = stmt.where(jd.c.company_id == company_id)
    if student_id is not None:
        stmt = stmt.where(a.c.student_id == student_id)
    if unverified_only:
        stmt = stmt.where(
            offer.c.offer_status == "Accepted",
            offer.c.offer_id.notin_(select(pr.c.offer_id)),
        )
    return paginate(conn, stmt.order_by(offer.c.offer_date.desc()), limit, offset)


@offers_router.get("/offers/{offer_id}")
def get_offer(offer_id: int, conn: Conn) -> dict[str, Any]:
    offer, pr = t("offer"), t("placement_record")
    row = fetch_one(conn, _offer_select().where(offer.c.offer_id == offer_id))
    if row is None:
        raise NotFound(f"offer offer_id={offer_id} not found")
    return {
        **row,
        "placement": fetch_one(conn, select(pr).where(pr.c.offer_id == offer_id)),
    }


@offers_router.post(
    "/offers", status_code=status.HTTP_201_CREATED, summary="Issue an offer"
)
def create_offer(payload: OfferCreate, conn: Conn) -> dict[str, Any]:
    """Creates the offer and moves the application to 'Selected' (rule T6).

    Both writes share one transaction, so a failure leaves neither behind.
    """
    assert_offer_ok(conn, payload.application_id)
    new_id = insert_returning_id(conn, "offer", payload.model_dump(exclude_none=True))
    mark_application_selected(conn, payload.application_id)
    return get_offer(new_id, conn)


@offers_router.patch("/offers/{offer_id}")
def update_offer(offer_id: int, payload: OfferUpdate, conn: Conn) -> dict[str, Any]:
    current = require(conn, "offer", "offer_id", offer_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolation("No fields supplied to update.")
    merged = {**current, **data}
    if merged["expected_joining_date"] and merged["expected_joining_date"] < merged["offer_date"]:
        raise RuleViolation("expected_joining_date cannot be before offer_date.")
    new_status = data.get("offer_status")
    if new_status and new_status != "Accepted" and current["offer_status"] == "Accepted":
        pr = t("placement_record")
        if conn.execute(
            select(func.count()).select_from(pr).where(pr.c.offer_id == offer_id)
        ).scalar_one():
            raise RuleViolation(
                "This offer has a verified placement record. Remove the placement "
                "record before changing the offer away from 'Accepted'."
            )
    update_by_pk(conn, "offer", "offer_id", offer_id, data)
    return get_offer(offer_id, conn)


@offers_router.get(
    "/applications/{application_id}/offer", summary="The one offer for an application"
)
def offer_for_application(application_id: int, conn: Conn) -> dict[str, Any]:
    offer = t("offer")
    row = fetch_one(conn, _offer_select().where(offer.c.application_id == application_id))
    if row is None:
        raise NotFound(f"no offer exists for application {application_id}")
    return row


# --- placement records ---------------------------------------------------


def _placement_select() -> Any:
    pr, offer, a, s, jd, c, d = (
        t("placement_record"), t("offer"), t("application"),
        t("student"), t("job_drive"), t("company"), t("department"),
    )
    return select(
        pr,
        offer.c.offered_ctc_lpa,
        offer.c.role_title,
        offer.c.offer_status,
        a.c.student_id,
        s.c.reg_no,
        _student_name(),
        s.c.batch_year,
        d.c.dept_id,
        d.c.dept_code,
        d.c.dept_name,
        c.c.company_id,
        c.c.company_name,
    ).select_from(
        pr.join(offer, offer.c.offer_id == pr.c.offer_id)
        .join(a, a.c.application_id == offer.c.application_id)
        .join(s, s.c.student_id == a.c.student_id)
        .join(d, d.c.dept_id == s.c.dept_id)
        .join(jd, jd.c.drive_id == a.c.drive_id)
        .join(c, c.c.company_id == jd.c.company_id)
    )


@placements_router.get("/placements", response_model=Page)
def list_placements(
    conn: Conn,
    academic_year: str | None = None,
    dept_id: int | None = None,
    batch_year: int | None = None,
    company_id: int | None = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    pr, s, jd = t("placement_record"), t("student"), t("job_drive")
    stmt = _placement_select()
    if academic_year:
        stmt = stmt.where(pr.c.academic_year == academic_year)
    if dept_id is not None:
        stmt = stmt.where(s.c.dept_id == dept_id)
    if batch_year is not None:
        stmt = stmt.where(s.c.batch_year == batch_year)
    if company_id is not None:
        stmt = stmt.where(jd.c.company_id == company_id)
    return paginate(conn, stmt.order_by(pr.c.verified_on.desc()), limit, offset)


@placements_router.get("/placements/{placement_id}")
def get_placement(placement_id: int, conn: Conn) -> dict[str, Any]:
    pr = t("placement_record")
    row = fetch_one(conn, _placement_select().where(pr.c.placement_id == placement_id))
    if row is None:
        raise NotFound(f"placement_record placement_id={placement_id} not found")
    return row


@placements_router.post(
    "/placements",
    status_code=status.HTTP_201_CREATED,
    summary="Record a verified joining (accepted offers only)",
)
def create_placement(payload: PlacementCreate, conn: Conn) -> dict[str, Any]:
    """Rule T1 — the offer must already be 'Accepted'.

    An offer is not a placement. A placement is a verified joining, confirmed
    by a named verifier.
    """
    assert_placement_ok(conn, payload.offer_id)
    new_id = insert_returning_id(
        conn, "placement_record", payload.model_dump(exclude_none=True)
    )
    return get_placement(new_id, conn)


@placements_router.patch("/placements/{placement_id}")
def update_placement(
    placement_id: int, payload: PlacementUpdate, conn: Conn
) -> dict[str, Any]:
    require(conn, "placement_record", "placement_id", placement_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolation("No fields supplied to update.")
    update_by_pk(conn, "placement_record", "placement_id", placement_id, data)
    return get_placement(placement_id, conn)
