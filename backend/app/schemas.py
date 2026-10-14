"""Request and response models.

Input validation mirrors the Phase 1 CHECK constraints and ENUM domains, so a
bad request is rejected with HTTP 422 before it ever reaches MySQL. The
database remains the final authority: every rule here is also enforced there.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

# --- domains, copied from the locked ENUM / CHECK definitions -------------

Gender = Literal["Male", "Female", "Other"]
JobType = Literal["Internship", "Full Time", "Intern + FTE"]
DriveStatus = Literal["Upcoming", "Open", "Closed", "Completed", "Cancelled"]
ApplicationStatus = Literal[
    "Applied", "Under Review", "Shortlisted", "Rejected", "Selected", "Withdrawn"
]
RoundType = Literal[
    "Aptitude Test",
    "Technical Test",
    "Group Discussion",
    "Technical Interview",
    "HR Interview",
    "Managerial",
]
InterviewMode = Literal["Online", "Offline"]
InterviewResult = Literal["Pending", "Pass", "Fail", "Absent"]
OfferStatus = Literal["Offered", "Accepted", "Declined", "Expired", "Revoked"]
Proficiency = Literal["Beginner", "Intermediate", "Advanced"]
SkillCategory = Literal[
    "Programming", "Database", "Web", "Tools", "Soft Skill", "Other"
]

Cgpa = Annotated[Decimal, Field(ge=0, le=10, max_digits=4, decimal_places=2)]
Pct = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
Ctc = Annotated[Decimal, Field(gt=0, le=9999.99, max_digits=6, decimal_places=2)]
BatchYear = Annotated[int, Field(ge=2000, le=2100)]
AcademicYear = Annotated[
    str, StringConstraints(pattern=r"^[0-9]{4}-[0-9]{4}$")
]

Str20 = Annotated[str, StringConstraints(min_length=1, max_length=20, strip_whitespace=True)]
Str40 = Annotated[str, StringConstraints(min_length=1, max_length=40, strip_whitespace=True)]
Str50 = Annotated[str, StringConstraints(min_length=1, max_length=50, strip_whitespace=True)]
Str60 = Annotated[str, StringConstraints(min_length=1, max_length=60, strip_whitespace=True)]
Str80 = Annotated[str, StringConstraints(min_length=1, max_length=80, strip_whitespace=True)]
Str100 = Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)]
Str120 = Annotated[str, StringConstraints(min_length=1, max_length=120, strip_whitespace=True)]
Str255 = Annotated[str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)]
Phone = Annotated[str, StringConstraints(pattern=r"^[0-9+\- ]{7,15}$")]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(BaseModel):
    """Envelope for every paginated list endpoint."""

    items: list[Any]
    total: int
    limit: int
    offset: int


# --- department -----------------------------------------------------------


class DepartmentOut(BaseModel):
    dept_id: int
    dept_code: str
    dept_name: str


# --- student --------------------------------------------------------------


class StudentCreate(Base):
    reg_no: Str20
    first_name: Str50
    last_name: Str50 | None = None
    email: EmailStr
    phone: Phone | None = None
    dob: date | None = None
    gender: Gender | None = None
    dept_id: int
    batch_year: BatchYear
    cgpa: Cgpa = Decimal("0.00")
    active_backlogs: Annotated[int, Field(ge=0)] = 0
    tenth_pct: Pct | None = None
    twelfth_pct: Pct | None = None
    resume_link: Str255 | None = None


class StudentUpdate(Base):
    first_name: Str50 | None = None
    last_name: Str50 | None = None
    email: EmailStr | None = None
    phone: Phone | None = None
    dob: date | None = None
    gender: Gender | None = None
    dept_id: int | None = None
    batch_year: BatchYear | None = None
    cgpa: Cgpa | None = None
    active_backlogs: Annotated[int, Field(ge=0)] | None = None
    tenth_pct: Pct | None = None
    twelfth_pct: Pct | None = None
    resume_link: Str255 | None = None


class StudentOut(BaseModel):
    student_id: int
    reg_no: str
    first_name: str
    last_name: str | None
    email: str
    phone: str | None
    dob: date | None
    gender: str | None
    dept_id: int
    dept_code: str | None = None
    dept_name: str | None = None
    batch_year: int
    cgpa: Decimal
    active_backlogs: int
    tenth_pct: Decimal | None
    twelfth_pct: Decimal | None
    resume_link: str | None
    created_at: datetime | None = None


# --- company --------------------------------------------------------------


class CompanyCreate(Base):
    company_name: Str120
    industry: Str80 | None = None
    website: Str255 | None = None
    hr_name: Str100
    hr_email: EmailStr
    hr_phone: Phone | None = None
    city: Str80 | None = None


class CompanyUpdate(Base):
    company_name: Str120 | None = None
    industry: Str80 | None = None
    website: Str255 | None = None
    hr_name: Str100 | None = None
    hr_email: EmailStr | None = None
    hr_phone: Phone | None = None
    city: Str80 | None = None


class CompanyOut(BaseModel):
    company_id: int
    company_name: str
    industry: str | None
    website: str | None
    hr_name: str
    hr_email: str
    hr_phone: str | None
    city: str | None
    created_at: datetime | None = None


# --- job drive ------------------------------------------------------------


class EligibilityCriteriaIn(Base):
    min_cgpa: Cgpa = Decimal("0.00")
    max_backlogs: Annotated[int, Field(ge=0)] = 0
    min_tenth_pct: Pct = Decimal("0.00")
    min_twelfth_pct: Pct = Decimal("0.00")
    eligible_batch_year: BatchYear
    allow_placed_students: bool = False


class EligibilityCriteriaOut(BaseModel):
    drive_id: int
    min_cgpa: Decimal
    max_backlogs: int
    min_tenth_pct: Decimal
    min_twelfth_pct: Decimal
    eligible_batch_year: int
    allow_placed_students: bool


class JobDriveCreate(Base):
    company_id: int
    job_title: Str120
    job_type: JobType = "Full Time"
    job_description: str | None = None
    ctc_lpa: Ctc
    job_location: Str80 | None = None
    num_openings: Annotated[int, Field(gt=0)] = 1
    apply_deadline: date
    drive_date: date
    drive_status: DriveStatus = "Upcoming"


class JobDriveUpdate(Base):
    job_title: Str120 | None = None
    job_type: JobType | None = None
    job_description: str | None = None
    ctc_lpa: Ctc | None = None
    job_location: Str80 | None = None
    num_openings: Annotated[int, Field(gt=0)] | None = None
    apply_deadline: date | None = None
    drive_date: date | None = None
    drive_status: DriveStatus | None = None


class JobDriveOut(BaseModel):
    drive_id: int
    company_id: int
    company_name: str | None = None
    job_title: str
    job_type: str
    job_description: str | None = None
    ctc_lpa: Decimal
    job_location: str | None
    num_openings: int
    apply_deadline: date
    drive_date: date
    drive_status: str
    created_at: datetime | None = None


class DriveSkillIn(Base):
    skill_id: int
    is_mandatory: bool = True
    min_proficiency: Proficiency = "Beginner"


# --- skill ----------------------------------------------------------------


class SkillCreate(Base):
    skill_name: Str60
    skill_category: SkillCategory = "Other"


class SkillOut(BaseModel):
    skill_id: int
    skill_name: str
    skill_category: str


class StudentSkillIn(Base):
    skill_id: int
    proficiency_level: Proficiency = "Beginner"


class StudentSkillUpdate(Base):
    proficiency_level: Proficiency


# --- application ----------------------------------------------------------


class ApplicationCreate(Base):
    student_id: int
    drive_id: int
    remarks: Str255 | None = None


class ApplicationStatusUpdate(Base):
    application_status: ApplicationStatus
    remarks: Str255 | None = None


class ApplicationOut(BaseModel):
    application_id: int
    student_id: int
    drive_id: int
    applied_on: datetime
    application_status: str
    remarks: str | None
    reg_no: str | None = None
    student_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None


# --- interview ------------------------------------------------------------


class InterviewCreate(Base):
    application_id: int
    round_no: Annotated[int, Field(gt=0)]
    round_type: RoundType
    mode: InterviewMode = "Offline"
    scheduled_at: datetime
    venue: Str120 | None = None
    interviewer_name: Str100 | None = None
    score: Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)] | None = None
    max_score: Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)] | None = None
    result: InterviewResult = "Pending"
    feedback: Str255 | None = None


class InterviewUpdate(Base):
    round_type: RoundType | None = None
    mode: InterviewMode | None = None
    scheduled_at: datetime | None = None
    venue: Str120 | None = None
    interviewer_name: Str100 | None = None
    score: Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)] | None = None
    max_score: Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)] | None = None
    result: InterviewResult | None = None
    feedback: Str255 | None = None


class InterviewOut(BaseModel):
    interview_id: int
    application_id: int
    round_no: int
    round_type: str
    mode: str
    scheduled_at: datetime
    venue: str | None
    interviewer_name: str | None
    score: Decimal | None
    max_score: Decimal | None
    result: str
    feedback: str | None


# --- offer ----------------------------------------------------------------


class OfferCreate(Base):
    application_id: int
    offer_date: date
    role_title: Str120
    offered_ctc_lpa: Ctc
    job_location: Str80 | None = None
    expected_joining_date: date | None = None
    offer_status: OfferStatus = "Offered"


class OfferUpdate(Base):
    offer_date: date | None = None
    role_title: Str120 | None = None
    offered_ctc_lpa: Ctc | None = None
    job_location: Str80 | None = None
    expected_joining_date: date | None = None
    offer_status: OfferStatus | None = None


class OfferOut(BaseModel):
    offer_id: int
    application_id: int
    offer_date: date
    role_title: str
    offered_ctc_lpa: Decimal
    job_location: str | None
    expected_joining_date: date | None
    offer_status: str
    student_id: int | None = None
    reg_no: str | None = None
    student_name: str | None = None
    company_name: str | None = None


# --- placement record -----------------------------------------------------


class PlacementCreate(Base):
    offer_id: int
    academic_year: AcademicYear
    verified_by: Str100
    actual_joining_date: date | None = None
    company_employee_code: Str40 | None = None
    verified_on: date | None = None
    remarks: Str255 | None = None


class PlacementUpdate(Base):
    actual_joining_date: date | None = None
    company_employee_code: Str40 | None = None
    academic_year: AcademicYear | None = None
    verified_by: Str100 | None = None
    verified_on: date | None = None
    remarks: Str255 | None = None


class PlacementOut(BaseModel):
    placement_id: int
    offer_id: int
    actual_joining_date: date | None
    company_employee_code: str | None
    academic_year: str
    verified_by: str
    verified_on: date
    remarks: str | None
    student_id: int | None = None
    reg_no: str | None = None
    student_name: str | None = None
    company_name: str | None = None
    offered_ctc_lpa: Decimal | None = None


# --- eligibility / health -------------------------------------------------


class EligibilityCheckOut(BaseModel):
    student_id: int
    drive_id: int
    eligible: bool
    criteria_defined: bool
    department_restricted: bool
    reasons: list[str]
    checks: list[dict[str, Any]]


class HealthOut(BaseModel):
    api: Literal["ok"]
    database: Literal["ok", "unavailable"]
    database_name: str | None = None
    mysql_version: str | None = None
    table_count: int | None = None
    detail: str | None = None
