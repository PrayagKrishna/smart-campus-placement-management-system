"""Students, departments and student skills."""

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
from ..rules import NotFound, RuleViolation, is_student_placed, require
from ..schemas import (
    DepartmentOut,
    Page,
    SkillOut,
    StudentCreate,
    StudentSkillIn,
    StudentSkillUpdate,
    StudentUpdate,
)

router = APIRouter(tags=["students"])

Conn = Annotated[Connection, Depends(get_conn)]


def _student_select() -> Any:
    s, d = t("student"), t("department")
    return select(
        s,
        d.c.dept_code,
        d.c.dept_name,
    ).select_from(s.join(d, d.c.dept_id == s.c.dept_id))


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(conn: Conn) -> list[dict[str, Any]]:
    d = t("department")
    return fetch_all(conn, select(d).order_by(d.c.dept_code))


@router.get("/departments/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int, conn: Conn) -> dict[str, Any]:
    return require(conn, "department", "dept_id", dept_id)


@router.get("/students", response_model=Page, summary="Search and filter students")
def list_students(
    conn: Conn,
    q: str | None = Query(None, description="Matches registration number, name or email"),
    dept_id: int | None = None,
    batch_year: int | None = None,
    min_cgpa: float | None = Query(None, ge=0, le=10),
    max_cgpa: float | None = Query(None, ge=0, le=10),
    max_backlogs: int | None = Query(None, ge=0),
    placed: bool | None = Query(None, description="Filter by verified placement"),
    sort: str = Query("reg_no", pattern="^(reg_no|cgpa|first_name|batch_year)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    s = t("student")
    stmt = _student_select()

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                s.c.reg_no.like(like),
                s.c.first_name.like(like),
                s.c.last_name.like(like),
                s.c.email.like(like),
            )
        )
    if dept_id is not None:
        stmt = stmt.where(s.c.dept_id == dept_id)
    if batch_year is not None:
        stmt = stmt.where(s.c.batch_year == batch_year)
    if min_cgpa is not None:
        stmt = stmt.where(s.c.cgpa >= min_cgpa)
    if max_cgpa is not None:
        stmt = stmt.where(s.c.cgpa <= max_cgpa)
    if max_backlogs is not None:
        stmt = stmt.where(s.c.active_backlogs <= max_backlogs)
    if placed is not None:
        app_t, offer, pr = t("application"), t("offer"), t("placement_record")
        placed_ids = (
            select(app_t.c.student_id)
            .select_from(
                pr.join(offer, offer.c.offer_id == pr.c.offer_id).join(
                    app_t, app_t.c.application_id == offer.c.application_id
                )
            )
            .distinct()
        )
        stmt = stmt.where(
            s.c.student_id.in_(placed_ids) if placed else s.c.student_id.notin_(placed_ids)
        )

    col = s.c[sort]
    stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())
    return paginate(conn, stmt, limit, offset)


@router.get("/students/{student_id}", summary="Student detail with skills and outcome")
def get_student(student_id: int, conn: Conn) -> dict[str, Any]:
    s = t("student")
    student = fetch_one(conn, _student_select().where(s.c.student_id == student_id))
    if student is None:
        raise NotFound(f"student student_id={student_id} not found")

    ss, sk = t("student_skill"), t("skill")
    skills = fetch_all(
        conn,
        select(sk.c.skill_id, sk.c.skill_name, sk.c.skill_category, ss.c.proficiency_level)
        .select_from(ss.join(sk, sk.c.skill_id == ss.c.skill_id))
        .where(ss.c.student_id == student_id)
        .order_by(sk.c.skill_category, sk.c.skill_name),
    )

    app_t, jd, c, offer, pr, iv = (
        t("application"), t("job_drive"), t("company"),
        t("offer"), t("placement_record"), t("interview"),
    )
    applications = fetch_all(
        conn,
        select(
            app_t.c.application_id,
            app_t.c.drive_id,
            app_t.c.applied_on,
            app_t.c.application_status,
            jd.c.job_title,
            jd.c.ctc_lpa,
            jd.c.drive_status,
            c.c.company_name,
            offer.c.offer_id,
            offer.c.offer_status,
            offer.c.offered_ctc_lpa,
            func.count(iv.c.interview_id).label("interview_rounds"),
        )
        .select_from(
            app_t.join(jd, jd.c.drive_id == app_t.c.drive_id)
            .join(c, c.c.company_id == jd.c.company_id)
            .outerjoin(offer, offer.c.application_id == app_t.c.application_id)
            .outerjoin(iv, iv.c.application_id == app_t.c.application_id)
        )
        .where(app_t.c.student_id == student_id)
        .group_by(app_t.c.application_id, offer.c.offer_id)
        .order_by(app_t.c.applied_on.desc()),
    )

    placement = fetch_one(
        conn,
        select(pr, offer.c.offered_ctc_lpa, offer.c.role_title, c.c.company_name)
        .select_from(
            pr.join(offer, offer.c.offer_id == pr.c.offer_id)
            .join(app_t, app_t.c.application_id == offer.c.application_id)
            .join(jd, jd.c.drive_id == app_t.c.drive_id)
            .join(c, c.c.company_id == jd.c.company_id)
        )
        .where(app_t.c.student_id == student_id),
    )

    return {
        **student,
        "skills": skills,
        "applications": applications,
        "placement": placement,
        "is_placed": is_student_placed(conn, student_id),
    }


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, conn: Conn) -> dict[str, Any]:
    require(conn, "department", "dept_id", payload.dept_id)
    new_id = insert_returning_id(conn, "student", payload.model_dump(exclude_none=True))
    s = t("student")
    return fetch_one(conn, _student_select().where(s.c.student_id == new_id)) or {}


