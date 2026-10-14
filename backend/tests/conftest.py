"""Test fixtures.

These are real integration tests against the real MySQL database, because the
point of Phase 2 is that the application works against the Phase 1 schema.

Isolation, without a throwaway database: each test runs inside one transaction
that is **rolled back** afterwards. The FastAPI ``get_conn`` dependency is
overridden to hand the route that same connection, so every write the test
makes disappears at the end. Nothing is dropped, nothing is truncated and no
foreign key check is ever disabled.
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, func, select

from app.db import engine, get_conn, t
from app.main import app

API = "/api"

_counter = itertools.count(1)


def uniq(prefix: str) -> str:
    return f"{prefix}{next(_counter):04d}"


@pytest.fixture(scope="session")
def db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
        return True
    except Exception as exc:  # pragma: no cover - reported, not hidden
        pytest.fail(f"MySQL is not reachable, integration tests cannot run: {exc}")


@pytest.fixture
def conn(db_available: bool) -> Connection:
    connection = engine.connect()
    trans = connection.begin()
    try:
        yield connection
    finally:
        trans.rollback()
        connection.close()


@pytest.fixture
def client(conn: Connection) -> TestClient:
    def _override():
        yield conn

    app.dependency_overrides[get_conn] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- scenario builders ---------------------------------------------------


@pytest.fixture
def make(conn: Connection) -> Any:
    """Build throwaway rows directly, so a test states only what it needs."""

    class Factory:
        def department(self) -> int:
            code = uniq("TD")[:10]
            return int(
                conn.execute(
                    t("department").insert().values(
                        dept_code=code, dept_name=f"Test Department {code}"
                    )
                ).inserted_primary_key[0]
            )

        def company(self) -> int:
            name = uniq("Test Company ")
            return int(
                conn.execute(
                    t("company").insert().values(
                        company_name=name,
                        hr_name="Test HR",
                        hr_email=f"{name.replace(' ', '').lower()}@test.example",
                    )
                ).inserted_primary_key[0]
            )

        def student(
            self,
            dept_id: int,
            *,
            cgpa: str = "9.00",
            backlogs: int = 0,
            batch_year: int = 2026,
            tenth: str = "90.00",
            twelfth: str = "90.00",
        ) -> int:
            reg = uniq("TSTU")
            return int(
                conn.execute(
                    t("student").insert().values(
                        reg_no=reg,
                        first_name="Test",
                        last_name=reg,
                        email=f"{reg.lower()}@test.example",
                        dept_id=dept_id,
                        batch_year=batch_year,
                        cgpa=Decimal(cgpa),
                        active_backlogs=backlogs,
                        tenth_pct=Decimal(tenth),
                        twelfth_pct=Decimal(twelfth),
                    )
                ).inserted_primary_key[0]
            )

        def drive(
            self,
            company_id: int,
            *,
            status: str = "Open",
            deadline_offset: int = 10,
            drive_offset: int = 20,
            ctc: str = "10.00",
        ) -> int:
            today = date.today()
            return int(
                conn.execute(
                    t("job_drive").insert().values(
                        company_id=company_id,
                        job_title=uniq("Test Role "),
                        ctc_lpa=Decimal(ctc),
                        apply_deadline=today + timedelta(days=deadline_offset),
                        drive_date=today + timedelta(days=drive_offset),
                        drive_status=status,
                    )
                ).inserted_primary_key[0]
            )

        def criteria(
            self,
            drive_id: int,
            *,
            min_cgpa: str = "6.00",
            max_backlogs: int = 2,
            batch_year: int = 2026,
            allow_placed: bool = False,
        ) -> None:
            conn.execute(
                t("eligibility_criteria").insert().values(
                    drive_id=drive_id,
                    min_cgpa=Decimal(min_cgpa),
                    max_backlogs=max_backlogs,
                    min_tenth_pct=Decimal("60.00"),
                    min_twelfth_pct=Decimal("60.00"),
                    eligible_batch_year=batch_year,
                    allow_placed_students=allow_placed,
                )
            )

        def eligible_dept(self, drive_id: int, dept_id: int) -> None:
            conn.execute(
                t("drive_eligible_department").insert().values(
                    drive_id=drive_id, dept_id=dept_id
                )
            )

        def application(
            self, student_id: int, drive_id: int, *, applied_on: datetime | None = None
        ) -> int:
            values: dict[str, Any] = {"student_id": student_id, "drive_id": drive_id}
            if applied_on is not None:
                values["applied_on"] = applied_on
            return int(
                conn.execute(t("application").insert().values(**values)).inserted_primary_key[0]
            )

        def offer(self, application_id: int, *, status: str = "Offered") -> int:
            return int(
                conn.execute(
                    t("offer").insert().values(
                        application_id=application_id,
                        offer_date=date.today(),
                        role_title="Test Role",
                        offered_ctc_lpa=Decimal("10.00"),
                        offer_status=status,
                    )
                ).inserted_primary_key[0]
            )

        def placement(self, offer_id: int) -> int:
            return int(
                conn.execute(
                    t("placement_record").insert().values(
                        offer_id=offer_id,
                        academic_year="2026-2027",
                        verified_by="Test Verifier",
                    )
                ).inserted_primary_key[0]
            )

        def skill(self) -> int:
            return int(
                conn.execute(
                    t("skill").insert().values(
                        skill_name=uniq("TestSkill"), skill_category="Programming"
                    )
                ).inserted_primary_key[0]
            )

        def open_drive_for(self, **student_kwargs: Any) -> tuple[int, int]:
            """A department-restricted open drive plus one eligible student."""
            dept = self.department()
            company = self.company()
            drive = self.drive(company)
            self.criteria(drive)
            self.eligible_dept(drive, dept)
            student = self.student(dept, **student_kwargs)
            return student, drive

        def count(self, table: str) -> int:
            return int(
                conn.execute(select(func.count()).select_from(t(table))).scalar_one()
            )

    return Factory()
