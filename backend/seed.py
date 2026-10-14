"""Repeatable demo data for the Smart Campus Placement Management System.

Run from the ``backend`` directory:

    .venv/bin/python seed.py            # insert or refresh the demo data
    .venv/bin/python seed.py --summary   # just print current row counts
    .venv/bin/python seed.py --reset     # remove ONLY the demo rows listed here

Design notes
------------
* Every row is matched on its **natural key**, so running the script twice
  updates instead of duplicating. There is no ``DROP TABLE`` and no
  ``TRUNCATE``, and foreign key checks are never disabled.
* ``--reset`` deletes only the departments, skills, companies and students
  named in the constants below, child rows first. If a row you created
  yourself references demo data, a RESTRICT foreign key stops the delete and
  the script reports it rather than removing your data.
* All people and companies here are fictional. No real student data is used.
* Applications are only generated for students who genuinely satisfy the
  drive's criteria, so the seeded data obeys the same business rules the API
  enforces.
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Connection, and_, func, select

from app.db import engine, t

RNG = random.Random(25_2223)
TODAY = date(2026, 10, 14)
ACADEMIC_YEAR = "2026-2027"

DEPARTMENTS = [
    ("CSE", "Computer Science and Engineering"),
    ("IT", "Information Technology"),
    ("ECE", "Electronics and Communication Engineering"),
    ("EEE", "Electrical and Electronics Engineering"),
    ("MEC", "Mechanical Engineering"),
    ("CIV", "Civil Engineering"),
]

SKILLS = [
    ("Python", "Programming"), ("Java", "Programming"), ("C++", "Programming"),
    ("JavaScript", "Programming"), ("TypeScript", "Programming"),
    ("MySQL", "Database"), ("PostgreSQL", "Database"), ("MongoDB", "Database"),
    ("React", "Web"), ("Node.js", "Web"), ("FastAPI", "Web"), ("HTML and CSS", "Web"),
    ("Git", "Tools"), ("Docker", "Tools"), ("Linux", "Tools"), ("Excel", "Tools"),
    ("Communication", "Soft Skill"), ("Teamwork", "Soft Skill"),
    ("Problem Solving", "Soft Skill"), ("AutoCAD", "Other"),
]

COMPANIES = [
    ("Northwind Technologies", "Information Technology", "hr@northwind-tech.example", "Priya Menon", "Bengaluru"),
    ("Blue Harbour Systems", "Software Products", "careers@blueharbour.example", "Arjun Rao", "Hyderabad"),
    ("Vertex Analytics", "Data and Analytics", "talent@vertex-analytics.example", "Sneha Iyer", "Pune"),
    ("Ironvale Motors", "Automotive", "recruit@ironvale.example", "Rahul Desai", "Chennai"),
    ("Clearwater Infra", "Construction", "jobs@clearwater-infra.example", "Meera Nair", "Kochi"),
    ("Helios Power Grid", "Energy", "hiring@helios-grid.example", "Vikram Shetty", "Mumbai"),
    ("Quanta Semiconductors", "Semiconductors", "hr@quanta-semi.example", "Divya Krishnan", "Bengaluru"),
    ("Meridian Consulting", "Consulting", "campus@meridian-consult.example", "Anand Pillai", "Gurugram"),
    ("Saffron Fintech", "Financial Services", "people@saffron-fintech.example", "Kavya Reddy", "Mumbai"),
    ("Lighthouse Cloud", "Cloud Services", "jobs@lighthouse-cloud.example", "Nikhil Verma", "Noida"),
]

FIRST_NAMES = [
    "Aarav", "Ananya", "Aditya", "Bhavana", "Chetan", "Deepika", "Dhruv", "Esha",
    "Farhan", "Gayatri", "Harsh", "Ishita", "Jayant", "Kiran", "Lakshmi", "Manav",
    "Nandini", "Omkar", "Pooja", "Rohit", "Sanjana", "Tarun", "Uma", "Varun",
    "Yashica", "Zoya", "Advait", "Charu", "Girish", "Hema", "Imran", "Jyoti",
    "Kabir", "Lalita", "Mohit", "Neha", "Parth", "Ritika", "Suresh", "Trisha",
]
LAST_NAMES = [
    "Sharma", "Nair", "Reddy", "Iyer", "Patel", "Bose", "Menon", "Kulkarni",
    "Joshi", "Chauhan", "Pillai", "Mehta", "Rao", "Gupta", "Shetty", "Das",
]

# Fictional registration numbers. The reset step matches exactly this set.
REG_PREFIX = {2026: "26BCD", 2027: "27BCD"}

STUDENT_COUNT = 40


def upsert(
    conn: Connection,
    table_name: str,
    keys: dict[str, Any],
    values: dict[str, Any] | None = None,
    pk: str | None = None,
) -> Any:
    """Insert the row, or update it if the natural key already exists."""
    table = t(table_name)
    values = values or {}
    where = and_(*[table.c[k] == v for k, v in keys.items()])
    existing = conn.execute(
        select(table.c[pk] if pk else func.count()).where(where)
    ).first()

    if pk:
        if existing is not None:
            if values:
                conn.execute(table.update().where(where).values(**values))
            return existing[0]
        result = conn.execute(table.insert().values(**keys, **values))
        return result.inserted_primary_key[0]

    if existing and int(existing[0]):
        if values:
            conn.execute(table.update().where(where).values(**values))
    else:
        conn.execute(table.insert().values(**keys, **values))
    return None


def seed(conn: Connection) -> dict[str, int]:
    counts: dict[str, int] = {}

    # --- level 0 ---------------------------------------------------------
    dept_id = {
        code: upsert(conn, "department", {"dept_code": code}, {"dept_name": name}, pk="dept_id")
        for code, name in DEPARTMENTS
    }
    counts["department"] = len(dept_id)

    skill_id = {
        name: upsert(conn, "skill", {"skill_name": name}, {"skill_category": cat}, pk="skill_id")
        for name, cat in SKILLS
    }
    counts["skill"] = len(skill_id)

    company_id = {}
    for name, industry, hr_email, hr_name, city in COMPANIES:
        company_id[name] = upsert(
            conn,
            "company",
            {"company_name": name},
            {
                "industry": industry,
                "hr_email": hr_email,
                "hr_name": hr_name,
                "city": city,
                "website": "https://www." + name.lower().replace(" ", "") + ".example",
                "hr_phone": f"+91 90{RNG.randint(10000000, 99999999)}"[:15],
            },
            pk="company_id",
        )
    counts["company"] = len(company_id)

    # --- students --------------------------------------------------------
    dept_codes = [c for c, _ in DEPARTMENTS]
    students: list[dict[str, Any]] = []
    for i in range(STUDENT_COUNT):
        batch = 2026 if i % 3 else 2027
        code = dept_codes[i % len(dept_codes)]
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 7) % len(LAST_NAMES)]
        reg = f"{REG_PREFIX[batch]}{i + 1:04d}"
        cgpa = Decimal(str(round(RNG.uniform(5.4, 9.7), 2)))
        backlogs = RNG.choice([0, 0, 0, 0, 1, 1, 2, 3])
        row = {
            "reg_no": reg,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}{i + 1}@campus.example",
            "phone": f"9{RNG.randint(100000000, 999999999)}",
            "dob": date(batch - 22, RNG.randint(1, 12), RNG.randint(1, 28)),
            "gender": RNG.choice(["Male", "Female", "Other"]),
            "dept_id": dept_id[code],
            "batch_year": batch,
            "cgpa": cgpa,
            "active_backlogs": backlogs,
            "tenth_pct": Decimal(str(round(RNG.uniform(68, 97), 2))),
            "twelfth_pct": Decimal(str(round(RNG.uniform(65, 96), 2))),
            "resume_link": f"https://campus.example/resumes/{reg}.pdf",
        }
        row["student_id"] = upsert(
            conn, "student", {"reg_no": reg},
            {k: v for k, v in row.items() if k != "reg_no"}, pk="student_id",
        )
        row["dept_code"] = code
        students.append(row)
    counts["student"] = len(students)

    # --- student skills --------------------------------------------------
    skill_names = list(skill_id)
    ss_rows = 0
    for st in students:
        picked = RNG.sample(skill_names, RNG.randint(3, 7))
        for name in picked:
            upsert(
                conn, "student_skill",
                {"student_id": st["student_id"], "skill_id": skill_id[name]},
                {"proficiency_level": RNG.choice(["Beginner", "Intermediate", "Advanced"])},
            )
            ss_rows += 1
    counts["student_skill"] = ss_rows

    # --- job drives ------------------------------------------------------
    # (company, title, type, ctc, openings, deadline offset, drive offset,
    #  status, batch, min_cgpa, max_backlogs, depts, skills, allow_placed)
    drive_specs = [
        ("Northwind Technologies", "Software Engineer", "Full Time", "12.50", 8, 20, 35, "Open", 2026, "7.50", 0,
         ["CSE", "IT"], [("Python", 1, "Intermediate"), ("MySQL", 1, "Beginner"), ("Git", 0, "Beginner")], False),
        ("Blue Harbour Systems", "Backend Developer", "Full Time", "10.00", 6, 14, 28, "Open", 2026, "7.00", 1,
         ["CSE", "IT", "ECE"], [("Java", 1, "Intermediate"), ("PostgreSQL", 0, "Beginner")], False),
        ("Vertex Analytics", "Data Analyst Intern", "Internship", "6.00", 10, 25, 40, "Open", 2027, "6.50", 2,
         ["CSE", "IT", "ECE", "EEE"], [("Python", 1, "Beginner"), ("Excel", 1, "Intermediate")], True),
        ("Lighthouse Cloud", "Cloud Engineer", "Intern + FTE", "14.00", 4, 10, 24, "Open", 2026, "8.00", 0,
         ["CSE", "IT"], [("Docker", 1, "Intermediate"), ("Linux", 1, "Intermediate"), ("Python", 0, "Beginner")], False),
        ("Saffron Fintech", "Full Stack Developer", "Full Time", "11.00", 5, 18, 30, "Open", 2026, "7.20", 0,
         ["CSE", "IT"], [("React", 1, "Intermediate"), ("Node.js", 1, "Beginner"), ("TypeScript", 0, "Beginner")], False),
        # No eligibility_criteria row: shows the optional 1:1 and policy P1.
        ("Meridian Consulting", "Business Analyst", "Full Time", "9.50", 6, 22, 38, "Open", None, None, None,
         ["CSE", "IT", "ECE", "EEE", "MEC", "CIV"],
         [("Communication", 1, "Intermediate"), ("Excel", 0, "Beginner")], None),
        # No eligible departments: shows policy P2 (open to every department).
        ("Quanta Semiconductors", "VLSI Design Engineer", "Full Time", "13.00", 3, 16, 32, "Open", 2026, "7.80", 0,
         [], [("C++", 1, "Intermediate"), ("Problem Solving", 0, "Intermediate")], False),
        ("Ironvale Motors", "Graduate Engineer Trainee", "Full Time", "7.50", 12, -140, -120, "Completed", 2026, "6.00", 2,
         ["MEC", "EEE", "ECE"], [("AutoCAD", 1, "Beginner"), ("Teamwork", 0, "Beginner")], False),
        ("Clearwater Infra", "Site Engineer", "Full Time", "6.50", 8, -130, -110, "Completed", 2026, "6.00", 3,
         ["CIV", "MEC"], [("AutoCAD", 1, "Intermediate")], False),
        ("Helios Power Grid", "Electrical Engineer", "Full Time", "8.00", 5, -120, -100, "Completed", 2026, "6.50", 1,
         ["EEE", "ECE"], [("Problem Solving", 1, "Beginner")], False),
        ("Northwind Technologies", "QA Engineer", "Full Time", "8.50", 4, -12, -2, "Closed", 2026, "6.80", 1,
         ["CSE", "IT"], [("Python", 0, "Beginner"), ("Communication", 1, "Intermediate")], False),
        ("Blue Harbour Systems", "Mobile Developer", "Full Time", "10.50", 3, 45, 60, "Upcoming", 2027, "7.50", 0,
         ["CSE", "IT"], [("JavaScript", 1, "Intermediate")], False),
        ("Vertex Analytics", "Research Intern", "Internship", "5.00", 6, 30, 50, "Upcoming", 2027, "8.20", 0,
         ["CSE", "ECE"], [("Python", 1, "Advanced")], False),
        ("Meridian Consulting", "Operations Associate", "Full Time", "7.00", 5, -5, 5, "Cancelled", 2026, "6.00", 2,
         ["MEC", "CIV"], [("Communication", 1, "Beginner")], False),
    ]

    drives: list[dict[str, Any]] = []
    criteria_rows = ded_rows = drs_rows = 0
    for spec in drive_specs:
        (cname, title, jtype, ctc, openings, dl_off, dd_off, dstatus,
         batch, min_cgpa, max_back, depts, skills, allow_placed) = spec
        deadline = TODAY + timedelta(days=dl_off)
        drive_date = TODAY + timedelta(days=dd_off)
        drive_id = upsert(
            conn, "job_drive",
            {"company_id": company_id[cname], "job_title": title, "drive_date": drive_date},
            {
                "job_type": jtype,
                "job_description": f"{title} role at {cname}. Campus hiring for the {ACADEMIC_YEAR} placement season.",
                "ctc_lpa": Decimal(ctc),
                "job_location": dict((c[0], c[4]) for c in COMPANIES)[cname],
                "num_openings": openings,
                "apply_deadline": deadline,
                "drive_status": dstatus,
            },
            pk="drive_id",
        )
        if batch is not None:
            upsert(
                conn, "eligibility_criteria", {"drive_id": drive_id},
                {
                    "min_cgpa": Decimal(min_cgpa),
                    "max_backlogs": max_back,
                    "min_tenth_pct": Decimal("60.00"),
                    "min_twelfth_pct": Decimal("60.00"),
                    "eligible_batch_year": batch,
                    "allow_placed_students": bool(allow_placed),
                },
            )
            criteria_rows += 1
        for code in depts:
            upsert(conn, "drive_eligible_department",
                   {"drive_id": drive_id, "dept_id": dept_id[code]})
            ded_rows += 1
        for sname, mandatory, prof in skills:
            upsert(conn, "drive_required_skill",
                   {"drive_id": drive_id, "skill_id": skill_id[sname]},
                   {"is_mandatory": bool(mandatory), "min_proficiency": prof})
            drs_rows += 1
        drives.append({
            "drive_id": drive_id, "company": cname, "title": title,
            "deadline": deadline, "drive_date": drive_date, "status": dstatus,
            "batch": batch, "min_cgpa": min_cgpa, "max_backlogs": max_back,
            "depts": depts, "ctc": Decimal(ctc),
        })
    counts["job_drive"] = len(drives)
    counts["eligibility_criteria"] = criteria_rows
    counts["drive_eligible_department"] = ded_rows
    counts["drive_required_skill"] = drs_rows

    # --- applications ----------------------------------------------------
    def qualifies(st: dict[str, Any], dr: dict[str, Any]) -> bool:
        """Mirrors the API's eligibility rules, so seeded data stays valid."""
        if dr["depts"] and st["dept_code"] not in dr["depts"]:
            return False
        if dr["batch"] is None:
            return True
        return (
            st["batch_year"] == dr["batch"]
            and st["cgpa"] >= Decimal(dr["min_cgpa"])
            and st["active_backlogs"] <= dr["max_backlogs"]
            and st["tenth_pct"] >= Decimal("60.00")
            and st["twelfth_pct"] >= Decimal("60.00")
        )

    applications: list[dict[str, Any]] = []
    for dr in drives:
        if dr["status"] == "Cancelled":
            continue
        pool = [s for s in students if qualifies(s, dr)]
        RNG.shuffle(pool)
        take = min(len(pool), RNG.randint(5, 11))
        for st in pool[:take]:
            # applied_on must never be after the deadline (rule T2).
            latest = min(dr["deadline"], TODAY)
            applied_on = datetime.combine(
                latest - timedelta(days=RNG.randint(1, 12)),
                datetime.min.time(),
            ).replace(hour=RNG.randint(9, 18), minute=RNG.choice([0, 15, 30, 45]))
            app_id = upsert(
                conn, "application",
                {"student_id": st["student_id"], "drive_id": dr["drive_id"]},
                {"applied_on": applied_on, "application_status": "Applied"},
                pk="application_id",
            )
            applications.append({
                "application_id": app_id, "student": st, "drive": dr,
                "applied_on": applied_on,
            })
    counts["application"] = len(applications)

    # --- interviews, offers, placements ---------------------------------
    OFFER_STATUS_CYCLE = [
        "Accepted", "Accepted", "Offered", "Accepted", "Declined",
        "Accepted", "Expired", "Accepted", "Revoked", "Accepted", "Offered",
    ]
    ROUNDS = [
        ("Aptitude Test", "Online", None),
        ("Technical Test", "Online", None),
        ("Technical Interview", "Offline", "Placement Cell Room 204"),
        ("HR Interview", "Offline", "Placement Cell Room 101"),
    ]
    iv_rows = 0
    offers: list[dict[str, Any]] = []
    placed_students: set[int] = set()

    for appn in applications:
        dr = appn["drive"]
        if dr["status"] not in ("Open", "Closed", "Completed"):
            continue
        # Past drives run the full pipeline; open ones only part of it.
        max_round = 4 if dr["status"] in ("Completed", "Closed") else RNG.choice([0, 1, 2, 3])
        if not max_round:
            continue
        status_now = "Under Review"
        passed_all = True
        for rnd in range(1, max_round + 1):
            rtype, mode, venue = ROUNDS[rnd - 1]
            sched = appn["applied_on"] + timedelta(days=3 * rnd, hours=RNG.randint(0, 6))
            if not passed_all:
                result, score = "Fail", None
            elif sched.date() > TODAY:
                result, score = "Pending", None
            else:
                result = RNG.choices(["Pass", "Fail", "Absent"], [80, 15, 5])[0]
                score = Decimal(str(RNG.randint(40, 98))) if result != "Absent" else Decimal("0.00")
            upsert(
                conn, "interview",
                {"application_id": appn["application_id"], "round_no": rnd},
                {
                    "round_type": rtype, "mode": mode, "scheduled_at": sched,
                    "venue": venue,
                    "interviewer_name": RNG.choice(
                        ["R. Subramanian", "A. Dsouza", "T. Banerjee", "S. Ghosh", "L. Varma"]
                    ),
                    "score": score,
                    "max_score": Decimal("100.00") if score is not None else None,
                    "result": result,
                    "feedback": {"Pass": "Cleared the round.", "Fail": "Did not meet the bar.",
                                 "Absent": "Candidate did not attend.",
                                 "Pending": None}[result],
                },
            )
            iv_rows += 1
            if result != "Pass":
                passed_all = False
                status_now = "Rejected" if result != "Pending" else "Under Review"
            elif rnd >= 3:
                status_now = "Shortlisted"

        if passed_all and max_round == 4:
            # Cleared every round: issue exactly one offer for this application.
            offer_date = (appn["applied_on"] + timedelta(days=15)).date()
            joining = offer_date + timedelta(days=RNG.randint(15, 75))
            already_placed = appn["student"]["student_id"] in placed_students
            # Deterministic cycle, so every offer status appears in the demo
            # data instead of depending on how the dice fall.
            ostatus = (
                "Declined" if already_placed
                else OFFER_STATUS_CYCLE[len(offers) % len(OFFER_STATUS_CYCLE)]
            )
            offer_id = upsert(
                conn, "offer",
                {"application_id": appn["application_id"]},
                {
                    "offer_date": offer_date,
                    "role_title": dr["title"],
                    "offered_ctc_lpa": dr["ctc"] + Decimal(str(RNG.choice([0, 0, 0.5, 1.0]))),
                    "job_location": dict((c[0], c[4]) for c in COMPANIES)[dr["company"]],
                    "expected_joining_date": joining,
                    "offer_status": ostatus,
                },
                pk="offer_id",
            )
            status_now = "Selected"
            offers.append({
                "offer_id": offer_id, "status": ostatus, "joining": joining,
                "student_id": appn["student"]["student_id"],
            })
            if ostatus == "Accepted":
                placed_students.add(appn["student"]["student_id"])

        a = t("application")
        conn.execute(
            a.update()
            .where(a.c.application_id == appn["application_id"])
            .values(application_status=status_now)
        )

    counts["interview"] = iv_rows
    counts["offer"] = len(offers)

    # Verified placements: only for Accepted offers whose joining date has passed.
    pr_rows = 0
    for off in offers:
        if off["status"] != "Accepted" or off["joining"] > TODAY:
            continue
        upsert(
            conn, "placement_record", {"offer_id": off["offer_id"]},
            {
                "actual_joining_date": off["joining"],
                "company_employee_code": f"EMP{off['offer_id']:05d}",
                "academic_year": ACADEMIC_YEAR,
                "verified_by": "Placement Cell",
                "verified_on": min(off["joining"] + timedelta(days=5), TODAY),
                "remarks": "Joining confirmed by the company HR.",
            },
        )
        pr_rows += 1
    counts["placement_record"] = pr_rows
    return counts


