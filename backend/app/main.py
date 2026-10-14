"""Smart Campus Placement Management System — Phase 2 API.

Phase 1 built and locked the 13 table MySQL schema. This API reads and writes
that same schema. It reflects the live tables rather than re-declaring them, so
it cannot drift from the DDL in ``database/``.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import errors
from .config import settings
from .routers import drives, meta, reports, students, workflow

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

DESCRIPTION = """
REST API over the Phase 1 `smart_campus_placement` MySQL schema.

**Business rules** that a MySQL `CHECK` cannot express (they read other tables)
are enforced in the service layer, so a direct API client cannot bypass them.
See `database/README.md` for the Phase 1 three tier constraint strategy.

**Documented policies**

* A drive with no `eligibility_criteria` row has *no academic gate*. The API
  reports `criteria_defined: false`; it never treats missing criteria as
  zero cut-offs.
* A drive with no `drive_eligible_department` rows is open to all departments.
* "Already placed" means an `Accepted` offer or a verified `placement_record`.
* Applications are only accepted while `drive_status = 'Open'`.
* `drive_status` moves forward only. See `GET /drive-status-transitions`.
"""

app = FastAPI(
    title=settings.api_title,
    description=DESCRIPTION,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.register(app)

API = "/api"
app.include_router(meta.router, prefix=API)
app.include_router(students.router, prefix=API)
app.include_router(students.skills_router, prefix=API)
app.include_router(drives.companies_router, prefix=API)
app.include_router(drives.drives_router, prefix=API)
app.include_router(workflow.applications_router, prefix=API)
app.include_router(workflow.interviews_router, prefix=API)
app.include_router(workflow.offers_router, prefix=API)
app.include_router(workflow.placements_router, prefix=API)
app.include_router(reports.router, prefix=API)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": settings.api_title,
        "version": "2.0.0",
        "docs": "/docs",
        "health": f"{API}/health",
    }
