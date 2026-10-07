-- ============================================================================
-- SMART CAMPUS PLACEMENT MANAGEMENT SYSTEM
-- File   : 02_create_tables.sql
--
-- Purpose: Create all 13 base tables.
--          This file carries every constraint that belongs to a table on its
--          own:  PRIMARY KEY, UNIQUE, NOT NULL, DEFAULT, ENUM domains and
--          CHECK constraints.
--          REFERENTIAL integrity (FOREIGN KEY) is applied separately in
--          03_constraints.sql, so table creation order never blocks a rerun.
--
-- Engine : InnoDB   (MyISAM silently ignores FOREIGN KEY - do not change this)
-- Charset: utf8mb4  with collation utf8mb4_0900_ai_ci
-- Target : MySQL 8.0.16+
--
-- Note on constraint names: in MySQL a CHECK constraint name must be unique
-- across the whole database, not just the table. Every CHECK below is
-- therefore prefixed with its table name.
-- ============================================================================

USE smart_campus_placement;

-- ---------------------------------------------------------------------------
-- Drop in reverse dependency order so this script can be rerun safely.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS placement_record;
DROP TABLE IF EXISTS offer;
DROP TABLE IF EXISTS interview;
DROP TABLE IF EXISTS application;
DROP TABLE IF EXISTS drive_required_skill;
DROP TABLE IF EXISTS student_skill;
DROP TABLE IF EXISTS drive_eligible_department;
DROP TABLE IF EXISTS eligibility_criteria;
DROP TABLE IF EXISTS job_drive;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS company;
DROP TABLE IF EXISTS skill;
DROP TABLE IF EXISTS department;