# --- reset ---------------------------------------------------------------

def reset(conn: Connection) -> dict[str, int]:
    """Delete only the demo rows named in this file, children first."""
    removed: dict[str, int] = {}
    reg_nos = [
        f"{REG_PREFIX[2026 if i % 3 else 2027]}{i + 1:04d}" for i in range(STUDENT_COUNT)
    ]
    s, c, d, sk = t("student"), t("company"), t("department"), t("skill")
    demo_students = [
        int(r[0]) for r in conn.execute(select(s.c.student_id).where(s.c.reg_no.in_(reg_nos)))
    ]
    demo_companies = [
        int(r[0]) for r in conn.execute(
            select(c.c.company_id).where(c.c.company_name.in_([x[0] for x in COMPANIES]))
        )
    ]

    jd, a, iv, o, pr = t("job_drive"), t("application"), t("interview"), t("offer"), t("placement_record")
    demo_drives = [
        int(r[0]) for r in conn.execute(select(jd.c.drive_id).where(jd.c.company_id.in_(demo_companies or [0])))
    ]
    demo_apps = [
        int(r[0]) for r in conn.execute(
            select(a.c.application_id).where(
                a.c.student_id.in_(demo_students or [0]) | a.c.drive_id.in_(demo_drives or [0])
            )
        )
    ]
    demo_offers = [
        int(r[0]) for r in conn.execute(select(o.c.offer_id).where(o.c.application_id.in_(demo_apps or [0])))
    ]

    def wipe(table: Any, clause: Any, label: str) -> None:
        removed[label] = int(conn.execute(table.delete().where(clause)).rowcount)

    wipe(pr, pr.c.offer_id.in_(demo_offers or [0]), "placement_record")
    wipe(o, o.c.offer_id.in_(demo_offers or [0]), "offer")
    wipe(iv, iv.c.application_id.in_(demo_apps or [0]), "interview")
    wipe(a, a.c.application_id.in_(demo_apps or [0]), "application")
    wipe(t("drive_required_skill"), t("drive_required_skill").c.drive_id.in_(demo_drives or [0]), "drive_required_skill")
    wipe(t("drive_eligible_department"), t("drive_eligible_department").c.drive_id.in_(demo_drives or [0]), "drive_eligible_department")
    wipe(t("eligibility_criteria"), t("eligibility_criteria").c.drive_id.in_(demo_drives or [0]), "eligibility_criteria")
    wipe(t("student_skill"), t("student_skill").c.student_id.in_(demo_students or [0]), "student_skill")
    wipe(jd, jd.c.drive_id.in_(demo_drives or [0]), "job_drive")
    wipe(s, s.c.student_id.in_(demo_students or [0]), "student")
    wipe(c, c.c.company_id.in_(demo_companies or [0]), "company")
    wipe(sk, sk.c.skill_name.in_([n for n, _ in SKILLS]), "skill")
    wipe(d, d.c.dept_code.in_([code for code, _ in DEPARTMENTS]), "department")
    return removed


def summary(conn: Connection) -> dict[str, int]:
    names = [
        "department", "skill", "company", "student", "student_skill", "job_drive",
        "eligibility_criteria", "drive_eligible_department", "drive_required_skill",
        "application", "interview", "offer", "placement_record",
    ]
    return {
        n: int(conn.execute(select(func.count()).select_from(t(n))).scalar_one()) for n in names
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="delete only the demo rows")
    parser.add_argument("--summary", action="store_true", help="print row counts and exit")
    args = parser.parse_args()

    with engine.connect() as conn:
        if args.summary:
            for name, n in summary(conn).items():
                print(f"{name:28} {n:>6}")
            return 0
        with conn.begin():
            result = reset(conn) if args.reset else seed(conn)
        label = "deleted" if args.reset else "seeded"
        print(f"--- {label} ---")
        for name, n in result.items():
            print(f"{name:28} {n:>6}")
        print("--- current row counts ---")
        for name, n in summary(conn).items():
            print(f"{name:28} {n:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
