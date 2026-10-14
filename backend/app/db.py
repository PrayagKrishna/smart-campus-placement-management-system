"""Database access.

The Phase 1 schema is locked and authoritative, so this layer *reflects* the
live tables instead of re-declaring them. Nothing here can rename a column,
drop a constraint or drift from the DDL in ``database/``.
"""

from collections.abc import Iterator
from typing import Any

from sqlalchemy import Connection, MetaData, Table, create_engine, func, select
from sqlalchemy.engine import Engine

from .config import settings

EXPECTED_TABLES = frozenset(
    {
        "application",
        "company",
        "department",
        "drive_eligible_department",
        "drive_required_skill",
        "eligibility_criteria",
        "interview",
        "job_drive",
        "offer",
        "placement_record",
        "skill",
        "student",
        "student_skill",
    }
)

engine: Engine = create_engine(
    settings.database_url,
    connect_args=settings.connect_args,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

_metadata: MetaData | None = None


def metadata() -> MetaData:
    """Reflect the schema once, on first use.

    Reflection is lazy so the process still starts (and ``/health`` still
    answers) when MySQL is down.
    """
    global _metadata
    if _metadata is None:
        md = MetaData()
        md.reflect(bind=engine)
        _metadata = md
    return _metadata


def t(name: str) -> Table:
    return metadata().tables[name]


def get_conn() -> Iterator[Connection]:
    """One connection and one transaction per request.

    The route handler runs inside ``conn.begin()``. Any exception rolls the
    whole request back, so multi-write operations are atomic by default.
    """
    with engine.connect() as conn:
        with conn.begin():
            yield conn


# --- small query helpers -------------------------------------------------


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


def rows_to_dicts(rows: Any) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in rows]


def fetch_one(conn: Connection, stmt: Any) -> dict[str, Any] | None:
    row = conn.execute(stmt).first()
    return row_to_dict(row) if row is not None else None


def fetch_all(conn: Connection, stmt: Any) -> list[dict[str, Any]]:
    return rows_to_dicts(conn.execute(stmt).fetchall())


def count_of(conn: Connection, stmt: Any) -> int:
    """Total row count for a SELECT, ignoring its own LIMIT/OFFSET/ORDER BY."""
    base = stmt.order_by(None).limit(None).offset(None)
    return int(conn.execute(select(func.count()).select_from(base.subquery())).scalar_one())


def paginate(
    conn: Connection, stmt: Any, limit: int, offset: int
) -> dict[str, Any]:
    total = count_of(conn, stmt)
    items = fetch_all(conn, stmt.limit(limit).offset(offset))
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def exists(conn: Connection, table_name: str, **where: Any) -> bool:
    table = t(table_name)
    stmt = select(func.count()).select_from(table)
    for col, val in where.items():
        stmt = stmt.where(table.c[col] == val)
    return int(conn.execute(stmt).scalar_one()) > 0


def get_by_pk(
    conn: Connection, table_name: str, pk_col: str, pk_val: Any
) -> dict[str, Any] | None:
    table = t(table_name)
    return fetch_one(conn, select(table).where(table.c[pk_col] == pk_val))


def insert_returning_id(
    conn: Connection, table_name: str, data: dict[str, Any]
) -> int:
    result = conn.execute(t(table_name).insert().values(**data))
    return int(result.inserted_primary_key[0])


def update_by_pk(
    conn: Connection,
    table_name: str,
    pk_col: str,
    pk_val: Any,
    data: dict[str, Any],
) -> int:
    table = t(table_name)
    result = conn.execute(
        table.update().where(table.c[pk_col] == pk_val).values(**data)
    )
    return int(result.rowcount)