-- ===========================================================================
-- LEVEL 0 : independent master tables
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. department  (strong entity)
--    Branch master. Needed because a drive is open to selected branches only.
--    Candidate keys: {dept_id}, {dept_code}, {dept_name}
-- ---------------------------------------------------------------------------
CREATE TABLE department (
    dept_id    INT          NOT NULL AUTO_INCREMENT,
    dept_code  VARCHAR(10)  NOT NULL,
    dept_name  VARCHAR(100) NOT NULL,

    CONSTRAINT pk_department      PRIMARY KEY (dept_id),
    CONSTRAINT uq_department_code UNIQUE      (dept_code),
    CONSTRAINT uq_department_name UNIQUE      (dept_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 2. skill  (strong entity)
--    Skill master. Referenced by student_skill and drive_required_skill.
--    Candidate keys: {skill_id}, {skill_name}
-- ---------------------------------------------------------------------------
CREATE TABLE skill (
    skill_id       INT         NOT NULL AUTO_INCREMENT,
    skill_name     VARCHAR(60) NOT NULL,
    skill_category ENUM('Programming','Database','Web','Tools','Soft Skill','Other')
                   NOT NULL DEFAULT 'Other',

    CONSTRAINT pk_skill      PRIMARY KEY (skill_id),
    CONSTRAINT uq_skill_name UNIQUE      (skill_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 3. company  (strong entity)
--    Candidate keys: {company_id}, {company_name}, {hr_email}
--    hr_email is NOT NULL + UNIQUE on purpose. That makes it a candidate key,
--    which is why hr_email -> hr_name is a key dependency and NOT a 3NF
--    violation. Assumption: one HR contact represents exactly one company.
-- ---------------------------------------------------------------------------
CREATE TABLE company (
    company_id   INT          NOT NULL AUTO_INCREMENT,
    company_name VARCHAR(120) NOT NULL,
    industry     VARCHAR(80)  NULL,
    website      VARCHAR(255) NULL,
    hr_name      VARCHAR(100) NOT NULL,
    hr_email     VARCHAR(120) NOT NULL,
    hr_phone     VARCHAR(15)  NULL,
    city         VARCHAR(80)  NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_company          PRIMARY KEY (company_id),
    CONSTRAINT uq_company_name     UNIQUE      (company_name),
    CONSTRAINT uq_company_hr_email UNIQUE      (hr_email)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ===========================================================================
-- LEVEL 1 : depend on the masters above
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 4. student  (strong entity)
--    Candidate keys: {student_id}, {reg_no}, {email}
--    phone is UNIQUE but NULLABLE, so it is a uniqueness constraint and NOT a
--    candidate key (a candidate key must be NOT NULL).
--    No is_placed / age column: both are derived and are exposed as views.
-- ---------------------------------------------------------------------------
CREATE TABLE student (
    student_id      INT          NOT NULL AUTO_INCREMENT,
    reg_no          VARCHAR(20)  NOT NULL,
    first_name      VARCHAR(50)  NOT NULL,
    last_name       VARCHAR(50)  NULL,
    email           VARCHAR(120) NOT NULL,
    phone           VARCHAR(15)  NULL,
    dob             DATE         NULL,
    gender          ENUM('Male','Female','Other') NULL,
    dept_id         INT          NOT NULL,
    batch_year      YEAR         NOT NULL,
    cgpa            DECIMAL(4,2) NOT NULL DEFAULT 0.00,
    active_backlogs INT          NOT NULL DEFAULT 0,
    tenth_pct       DECIMAL(5,2) NULL,
    twelfth_pct     DECIMAL(5,2) NULL,
    resume_link     VARCHAR(255) NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_student        PRIMARY KEY (student_id),
    CONSTRAINT uq_student_reg_no UNIQUE      (reg_no),
    CONSTRAINT uq_student_email  UNIQUE      (email),
    CONSTRAINT uq_student_phone  UNIQUE      (phone),

    CONSTRAINT chk_student_cgpa       CHECK (cgpa BETWEEN 0.00 AND 10.00),
    CONSTRAINT chk_student_backlogs   CHECK (active_backlogs >= 0),
    CONSTRAINT chk_student_tenth      CHECK (tenth_pct   IS NULL OR tenth_pct   BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_student_twelfth    CHECK (twelfth_pct IS NULL OR twelfth_pct BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_student_batch_year CHECK (batch_year BETWEEN 2000 AND 2100)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 5. job_drive  (strong entity)
--    Candidate keys: {drive_id}  and  {company_id, job_title, drive_date}
--    The composite alternate key is why 2NF had to be checked by subset
--    testing here instead of claimed automatically.
-- ---------------------------------------------------------------------------
CREATE TABLE job_drive (
    drive_id        INT          NOT NULL AUTO_INCREMENT,
    company_id      INT          NOT NULL,
    job_title       VARCHAR(120) NOT NULL,
    job_type        ENUM('Internship','Full Time','Intern + FTE')
                    NOT NULL DEFAULT 'Full Time',
    job_description TEXT         NULL,
    ctc_lpa         DECIMAL(6,2) NOT NULL,
    job_location    VARCHAR(80)  NULL,
    num_openings    INT          NOT NULL DEFAULT 1,
    apply_deadline  DATE         NOT NULL,
    drive_date      DATE         NOT NULL,
    drive_status    ENUM('Upcoming','Open','Closed','Completed','Cancelled')
                    NOT NULL DEFAULT 'Upcoming',
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_job_drive PRIMARY KEY (drive_id),
    CONSTRAINT uq_job_drive_company_title_date
        UNIQUE (company_id, job_title, drive_date),

    CONSTRAINT chk_job_drive_ctc      CHECK (ctc_lpa > 0),
    CONSTRAINT chk_job_drive_openings CHECK (num_openings > 0),
    CONSTRAINT chk_job_drive_dates    CHECK (apply_deadline <= drive_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ===========================================================================
-- LEVEL 2 : dependents and bridges
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 6. eligibility_criteria  (optional 1:1 dependent entity)
--    PRIMARY KEY is also the FOREIGN KEY. That is what enforces 1:1 in the
--    schema itself. The row is optional, so a drive may have no cut-offs.
--    Assumption A1: one drive targets exactly one eligible batch year.
-- ---------------------------------------------------------------------------
CREATE TABLE eligibility_criteria (
    drive_id              INT          NOT NULL,
    min_cgpa              DECIMAL(4,2) NOT NULL DEFAULT 0.00,
    max_backlogs          INT          NOT NULL DEFAULT 0,
    min_tenth_pct         DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    min_twelfth_pct       DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    eligible_batch_year   YEAR         NOT NULL,
    allow_placed_students BOOLEAN      NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_eligibility_criteria PRIMARY KEY (drive_id),

    CONSTRAINT chk_ec_min_cgpa     CHECK (min_cgpa BETWEEN 0.00 AND 10.00),
    CONSTRAINT chk_ec_max_backlogs CHECK (max_backlogs >= 0),
    CONSTRAINT chk_ec_min_tenth    CHECK (min_tenth_pct   BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_ec_min_twelfth  CHECK (min_twelfth_pct BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_ec_batch_year   CHECK (eligible_batch_year BETWEEN 2000 AND 2100)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 7. drive_eligible_department  (pure bridge)
--    Resolves the M:N  job_drive <-> department.
--    All-key relation: no non-prime attribute exists, so 2NF and 3NF hold
--    vacuously. This table is the 1NF fix for a comma separated branch list.
-- ---------------------------------------------------------------------------
CREATE TABLE drive_eligible_department (
    drive_id INT NOT NULL,
    dept_id  INT NOT NULL,

    CONSTRAINT pk_drive_eligible_department PRIMARY KEY (drive_id, dept_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 8. student_skill  (associative bridge)
--    Resolves the M:N  student <-> skill, and carries proficiency_level.
--    1NF fix for storing skills as 'Java, SQL, Python' in one column.
-- ---------------------------------------------------------------------------
CREATE TABLE student_skill (
    student_id        INT NOT NULL,
    skill_id          INT NOT NULL,
    proficiency_level ENUM('Beginner','Intermediate','Advanced')
                      NOT NULL DEFAULT 'Beginner',

    CONSTRAINT pk_student_skill PRIMARY KEY (student_id, skill_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 9. drive_required_skill  (associative bridge)
--    Resolves the M:N  job_drive <-> skill.
--    Kept separate from drive_eligible_department on purpose: merging the two
--    multivalued facts into one table would create a 4NF violation.
-- ---------------------------------------------------------------------------
CREATE TABLE drive_required_skill (
    drive_id        INT     NOT NULL,
    skill_id        INT     NOT NULL,
    is_mandatory    BOOLEAN NOT NULL DEFAULT TRUE,
    min_proficiency ENUM('Beginner','Intermediate','Advanced')
                    NOT NULL DEFAULT 'Beginner',

    CONSTRAINT pk_drive_required_skill PRIMARY KEY (drive_id, skill_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 10. application  (associative entity)
--     Resolves the M:N  student <-> job_drive.
--     Candidate keys: {application_id}  and  {student_id, drive_id}
--     The UNIQUE on (student_id, drive_id) is the business rule
--     "one student cannot apply twice to the same drive".
--     No ctc column here: that would duplicate job_drive.ctc_lpa.
-- ---------------------------------------------------------------------------
CREATE TABLE application (
    application_id     INT          NOT NULL AUTO_INCREMENT,
    student_id         INT          NOT NULL,
    drive_id           INT          NOT NULL,
    applied_on         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    application_status ENUM('Applied','Under Review','Shortlisted',
                            'Rejected','Selected','Withdrawn')
                       NOT NULL DEFAULT 'Applied',
    remarks            VARCHAR(255) NULL,

    CONSTRAINT pk_application PRIMARY KEY (application_id),
    CONSTRAINT uq_application_student_drive UNIQUE (student_id, drive_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ===========================================================================
-- LEVEL 3 and 4 : results of an application
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 11. interview  (dependent entity)
--     One round of one application. It points at application_id only, never
--     at student_id + drive_id, so an interview without an application is
--     impossible.
--     Candidate keys: {interview_id}  and  {application_id, round_no}
-- ---------------------------------------------------------------------------
CREATE TABLE interview (
    interview_id     INT          NOT NULL AUTO_INCREMENT,
    application_id   INT          NOT NULL,
    round_no         INT          NOT NULL,
    round_type       ENUM('Aptitude Test','Technical Test','Group Discussion',
                          'Technical Interview','HR Interview','Managerial')
                     NOT NULL,
    `mode`           ENUM('Online','Offline') NOT NULL DEFAULT 'Offline',
    scheduled_at     DATETIME     NOT NULL,
    venue            VARCHAR(120) NULL,
    interviewer_name VARCHAR(100) NULL,
    score            DECIMAL(6,2) NULL,
    max_score        DECIMAL(6,2) NULL,
    result           ENUM('Pending','Pass','Fail','Absent')
                     NOT NULL DEFAULT 'Pending',
    feedback         VARCHAR(255) NULL,

    CONSTRAINT pk_interview PRIMARY KEY (interview_id),
    CONSTRAINT uq_interview_app_round UNIQUE (application_id, round_no),

    CONSTRAINT chk_interview_round_no  CHECK (round_no > 0),
    CONSTRAINT chk_interview_score     CHECK (score     IS NULL OR score     >= 0),
    CONSTRAINT chk_interview_max_score CHECK (max_score IS NULL OR max_score >  0),
    CONSTRAINT chk_interview_score_max CHECK (score IS NULL OR max_score IS NULL
                                              OR score <= max_score),
    -- An offline round must name a venue. An online round need not.
    CONSTRAINT chk_interview_venue     CHECK (`mode` = 'Online' OR venue IS NOT NULL)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 12. offer  (1:1 dependent entity)
--     UNIQUE (application_id) enforces at most one offer per application.
--     role_title / job_location / offered_ctc_lpa are a snapshot of the agreed
--     terms, the same reason an order line stores its own unit price. They are
--     not duplicates of job_drive.
--     Candidate keys: {offer_id}, {application_id}
-- ---------------------------------------------------------------------------
CREATE TABLE offer (
    offer_id              INT          NOT NULL AUTO_INCREMENT,
    application_id        INT          NOT NULL,
    offer_date            DATE         NOT NULL,
    role_title            VARCHAR(120) NOT NULL,
    offered_ctc_lpa       DECIMAL(6,2) NOT NULL,
    job_location          VARCHAR(80)  NULL,
    expected_joining_date DATE         NULL,
    offer_status          ENUM('Offered','Accepted','Declined','Expired','Revoked')
                          NOT NULL DEFAULT 'Offered',

    CONSTRAINT pk_offer PRIMARY KEY (offer_id),
    CONSTRAINT uq_offer_application UNIQUE (application_id),

    CONSTRAINT chk_offer_ctc   CHECK (offered_ctc_lpa > 0),
    CONSTRAINT chk_offer_dates CHECK (expected_joining_date IS NULL
                                      OR expected_joining_date >= offer_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


-- ---------------------------------------------------------------------------
-- 13. placement_record  (1:1 dependent entity)
--     A verified placement, which is a different fact from an accepted offer:
--     an accepted offer is the student's intention, a placement record is the
--     placement cell's verified outcome.
--     Holds ZERO columns that already exist in offer. No CTC, no company,
--     no student. Those are reached by joining through offer.
--     Candidate keys: {placement_id}, {offer_id}
-- ---------------------------------------------------------------------------
CREATE TABLE placement_record (
    placement_id          INT          NOT NULL AUTO_INCREMENT,
    offer_id              INT          NOT NULL,
    actual_joining_date   DATE         NULL,
    company_employee_code VARCHAR(40)  NULL,
    academic_year         VARCHAR(9)   NOT NULL,
    verified_by           VARCHAR(100) NOT NULL,
    verified_on           DATE         NOT NULL DEFAULT (CURRENT_DATE),
    remarks               VARCHAR(255) NULL,

    CONSTRAINT pk_placement_record PRIMARY KEY (placement_id),
    CONSTRAINT uq_placement_offer  UNIQUE      (offer_id),

    -- Format 'YYYY-YYYY', for example '2026-2027'.
    CONSTRAINT chk_placement_academic_year
        CHECK (academic_year REGEXP '^[0-9]{4}-[0-9]{4}$')
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;


SELECT '02_create_tables.sql completed' AS status;
