-- ============================================================================
-- SMART CAMPUS PLACEMENT MANAGEMENT SYSTEM
-- Course : BACSE202 - Database Systems
-- Phase  : 1  (Database Design and Table Creation)
--
-- File   : 01_create_database.sql
-- Purpose: Create the project schema with the required character set.
-- Target : MySQL 8.0.16 or later  (CHECK constraints are enforced from 8.0.16)
-- Engine : InnoDB (set per table in 02_create_tables.sql)
--
-- Run order: 01 -> 02 -> 03 -> 04
-- ============================================================================

CREATE DATABASE IF NOT EXISTS smart_campus_placement
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE smart_campus_placement;

-- Confirm what the server actually is, so the CHECK support claim is verifiable.
SELECT
    VERSION()                AS mysql_version,
    DATABASE()               AS current_database,
    @@default_storage_engine AS default_engine,
    @@character_set_database AS db_charset,
    @@collation_database     AS db_collation;
