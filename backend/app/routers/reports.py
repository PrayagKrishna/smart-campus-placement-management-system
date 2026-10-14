"""Reporting queries.

Every number here is derived with SQL aggregation at read time. No total is
stored in a base table, which is the Phase 1 design decision that kept the
schema in 3NF.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

from ..db import get_conn, rows_to_dicts

router = APIRouter(tags=["reports"])

Conn = Annotated[Connection, Depends(get_conn)]

STUDENT_NAME = "TRIM(CONCAT(s.first_name, ' ', COALESCE(s.last_name, '')))"

# Named, parameterised SQL. Keys become the /reports/{name} path value.
QUERIES: dict[str, dict[str, str]] = {
    "applications-by-company": {
        "description": "Application and offer counts per company and drive.",
        "sql": f"""
            SELECT  c.company_id,
                    c.company_name,
                    jd.drive_id,
                    jd.job_title,
                    jd.drive_status,
                    jd.ctc_lpa,
                    COUNT(DISTINCT a.application_id) AS applications,
                    COUNT(DISTINCT o.offer_id)       AS offers,
                    COUNT(DISTINCT CASE WHEN o.offer_status = 'Accepted'
                                        THEN o.offer_id END) AS accepted
            FROM        company   c
            JOIN        job_drive jd ON jd.company_id = c.company_id
            LEFT JOIN   application a ON a.drive_id = jd.drive_id
            LEFT JOIN   offer       o ON o.application_id = a.application_id
            GROUP BY    c.company_id, jd.drive_id
            ORDER BY    c.company_name, jd.drive_date DESC
        """,
    },
    "interview-progress": {
        "description": "Interview rounds completed and passed, per application.",
        "sql": f"""
            SELECT  a.application_id,
                    s.reg_no,
                    {STUDENT_NAME} AS student_name,
                    c.company_name,
                    jd.job_title,
                    a.application_status,
                    COUNT(i.interview_id)                                   AS total_rounds,
                    SUM(i.result = 'Pass')                                  AS rounds_passed,
                    SUM(i.result = 'Fail')                                  AS rounds_failed,
                    SUM(i.result = 'Pending')                               AS rounds_pending,
                    MAX(i.round_no)                                         AS latest_round,
                    ROUND(AVG(CASE WHEN i.score IS NOT NULL AND i.max_score > 0
                                   THEN 100 * i.score / i.max_score END), 2) AS avg_score_pct
            FROM        application a
            JOIN        student     s  ON s.student_id = a.student_id
            JOIN        job_drive   jd ON jd.drive_id  = a.drive_id
            JOIN        company     c  ON c.company_id = jd.company_id
            LEFT JOIN   interview   i  ON i.application_id = a.application_id
            GROUP BY    a.application_id
            HAVING      total_rounds > 0
            ORDER BY    total_rounds DESC, a.application_id
        """,
    },
    "offers-by-status": {
        "description": "Offer counts and average CTC grouped by offer status.",
        "sql": """
            SELECT  o.offer_status,
                    COUNT(*)                        AS offers,
                    ROUND(AVG(o.offered_ctc_lpa),2) AS avg_ctc_lpa,
                    MIN(o.offered_ctc_lpa)          AS min_ctc_lpa,
                    MAX(o.offered_ctc_lpa)          AS max_ctc_lpa
            FROM        offer o
            GROUP BY    o.offer_status
            ORDER BY    offers DESC
        """,
    },
    "placements-by-batch": {
        "description": "Verified placements grouped by student batch year.",
        "sql": """
            SELECT  s.batch_year,
                    COUNT(DISTINCT pr.placement_id)      AS placements,
                    COUNT(DISTINCT s.student_id)         AS students_placed,
                    ROUND(AVG(o.offered_ctc_lpa), 2)     AS avg_ctc_lpa,
                    MAX(o.offered_ctc_lpa)               AS highest_ctc_lpa
            FROM        placement_record pr
            JOIN        offer       o  ON o.offer_id      = pr.offer_id
            JOIN        application a  ON a.application_id = o.application_id
            JOIN        student     s  ON s.student_id     = a.student_id
            GROUP BY    s.batch_year
            ORDER BY    s.batch_year DESC
        """,
    },
    "placements-by-department": {
        "description": "Placement count and rate per department.",
        "sql": """
            SELECT  d.dept_id,
                    d.dept_code,
                    d.dept_name,
                    COUNT(DISTINCT s.student_id)  AS total_students,
                    COUNT(DISTINCT pr.placement_id) AS placements,
                    ROUND(100 * COUNT(DISTINCT pr.placement_id)
                              / NULLIF(COUNT(DISTINCT s.student_id), 0), 2) AS placement_pct,
                    ROUND(AVG(o.offered_ctc_lpa), 2) AS avg_ctc_lpa
            FROM        department d
            LEFT JOIN   student     s  ON s.dept_id = d.dept_id
            LEFT JOIN   application a  ON a.student_id = s.student_id
            LEFT JOIN   offer       o  ON o.application_id = a.application_id
            LEFT JOIN   placement_record pr ON pr.offer_id = o.offer_id
            GROUP BY    d.dept_id
            ORDER BY    placements DESC, d.dept_code
        """,
    },
    "placements-by-company": {
        "description": "Hires and average offered CTC per company.",
        "sql": """
            SELECT  c.company_id,
                    c.company_name,
                    c.industry,
                    COUNT(DISTINCT o.offer_id)       AS offers_issued,
                    COUNT(DISTINCT CASE WHEN o.offer_status = 'Accepted'
                                        THEN o.offer_id END) AS offers_accepted,
                    COUNT(DISTINCT pr.placement_id)  AS verified_placements,
                    ROUND(AVG(o.offered_ctc_lpa), 2) AS avg_offered_ctc_lpa,
                    MAX(o.offered_ctc_lpa)           AS highest_offered_ctc_lpa
            FROM        company   c
            JOIN        job_drive jd ON jd.company_id = c.company_id
            LEFT JOIN   application a ON a.drive_id = jd.drive_id
            LEFT JOIN   offer       o ON o.application_id = a.application_id
            LEFT JOIN   placement_record pr ON pr.offer_id = o.offer_id
            GROUP BY    c.company_id
            HAVING      offers_issued > 0
            ORDER BY    verified_placements DESC, avg_offered_ctc_lpa DESC
        """,
    },
    "students-without-applications": {
        "description": "Students who have not applied to any drive.",
        "sql": f"""
            SELECT  s.student_id,
                    s.reg_no,
                    {STUDENT_NAME} AS student_name,
                    d.dept_code,
                    s.batch_year,
                    s.cgpa,
                    s.active_backlogs
            FROM        student    s
            JOIN        department d ON d.dept_id = s.dept_id
            LEFT JOIN   application a ON a.student_id = s.student_id
            WHERE       a.application_id IS NULL
            ORDER BY    s.cgpa DESC, s.reg_no
        """,
    },
    "applications-without-interviews": {
        "description": "Applications that have no interview round scheduled.",
        "sql": f"""
            SELECT  a.application_id,
                    s.reg_no,
                    {STUDENT_NAME} AS student_name,
                    c.company_name,
                    jd.job_title,
                    a.application_status,
                    a.applied_on
            FROM        application a
            JOIN        student   s  ON s.student_id = a.student_id
            JOIN        job_drive jd ON jd.drive_id  = a.drive_id
            JOIN        company   c  ON c.company_id = jd.company_id
            LEFT JOIN   interview i  ON i.application_id = a.application_id
            WHERE       i.interview_id IS NULL
            ORDER BY    a.applied_on DESC
        """,
    },
    "drives-without-applications": {
        "description": "Drives that received no applications.",
        "sql": """
            SELECT  jd.drive_id,
                    c.company_name,
                    jd.job_title,
                    jd.job_type,
                    jd.ctc_lpa,
                    jd.drive_status,
                    jd.apply_deadline,
                    jd.drive_date
            FROM        job_drive jd
            JOIN        company   c ON c.company_id = jd.company_id
            LEFT JOIN   application a ON a.drive_id = jd.drive_id
            WHERE       a.application_id IS NULL
            ORDER BY    jd.drive_date DESC
        """,
    },
    "accepted-offers-not-verified": {
        "description": "Accepted offers with no verified placement record yet.",
        "sql": f"""
            SELECT  o.offer_id,
                    o.offer_date,
                    o.role_title,
                    o.offered_ctc_lpa,
                    o.expected_joining_date,
                    s.reg_no,
                    {STUDENT_NAME} AS student_name,
                    d.dept_code,
                    c.company_name
            FROM        offer       o
            JOIN        application a ON a.application_id = o.application_id
            JOIN        student     s ON s.student_id = a.student_id
            JOIN        department  d ON d.dept_id = s.dept_id
            JOIN        job_drive  jd ON jd.drive_id = a.drive_id
            JOIN        company     c ON c.company_id = jd.company_id
            LEFT JOIN   placement_record pr ON pr.offer_id = o.offer_id
            WHERE       o.offer_status = 'Accepted'
              AND       pr.placement_id IS NULL
            ORDER BY    o.expected_joining_date, o.offer_date
        """,
    },
    "skill-demand": {
        "description": "Most requested skills across drives, versus student supply.",
        "sql": """
            SELECT  sk.skill_id,
                    sk.skill_name,
                    sk.skill_category,
                    COUNT(DISTINCT drs.drive_id)   AS drives_requiring,
                    COUNT(DISTINCT CASE WHEN drs.is_mandatory = 1
                                        THEN drs.drive_id END) AS drives_mandatory,
                    COUNT(DISTINCT ss.student_id)  AS students_having
            FROM        skill sk
            LEFT JOIN   drive_required_skill drs ON drs.skill_id = sk.skill_id
            LEFT JOIN   student_skill        ss  ON ss.skill_id  = sk.skill_id
            GROUP BY    sk.skill_id
            ORDER BY    drives_requiring DESC, students_having DESC
        """,
    },
    "top-offers": {
        "description": "Highest offers, with the student and company behind each.",
        "sql": f"""
            SELECT  o.offer_id,
                    o.offered_ctc_lpa,
                    o.role_title,
                    o.offer_status,
                    o.offer_date,
                    s.reg_no,
                    {STUDENT_NAME} AS student_name,
                    s.cgpa,
                    d.dept_code,
                    c.company_name
            FROM        offer       o
            JOIN        application a ON a.application_id = o.application_id
            JOIN        student     s ON s.student_id = a.student_id
            JOIN        department  d ON d.dept_id = s.dept_id
            JOIN        job_drive  jd ON jd.drive_id = a.drive_id
            JOIN        company     c ON c.company_id = jd.company_id
            ORDER BY    o.offered_ctc_lpa DESC, o.offer_date DESC
        """,
    },
    "application-funnel": {
        "description": "The whole pipeline, counted stage by stage.",
        "sql": """
            SELECT 'Applications'        AS stage, COUNT(*) AS count FROM application
            UNION ALL
            SELECT 'Shortlisted',   COUNT(*) FROM application
                   WHERE application_status IN ('Shortlisted','Selected')
            UNION ALL
            SELECT 'Interviewed',   COUNT(DISTINCT application_id) FROM interview
            UNION ALL
            SELECT 'Offers issued', COUNT(*) FROM offer
            UNION ALL
            SELECT 'Offers accepted', COUNT(*) FROM offer WHERE offer_status = 'Accepted'
            UNION ALL
            SELECT 'Verified placements', COUNT(*) FROM placement_record
        """,
    },
}


@router.get("/reports", summary="List the available reports")
def list_reports() -> list[dict[str, str]]:
    return [{"name": k, "description": v["description"]} for k, v in QUERIES.items()]


@router.get("/reports/{name}", summary="Run one named report")
def run_report(
    name: str,
    conn: Conn,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Each report is a fixed SQL statement. Only LIMIT and OFFSET are bound,
    as parameters, so no part of the SQL is built from user input.
    """
    entry = QUERIES.get(name)
    if entry is None:
        from ..rules import NotFound

        raise NotFound(f"report '{name}' not found. See GET /reports.")
    stmt = text(f"{entry['sql']}\nLIMIT :limit OFFSET :offset")
    rows = conn.execute(stmt, {"limit": limit, "offset": offset}).fetchall()
    return {
        "name": name,
        "description": entry["description"],
        "rows": rows_to_dicts(rows),
        "row_count": len(rows),
        "limit": limit,
        "offset": offset,
    }
