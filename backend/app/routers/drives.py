"""Companies and job drives, including eligibility configuration."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Connection, and_, func, or_, select

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
    assert_drive_status_transition,
    evaluate_eligibility,
    require,
    skill_match,
)
from ..schemas import (
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    DriveSkillIn,
    EligibilityCheckOut,
    EligibilityCriteriaIn,
    EligibilityCriteriaOut,
    JobDriveCreate,
    JobDriveUpdate,
    Page,
)

companies_router = APIRouter(tags=["companies"])
drives_router = APIRouter(tags=["job drives"])

Conn = Annotated[Connection, Depends(get_conn)]


# --- companies -----------------------------------------------------------


@companies_router.get("/companies", response_model=Page)
def list_companies(
    conn: Conn,
    q: str | None = None,
    industry: str | None = None,
    city: str | None = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    c, jd = t("company"), t("job_drive")
    stmt = (
        select(c, func.count(jd.c.drive_id).label("drive_count"))
        .select_from(c.outerjoin(jd, jd.c.company_id == c.c.company_id))
        .group_by(c.c.company_id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(c.c.company_name.like(like), c.c.industry.like(like)))
    if industry:
        stmt = stmt.where(c.c.industry == industry)
    if city:
        stmt = stmt.where(c.c.city == city)
    return paginate(conn, stmt.order_by(c.c.company_name), limit, offset)


@companies_router.get("/companies/{company_id}", summary="Company with its drives")
def get_company(company_id: int, conn: Conn) -> dict[str, Any]:
    company = require(conn, "company", "company_id", company_id)
    jd, app_t = t("job_drive"), t("application")
    drives = fetch_all(
        conn,
        select(jd, func.count(app_t.c.application_id).label("application_count"))
        .select_from(jd.outerjoin(app_t, app_t.c.drive_id == jd.c.drive_id))
        .where(jd.c.company_id == company_id)
        .group_by(jd.c.drive_id)
        .order_by(jd.c.drive_date.desc()),
    )
    return {**company, "drives": drives}


@companies_router.post("/companies", status_code=status.HTTP_201_CREATED, response_model=CompanyOut)
def create_company(payload: CompanyCreate, conn: Conn) -> dict[str, Any]:
    new_id = insert_returning_id(conn, "company", payload.model_dump(exclude_none=True))
    return require(conn, "company", "company_id", new_id)


@companies_router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, payload: CompanyUpdate, conn: Conn) -> dict[str, Any]:
    require(conn, "company", "company_id", company_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolation("No fields supplied to update.")
    update_by_pk(conn, "company", "company_id", company_id, data)
    return require(conn, "company", "company_id", company_id)


# --- job drives ----------------------------------------------------------


def _drive_select() -> Any:
    jd, c = t("job_drive"), t("company")
    return select(jd, c.c.company_name).select_from(
        jd.join(c, c.c.company_id == jd.c.company_id)
    )


@drives_router.get("/drives", response_model=Page, summary="Search and filter drives")
def list_drives(
    conn: Conn,
    q: str | None = Query(None, description="Matches job title or company name"),
    company_id: int | None = None,
    dept_id: int | None = Query(None, description="Drives this department is eligible for"),
    drive_status: str | None = None,
    job_type: str | None = None,
    batch_year: int | None = Query(None, description="From the drive's eligibility criteria"),
    min_ctc: float | None = Query(None, gt=0),
    max_ctc: float | None = Query(None, gt=0),
    sort: str = Query("drive_date", pattern="^(drive_date|apply_deadline|ctc_lpa|job_title)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    jd, c = t("job_drive"), t("company")
    app_t = t("application")
    stmt = (
        select(jd, c.c.company_name, func.count(app_t.c.application_id).label("application_count"))
        .select_from(
            jd.join(c, c.c.company_id == jd.c.company_id).outerjoin(
                app_t, app_t.c.drive_id == jd.c.drive_id
            )
        )
        .group_by(jd.c.drive_id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(jd.c.job_title.like(like), c.c.company_name.like(like)))
    if company_id is not None:
        stmt = stmt.where(jd.c.company_id == company_id)
    if drive_status:
        stmt = stmt.where(jd.c.drive_status == drive_status)
    if job_type:
        stmt = stmt.where(jd.c.job_type == job_type)
    if min_ctc is not None:
        stmt = stmt.where(jd.c.ctc_lpa >= min_ctc)
    if max_ctc is not None:
        stmt = stmt.where(jd.c.ctc_lpa <= max_ctc)
    if dept_id is not None:
        ded = t("drive_eligible_department")
        stmt = stmt.where(
            jd.c.drive_id.in_(select(ded.c.drive_id).where(ded.c.dept_id == dept_id))
        )
    if batch_year is not None:
        ec = t("eligibility_criteria")
        stmt = stmt.where(
            jd.c.drive_id.in_(
                select(ec.c.drive_id).where(ec.c.eligible_batch_year == batch_year)
            )
        )
    col = jd.c[sort]
    stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())
    return paginate(conn, stmt, limit, offset)


@drives_router.get("/drives/{drive_id}", summary="Drive detail with eligibility setup")
def get_drive(drive_id: int, conn: Conn) -> dict[str, Any]:
    jd = t("job_drive")
    drive = fetch_one(conn, _drive_select().where(jd.c.drive_id == drive_id))
    if drive is None:
        raise NotFound(f"job_drive drive_id={drive_id} not found")

    ded, d = t("drive_eligible_department"), t("department")
    departments = fetch_all(
        conn,
        select(d.c.dept_id, d.c.dept_code, d.c.dept_name)
        .select_from(ded.join(d, d.c.dept_id == ded.c.dept_id))
        .where(ded.c.drive_id == drive_id)
        .order_by(d.c.dept_code),
    )

    drs, sk = t("drive_required_skill"), t("skill")
    skills = fetch_all(
        conn,
        select(
            sk.c.skill_id, sk.c.skill_name, sk.c.skill_category,
            drs.c.is_mandatory, drs.c.min_proficiency,
        )
        .select_from(drs.join(sk, sk.c.skill_id == drs.c.skill_id))
        .where(drs.c.drive_id == drive_id)
        .order_by(drs.c.is_mandatory.desc(), sk.c.skill_name),
    )

    app_t, offer = t("application"), t("offer")
    stats = conn.execute(
        select(
            func.count(app_t.c.application_id).label("applications"),
            func.count(offer.c.offer_id).label("offers"),
        ).select_from(
            app_t.outerjoin(offer, offer.c.application_id == app_t.c.application_id)
        ).where(app_t.c.drive_id == drive_id)
    ).first()

    return {
        **drive,
        "eligibility_criteria": fetch_one(
            conn,
            select(t("eligibility_criteria")).where(
                t("eligibility_criteria").c.drive_id == drive_id
            ),
        ),
        "eligible_departments": departments,
        "required_skills": skills,
        "application_count": int(stats[0]) if stats else 0,
        "offer_count": int(stats[1]) if stats else 0,
    }


@drives_router.post("/drives", status_code=status.HTTP_201_CREATED)
def create_drive(payload: JobDriveCreate, conn: Conn) -> dict[str, Any]:
    require(conn, "company", "company_id", payload.company_id)
    if payload.apply_deadline > payload.drive_date:
        raise RuleViolation("apply_deadline must be on or before drive_date.")
    new_id = insert_returning_id(conn, "job_drive", payload.model_dump(exclude_none=True))
    return get_drive(new_id, conn)


@drives_router.patch("/drives/{drive_id}")
def update_drive(drive_id: int, payload: JobDriveUpdate, conn: Conn) -> dict[str, Any]:
    current = require(conn, "job_drive", "drive_id", drive_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolation("No fields supplied to update.")
    if "drive_status" in data and data["drive_status"] is not None:
        assert_drive_status_transition(current["drive_status"], data["drive_status"])
    deadline = data.get("apply_deadline", current["apply_deadline"])
    drive_date = data.get("drive_date", current["drive_date"])
    if deadline > drive_date:
        raise RuleViolation("apply_deadline must be on or before drive_date.")
    update_by_pk(conn, "job_drive", "drive_id", drive_id, data)
    return get_drive(drive_id, conn)


@drives_router.get("/drive-status-transitions", summary="The documented status policy")
def status_transitions() -> dict[str, list[str]]:
    from ..rules import DRIVE_STATUS_TRANSITIONS

    return {k: sorted(v) for k, v in DRIVE_STATUS_TRANSITIONS.items()}


# --- eligibility criteria (optional 1:1 dependent entity) ----------------


@drives_router.get(
    "/drives/{drive_id}/eligibility-criteria",
    response_model=EligibilityCriteriaOut | None,
    summary="Criteria row, or null when the drive defines none",
)
def get_criteria(drive_id: int, conn: Conn) -> dict[str, Any] | None:
    require(conn, "job_drive", "drive_id", drive_id)
    ec = t("eligibility_criteria")
    return fetch_one(conn, select(ec).where(ec.c.drive_id == drive_id))


@drives_router.put(
    "/drives/{drive_id}/eligibility-criteria",
    response_model=EligibilityCriteriaOut,
    summary="Create or replace the drive's criteria",
)
def put_criteria(
    drive_id: int, payload: EligibilityCriteriaIn, conn: Conn
) -> dict[str, Any]:
    require(conn, "job_drive", "drive_id", drive_id)
    ec = t("eligibility_criteria")
    data = payload.model_dump()
    rows = conn.execute(ec.update().where(ec.c.drive_id == drive_id).values(**data)).rowcount
    if not rows:
        conn.execute(ec.insert().values(drive_id=drive_id, **data))
    return fetch_one(conn, select(ec).where(ec.c.drive_id == drive_id)) or {}


# --- eligible departments and required skills ----------------------------


@drives_router.post(
    "/drives/{drive_id}/departments/{dept_id}", status_code=status.HTTP_201_CREATED
)
def add_eligible_department(drive_id: int, dept_id: int, conn: Conn) -> dict[str, Any]:
    require(conn, "job_drive", "drive_id", drive_id)
    require(conn, "department", "dept_id", dept_id)
    conn.execute(t("drive_eligible_department").insert().values(drive_id=drive_id, dept_id=dept_id))
    return {"drive_id": drive_id, "dept_id": dept_id}


@drives_router.delete(
    "/drives/{drive_id}/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_eligible_department(drive_id: int, dept_id: int, conn: Conn) -> None:
    ded = t("drive_eligible_department")
    rows = conn.execute(
        ded.delete().where(and_(ded.c.drive_id == drive_id, ded.c.dept_id == dept_id))
    ).rowcount
    if not rows:
        raise NotFound(f"drive_eligible_department ({drive_id}, {dept_id}) not found")


@drives_router.post("/drives/{drive_id}/skills", status_code=status.HTTP_201_CREATED)
def add_required_skill(drive_id: int, payload: DriveSkillIn, conn: Conn) -> dict[str, Any]:
    require(conn, "job_drive", "drive_id", drive_id)
    require(conn, "skill", "skill_id", payload.skill_id)
    conn.execute(
        t("drive_required_skill").insert().values(drive_id=drive_id, **payload.model_dump())
    )
    return {"drive_id": drive_id, **payload.model_dump()}


@drives_router.delete(
    "/drives/{drive_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_required_skill(drive_id: int, skill_id: int, conn: Conn) -> None:
    drs = t("drive_required_skill")
    rows = conn.execute(
        drs.delete().where(and_(drs.c.drive_id == drive_id, drs.c.skill_id == skill_id))
    ).rowcount
    if not rows:
        raise NotFound(f"drive_required_skill ({drive_id}, {skill_id}) not found")


# --- eligibility evaluation ----------------------------------------------


@drives_router.get(
    "/drives/{drive_id}/eligibility/{student_id}",
    response_model=EligibilityCheckOut,
    summary="Why one student is or is not eligible",
)
def check_eligibility(drive_id: int, student_id: int, conn: Conn) -> dict[str, Any]:
    return evaluate_eligibility(conn, student_id, drive_id)


@drives_router.get(
    "/drives/{drive_id}/eligible-students",
    summary="Students who satisfy the drive's criteria",
)
def eligible_students(
    drive_id: int,
    conn: Conn,
    include_skill_match: bool = Query(False, description="Also report skill coverage"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Set based eligibility, evaluated entirely in SQL.

    Avoids an N+1 pattern: one query filters the whole student table instead
    of calling evaluate_eligibility once per student.
    """
    require(conn, "job_drive", "drive_id", drive_id)
    s, d = t("student"), t("department")
    ec, ded = t("eligibility_criteria"), t("drive_eligible_department")
    app_t, offer, pr = t("application"), t("offer"), t("placement_record")

    criteria = fetch_one(conn, select(ec).where(ec.c.drive_id == drive_id))
    dept_ids = [
        int(r[0])
        for r in conn.execute(select(ded.c.dept_id).where(ded.c.drive_id == drive_id)).fetchall()
    ]

    stmt = (
        select(
            s.c.student_id, s.c.reg_no, s.c.first_name, s.c.last_name, s.c.email,
            s.c.cgpa, s.c.active_backlogs, s.c.tenth_pct, s.c.twelfth_pct,
            s.c.batch_year, d.c.dept_code, d.c.dept_name,
        )
        .select_from(s.join(d, d.c.dept_id == s.c.dept_id))
    )

    if dept_ids:
        stmt = stmt.where(s.c.dept_id.in_(dept_ids))

    if criteria:
        stmt = stmt.where(
            and_(
                s.c.cgpa >= criteria["min_cgpa"],
                s.c.active_backlogs <= criteria["max_backlogs"],
                s.c.batch_year == criteria["eligible_batch_year"],
                or_(s.c.tenth_pct >= criteria["min_tenth_pct"], criteria["min_tenth_pct"] <= 0),
                or_(s.c.twelfth_pct >= criteria["min_twelfth_pct"], criteria["min_twelfth_pct"] <= 0),
            )
        )
        if not criteria["allow_placed_students"]:
            placed_ids = (
                select(app_t.c.student_id)
                .select_from(
                    offer.join(app_t, app_t.c.application_id == offer.c.application_id)
                    .outerjoin(pr, pr.c.offer_id == offer.c.offer_id)
                )
                .where(or_(offer.c.offer_status == "Accepted", pr.c.placement_id.isnot(None)))
                .distinct()
            )
            stmt = stmt.where(s.c.student_id.notin_(placed_ids))

    # Exclude students who already applied.
    stmt = stmt.where(
        s.c.student_id.notin_(select(app_t.c.student_id).where(app_t.c.drive_id == drive_id))
    )

    page = paginate(conn, stmt.order_by(s.c.cgpa.desc(), s.c.reg_no), limit, offset)
    if include_skill_match:
        for row in page["items"]:
            row["skill_match"] = skill_match(conn, int(row["student_id"]), drive_id)
    page["criteria_defined"] = criteria is not None
    page["department_restricted"] = bool(dept_ids)
    return page


@drives_router.get(
    "/drives/{drive_id}/skill-match/{student_id}", summary="Skill coverage for one student"
)
def drive_skill_match(drive_id: int, student_id: int, conn: Conn) -> dict[str, Any]:
    require(conn, "job_drive", "drive_id", drive_id)
    require(conn, "student", "student_id", student_id)
    return skill_match(conn, student_id, drive_id)
