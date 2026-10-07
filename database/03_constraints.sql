-- ============================================================================
-- SMART CAMPUS PLACEMENT MANAGEMENT SYSTEM
-- File   : 03_constraints.sql
--
-- Purpose: Apply referential integrity. 14 named FOREIGN KEY constraints.
--
-- ON DELETE policy, decided per relationship:
--   CASCADE  -> the child row has no meaning without its parent
--               (criteria, bridge rows, interview rounds)
--   RESTRICT -> the row is placement history and must never be lost silently
--               (students, companies, drives, applications, offers, masters)
--
-- ON UPDATE is RESTRICT everywhere, because every parent key is an
-- AUTO_INCREMENT surrogate that never changes.
--
-- Phase 1 scope note: cross-table business rules (eligibility enforcement,
-- "a placement record requires an accepted offer", deadline checks) CANNOT be
-- expressed as a MySQL CHECK, because a CHECK may only read columns of the row
-- being written. Those rules are documented in database/README.md and are
-- deliberately deferred to Phase 2 as triggers / application logic.
-- ============================================================================

USE smart_campus_placement;


-- --- student -> department --------------------------------------------------
ALTER TABLE student
    ADD CONSTRAINT fk_student_department
        FOREIGN KEY (dept_id) REFERENCES department (dept_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- job_drive -> company --------------------------------------------------
ALTER TABLE job_drive
    ADD CONSTRAINT fk_drive_company
        FOREIGN KEY (company_id) REFERENCES company (company_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- eligibility_criteria -> job_drive  (1:1, PK is also the FK) -----------
ALTER TABLE eligibility_criteria
    ADD CONSTRAINT fk_criteria_drive
        FOREIGN KEY (drive_id) REFERENCES job_drive (drive_id)
        ON DELETE CASCADE ON UPDATE RESTRICT;


-- --- drive_eligible_department -> job_drive, department --------------------
ALTER TABLE drive_eligible_department
    ADD CONSTRAINT fk_dedept_drive
        FOREIGN KEY (drive_id) REFERENCES job_drive (drive_id)
        ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE drive_eligible_department
    ADD CONSTRAINT fk_dedept_department
        FOREIGN KEY (dept_id) REFERENCES department (dept_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- student_skill -> student, skill ---------------------------------------
ALTER TABLE student_skill
    ADD CONSTRAINT fk_studentskill_student
        FOREIGN KEY (student_id) REFERENCES student (student_id)
        ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE student_skill
    ADD CONSTRAINT fk_studentskill_skill
        FOREIGN KEY (skill_id) REFERENCES skill (skill_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- drive_required_skill -> job_drive, skill -----------------------------
ALTER TABLE drive_required_skill
    ADD CONSTRAINT fk_driveskill_drive
        FOREIGN KEY (drive_id) REFERENCES job_drive (drive_id)
        ON DELETE CASCADE ON UPDATE RESTRICT;

ALTER TABLE drive_required_skill
    ADD CONSTRAINT fk_driveskill_skill
        FOREIGN KEY (skill_id) REFERENCES skill (skill_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- application -> student, job_drive ------------------------------------
ALTER TABLE application
    ADD CONSTRAINT fk_application_student
        FOREIGN KEY (student_id) REFERENCES student (student_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE application
    ADD CONSTRAINT fk_application_drive
        FOREIGN KEY (drive_id) REFERENCES job_drive (drive_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- interview -> application ---------------------------------------------
ALTER TABLE interview
    ADD CONSTRAINT fk_interview_application
        FOREIGN KEY (application_id) REFERENCES application (application_id)
        ON DELETE CASCADE ON UPDATE RESTRICT;


-- --- offer -> application  (1:1 via UNIQUE on application_id) -------------
ALTER TABLE offer
    ADD CONSTRAINT fk_offer_application
        FOREIGN KEY (application_id) REFERENCES application (application_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


-- --- placement_record -> offer  (1:1 via UNIQUE on offer_id) --------------
ALTER TABLE placement_record
    ADD CONSTRAINT fk_placement_offer
        FOREIGN KEY (offer_id) REFERENCES offer (offer_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT;


SELECT '03_constraints.sql completed' AS status;