@router.patch("/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdate, conn: Conn) -> dict[str, Any]:
    require(conn, "student", "student_id", student_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolation("No fields supplied to update.")
    if "dept_id" in data and data["dept_id"] is not None:
        require(conn, "department", "dept_id", data["dept_id"])
    update_by_pk(conn, "student", "student_id", student_id, data)
    s = t("student")
    return fetch_one(conn, _student_select().where(s.c.student_id == student_id)) or {}


# --- student skills ------------------------------------------------------


@router.get("/students/{student_id}/skills", response_model=list[dict])
def list_student_skills(student_id: int, conn: Conn) -> list[dict[str, Any]]:
    require(conn, "student", "student_id", student_id)
    ss, sk = t("student_skill"), t("skill")
    return fetch_all(
        conn,
        select(sk.c.skill_id, sk.c.skill_name, sk.c.skill_category, ss.c.proficiency_level)
        .select_from(ss.join(sk, sk.c.skill_id == ss.c.skill_id))
        .where(ss.c.student_id == student_id)
        .order_by(sk.c.skill_name),
    )


@router.post("/students/{student_id}/skills", status_code=status.HTTP_201_CREATED)
def add_student_skill(
    student_id: int, payload: StudentSkillIn, conn: Conn
) -> dict[str, Any]:
    """Insert one row of student_skill, whose PK is (student_id, skill_id)."""
    require(conn, "student", "student_id", student_id)
    require(conn, "skill", "skill_id", payload.skill_id)
    ss = t("student_skill")
    conn.execute(
        ss.insert().values(
            student_id=student_id,
            skill_id=payload.skill_id,
            proficiency_level=payload.proficiency_level,
        )
    )
    return {
        "student_id": student_id,
        "skill_id": payload.skill_id,
        "proficiency_level": payload.proficiency_level,
    }


@router.patch("/students/{student_id}/skills/{skill_id}")
def update_student_skill(
    student_id: int, skill_id: int, payload: StudentSkillUpdate, conn: Conn
) -> dict[str, Any]:
    ss = t("student_skill")
    rows = conn.execute(
        ss.update()
        .where(and_(ss.c.student_id == student_id, ss.c.skill_id == skill_id))
        .values(proficiency_level=payload.proficiency_level)
    ).rowcount
    if not rows:
        raise NotFound(f"student_skill ({student_id}, {skill_id}) not found")
    return {
        "student_id": student_id,
        "skill_id": skill_id,
        "proficiency_level": payload.proficiency_level,
    }


@router.delete("/students/{student_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_skill(student_id: int, skill_id: int, conn: Conn) -> None:
    ss = t("student_skill")
    rows = conn.execute(
        ss.delete().where(and_(ss.c.student_id == student_id, ss.c.skill_id == skill_id))
    ).rowcount
    if not rows:
        raise NotFound(f"student_skill ({student_id}, {skill_id}) not found")


# --- skills catalogue ----------------------------------------------------

skills_router = APIRouter(tags=["skills"])


@skills_router.get("/skills", response_model=list[SkillOut])
def list_skills(
    conn: Conn,
    category: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    sk = t("skill")
    stmt = select(sk)
    if category:
        stmt = stmt.where(sk.c.skill_category == category)
    if q:
        stmt = stmt.where(sk.c.skill_name.like(f"%{q}%"))
    return fetch_all(conn, stmt.order_by(sk.c.skill_category, sk.c.skill_name))


@skills_router.get("/skills/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, conn: Conn) -> dict[str, Any]:
    return require(conn, "skill", "skill_id", skill_id)
