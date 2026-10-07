-- ============================================================================
-- SMART CAMPUS PLACEMENT MANAGEMENT SYSTEM
-- File   : 04_verify.sql
-- Purpose: Evidence queries for the Phase 1 rubric.
--          Run each block in MySQL Workbench and screenshot the result grid.
-- ============================================================================

USE smart_campus_placement;

-- === V0. Server facts ======================================================
SELECT VERSION() AS mysql_version, DATABASE() AS current_db;

-- === V1. All tables exist (expect 13 rows) =================================
SHOW TABLES;

-- === V1b. Table count, engine and charset check ============================
SELECT TABLE_NAME, ENGINE, TABLE_COLLATION
FROM   INFORMATION_SCHEMA.TABLES
WHERE  TABLE_SCHEMA = 'smart_campus_placement'
ORDER  BY TABLE_NAME;

-- === V2. Structure of the main entity ======================================
DESCRIBE student;

-- === V3. Structure of an associative entity ================================
DESCRIBE application;

-- === V4. Composite primary key on a bridge table ==========================
DESCRIBE student_skill;
DESCRIBE drive_eligible_department;

-- === V5. The 1:1 dependent whose PK is also its FK ========================
DESCRIBE eligibility_criteria;

-- === V6. Every PRIMARY KEY, with composite keys shown in column order =====
SELECT TABLE_NAME,
       GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION) AS primary_key_columns
FROM   INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE  TABLE_SCHEMA = 'smart_campus_placement'
  AND  CONSTRAINT_NAME = 'PRIMARY'
GROUP  BY TABLE_NAME
ORDER  BY TABLE_NAME;

-- === V7. Every FOREIGN KEY with its referenced table and delete rule ======
SELECT k.CONSTRAINT_NAME        AS fk_name,
       k.TABLE_NAME             AS child_table,
       k.COLUMN_NAME            AS child_column,
       k.REFERENCED_TABLE_NAME  AS parent_table,
       k.REFERENCED_COLUMN_NAME AS parent_column,
       r.DELETE_RULE,
       r.UPDATE_RULE
FROM        INFORMATION_SCHEMA.KEY_COLUMN_USAGE k
JOIN        INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS r
         ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA
        AND r.CONSTRAINT_NAME   = k.CONSTRAINT_NAME
WHERE  k.TABLE_SCHEMA = 'smart_campus_placement'
  AND  k.REFERENCED_TABLE_NAME IS NOT NULL
ORDER  BY k.TABLE_NAME, k.CONSTRAINT_NAME;

-- === V8. Every UNIQUE constraint (composite ones shown in column order) ====
SELECT TABLE_NAME,
       CONSTRAINT_NAME,
       GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION) AS unique_columns
FROM   INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE  TABLE_SCHEMA = 'smart_campus_placement'
  AND  CONSTRAINT_NAME <> 'PRIMARY'
  AND  REFERENCED_TABLE_NAME IS NULL
GROUP  BY TABLE_NAME, CONSTRAINT_NAME
ORDER  BY TABLE_NAME, CONSTRAINT_NAME;

-- === V9. Every CHECK constraint with its expression =======================
SELECT c.TABLE_NAME, c.CONSTRAINT_NAME, k.CHECK_CLAUSE
FROM        INFORMATION_SCHEMA.TABLE_CONSTRAINTS c
JOIN        INFORMATION_SCHEMA.CHECK_CONSTRAINTS k
         ON k.CONSTRAINT_SCHEMA = c.CONSTRAINT_SCHEMA
        AND k.CONSTRAINT_NAME   = c.CONSTRAINT_NAME
WHERE  c.TABLE_SCHEMA     = 'smart_campus_placement'
  AND  c.CONSTRAINT_TYPE  = 'CHECK'
ORDER  BY c.TABLE_NAME, c.CONSTRAINT_NAME;

-- === V10. Constraint count summary =======================================
SELECT CONSTRAINT_TYPE, COUNT(*) AS total
FROM   INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE  TABLE_SCHEMA = 'smart_campus_placement'
GROUP  BY CONSTRAINT_TYPE
ORDER  BY CONSTRAINT_TYPE;
