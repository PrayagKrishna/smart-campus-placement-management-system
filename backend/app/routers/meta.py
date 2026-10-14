"""Health checks and the dashboard summary."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, and_, func, select, text

from ..db import EXPECTED_TABLES, engine, get_conn, metadata, t
from ..schemas import HealthOut

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut, summary="API and database health")
def health() -> dict[str, Any]:
    """API liveness and database reachability, reported separately.

    The API part answers even when MySQL is down, so a failure can be told
    apart from the whole service being unreachable.
    """
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar_one()
            db_name = conn.execute(text("SELECT DATABASE()")).scalar_one()
            tables = set(metadata().tables)
        return {
            "api": "ok",
            "database": "ok",
            "database_name": db_name,
            "mysql_version": version,
            "table_count": len(tables),
            "detail": (
                None
                if EXPECTED_TABLES <= tables
                else "Missing Phase 1 tables: "
                + ", ".join(sorted(EXPECTED_TABLES - tables))
            ),
        }
    except Exception as exc:  # reported, never hidden
        return {
            "api": "ok",
            "database": "unavailable",
            "detail": type(exc).__name__,
        }


@router.get("/dashboard", summary="Aggregate counts for the dashboard")
def dashboard(conn: Annotated[Connection, Depends(get_conn)]) -> dict[str, Any]:
    """Every total is computed with SQL aggregation. Nothing is stored."""

    def n(stmt: Any) -> int:
        return int(conn.execute(stmt).scalar_one())

    student, company, drive = t("student"), t("company"), t("job_drive")
    app_t, iv, offer, pr = t("application"), t("interview"), t("offer"), t("placement_record")

    totals = {
        "students": n(select(func.count()).select_from(student)),
        "departments": n(select(func.count()).select_from(t("department"))),
        "skills": n(select(func.count()).select_from(t("skill"))),
        "companies": n(select(func.count()).select_from(company)),
        "job_drives": n(select(func.count()).select_from(drive)),
        "open_drives": n(
            select(func.count()).select_from(drive).where(drive.c.drive_status == "Open")
        ),
        "applications": n(select(func.count()).select_from(app_t)),
        "interviews": n(select(func.count()).select_from(iv)),
        "interviews_pending": n(
            select(func.count()).select_from(iv).where(iv.c.result == "Pending")
        ),
        "offers_issued": n(select(func.count()).select_from(offer)),
        "offers_accepted": n(
            select(func.count()).select_from(offer).where(offer.c.offer_status == "Accepted")
        ),
        "verified_placements": n(select(func.count()).select_from(pr)),
    }

    totals["placement_percentage"] = (
        round(100.0 * totals["verified_placements"] / totals["students"], 2)
        if totals["students"]
        else 0.0
    )

    avg_ctc = conn.execute(
        select(func.avg(offer.c.offered_ctc_lpa)).where(offer.c.offer_status == "Accepted")
    ).scalar_one()
    highest = conn.execute(select(func.max(offer.c.offered_ctc_lpa))).scalar_one()
    totals["average_accepted_ctc_lpa"] = float(avg_ctc) if avg_ctc is not None else None
    totals["highest_offer_ctc_lpa"] = float(highest) if highest is not None else None

    by_status = conn.execute(
        select(app_t.c.application_status, func.count().label("count"))
        .group_by(app_t.c.application_status)
        .order_by(func.count().desc())
    ).fetchall()
    offers_by_status = conn.execute(
        select(offer.c.offer_status, func.count().label("count"))
        .group_by(offer.c.offer_status)
        .order_by(func.count().desc())
    ).fetchall()

    return {
        "totals": totals,
        "applications_by_status": [
            {"application_status": r[0], "count": int(r[1])} for r in by_status
        ],
        "offers_by_status": [
            {"offer_status": r[0], "count": int(r[1])} for r in offers_by_status
        ],
    }
