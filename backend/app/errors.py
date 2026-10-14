"""Translate database and rule failures into clean HTTP responses.

No exception trace, SQL statement or connection string ever reaches a client.
The full detail is logged server side instead.

MySQL reports the same error number through different SQLAlchemy exception
classes depending on when it is raised, so the error number is mapped in one
place and both handlers use that mapping.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from .rules import NotFound, RuleViolation

log = logging.getLogger("campus.api")

CONFLICT = status.HTTP_409_CONFLICT
UNPROCESSABLE = 422  # literal: the Starlette constant name differs across versions

# MySQL error number -> (HTTP status, message). `{name}` is filled in with the
# violated constraint when the driver message names one.
ERROR_MAP: dict[int, tuple[int, str]] = {
    1062: (CONFLICT, "A record with these unique values already exists.{name}"),
    1452: (CONFLICT, "A referenced record does not exist.{name}"),
    1451: (CONFLICT, "This record is still referenced by other records.{name}"),
    3819: (UNPROCESSABLE, "The value breaks a database CHECK constraint.{name}"),
    1048: (UNPROCESSABLE, "A required field was left empty."),
    1264: (UNPROCESSABLE, "A value is outside the range the column allows."),
    1265: (UNPROCESSABLE, "A value is not one of the values this column allows."),
    1406: (UNPROCESSABLE, "A value is too long for its column."),
}


def _mysql_errno(exc: SQLAlchemyError) -> int | None:
    args = getattr(getattr(exc, "orig", None), "args", None)
    return args[0] if args and isinstance(args[0], int) else None


def _constraint_name(exc: SQLAlchemyError) -> str | None:
    args = getattr(getattr(exc, "orig", None), "args", None)
    if not args or len(args) < 2 or not isinstance(args[1], str):
        return None
    text = args[1]
    for marker in ("key '", "constraint '", "CONSTRAINT `"):
        if marker in text:
            return text.split(marker, 1)[1].split("'")[0].split("`")[0]
    return None


def _mapped_response(exc: SQLAlchemyError) -> JSONResponse | None:
    errno = _mysql_errno(exc)
    if errno not in ERROR_MAP:
        return None
    code, template = ERROR_MAP[errno]
    name = _constraint_name(exc)
    detail = template.format(name=f" Violated constraint: {name}." if name else "")
    return JSONResponse(status_code=code, content={"detail": detail})


def register(app: FastAPI) -> None:
    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
        )

    @app.exception_handler(RuleViolation)
    async def _rule(_: Request, exc: RuleViolation) -> JSONResponse:
        return JSONResponse(
            status_code=CONFLICT,
            content={"detail": exc.message, "reasons": exc.reasons},
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        log.warning(
            "integrity error %s on %s: %s", _mysql_errno(exc), request.url.path, exc.orig
        )
        return _mapped_response(exc) or JSONResponse(
            status_code=CONFLICT,
            content={"detail": "The request breaks a database integrity rule."},
        )

    @app.exception_handler(OperationalError)
    async def _operational(request: Request, exc: OperationalError) -> JSONResponse:
        errno = _mysql_errno(exc)
        mapped = _mapped_response(exc)
        if mapped is not None:
            # A rejected value, not an unreachable server.
            log.warning("rejected value %s on %s: %s", errno, request.url.path, exc.orig)
            return mapped
        log.error("operational error %s on %s: %s", errno, request.url.path, exc.orig)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "The database is not available. Try again shortly."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        mapped = _mapped_response(exc)
        if mapped is not None:
            return mapped
        log.exception("database error on %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred."},
        )
