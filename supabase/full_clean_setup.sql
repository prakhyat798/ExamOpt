-- ============================================================================
-- ExamOpt: Complete Clean Setup & Hardened Schema for Supabase PostgreSQL
-- Problem Statement C10: Intelligent Examination Timetable Optimization System
-- GLA University Context: CSED Block AB-XI, BCA / BCA-DS / MCA Programs
-- 
-- INSTRUCTIONS FOR USE:
-- 1. Open your Supabase Dashboard: https://supabase.com/dashboard/project/tvyiqyngqehrxrcxqwei/sql/new
-- 2. Paste this entire script into the SQL Editor.
-- 3. Click "Run" (or Ctrl+Enter).
--
-- This script:
--   - Safely removes any erroneous or stale tables/policies in schema public.
--   - Recreates all 11 core ExamOpt relational tables with strict constraints.
--   - Adds all performance indexes (including idx_pg_student_enrollments_group).
--   - Configures the user_profiles table for role-based authentication.
--   - Enables Row Level Security (RLS) on all 12 tables.
--   - Enforces least-privilege access policies for public, students, faculty, and admins.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1: Clean Up Stale / Erroneous Objects (Safe Cascade Drop)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS schedule_conflicts CASCADE;
DROP TABLE IF EXISTS published_schedules CASCADE;
DROP TABLE IF EXISTS scheduled_exams CASCADE;
DROP TABLE IF EXISTS scheduling_runs CASCADE;
DROP TABLE IF EXISTS student_subject_enrollments CASCADE;
DROP TABLE IF EXISTS student_enrollments CASCADE;
DROP TABLE IF EXISTS student_groups CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS faculty CASCADE;
DROP TABLE IF EXISTS timeslots CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;

DROP FUNCTION IF EXISTS public.get_current_user_role() CASCADE;
DROP FUNCTION IF EXISTS public.get_current_student_roll_no() CASCADE;
DROP FUNCTION IF EXISTS public.get_current_faculty_id() CASCADE;
DROP FUNCTION IF EXISTS public.is_admin() CASCADE;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- STEP 2: Create Core Relational Tables
-- ----------------------------------------------------------------------------

-- 1. Examination Rooms Table
CREATE TABLE rooms (
    room_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    building VARCHAR(255) NOT NULL DEFAULT 'AB-XI CSED Block',
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    room_type VARCHAR(20) NOT NULL CHECK (room_type IN ('THEORY', 'LAB')),
    unavailable_slots TEXT DEFAULT '', -- Pipe-separated slot IDs (e.g. 'D2-M|D4-E')
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Examination Time Slots Table
CREATE TABLE timeslots (
    slot_id VARCHAR(50) PRIMARY KEY,
    day_number INTEGER NOT NULL CHECK (day_number BETWEEN 1 AND 14),
    exam_date DATE NOT NULL,
    session VARCHAR(20) NOT NULL CHECK (session IN ('MORNING', 'EVENING')),
    time_range VARCHAR(50) NOT NULL, -- e.g. '09:30 AM - 12:30 PM'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(exam_date, session)
);

-- 3. Faculty / Invigilators Table
CREATE TABLE faculty (
    faculty_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(50) NOT NULL CHECK (department IN ('CSED', 'BCA', 'MCA')),
    unavailable_slots TEXT DEFAULT '',
    max_duties INTEGER NOT NULL DEFAULT 4 CHECK (max_duties >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Subjects / Courses Table
CREATE TABLE subjects (
    subject_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    program VARCHAR(50) NOT NULL CHECK (program IN ('BCA', 'BCA-DS', 'MCA')),
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    duration_hours INTEGER NOT NULL CHECK (duration_hours IN (2, 3)),
    requires_lab BOOLEAN NOT NULL DEFAULT FALSE,
    fixed_slot VARCHAR(50) REFERENCES timeslots(slot_id) ON DELETE SET NULL,
    unavailable_slots TEXT DEFAULT '',
    enrolled_students INTEGER NOT NULL DEFAULT 0 CHECK (enrolled_students >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Student Groups / Cohorts Table
CREATE TABLE student_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    program VARCHAR(50) NOT NULL CHECK (program IN ('BCA', 'BCA-DS', 'MCA')),
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    is_backlog_group BOOLEAN NOT NULL DEFAULT FALSE,
    student_count INTEGER NOT NULL DEFAULT 0 CHECK (student_count >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Student Enrollments Table
CREATE TABLE student_enrollments (
    roll_no VARCHAR(50) PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    group_id VARCHAR(50) NOT NULL REFERENCES student_groups(group_id) ON DELETE RESTRICT,
    enrolled_subject_ids TEXT NOT NULL, -- Comma-separated subject IDs
    has_backlog BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Normalized Student-Subject Junction Table
CREATE TABLE student_subject_enrollments (
    id BIGSERIAL PRIMARY KEY,
    roll_no VARCHAR(50) NOT NULL REFERENCES student_enrollments(roll_no) ON DELETE CASCADE,
    subject_id VARCHAR(50) NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(roll_no, subject_id)
);

-- 8. Scheduling Runs Table
CREATE TABLE scheduling_runs (
    run_id VARCHAR(100) PRIMARY KEY,
    algorithm VARCHAR(50) NOT NULL CHECK (algorithm IN ('FIRST_FIT', 'WELSH_POWELL', 'BACKTRACKING')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('FEASIBLE', 'INFEASIBLE', 'PARTIAL', 'TIMEOUT')),
    total_exams INTEGER NOT NULL DEFAULT 0,
    scheduled_exams INTEGER NOT NULL DEFAULT 0,
    unscheduled_exams INTEGER NOT NULL DEFAULT 0,
    hard_conflicts INTEGER NOT NULL DEFAULT 0,
    soft_score NUMERIC(10, 4) NOT NULL DEFAULT 0.0,
    execution_time_ms NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Scheduled Examination Allocations Table
CREATE TABLE scheduled_exams (
    id VARCHAR(100) PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    subject_id VARCHAR(50) NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    slot_id VARCHAR(50) NOT NULL REFERENCES timeslots(slot_id) ON DELETE CASCADE,
    room_id VARCHAR(50) NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    assigned_faculty_id VARCHAR(50) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    assigned_students INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(run_id, subject_id)
);

-- 10. Published Schedules Table
CREATE TABLE published_schedules (
    published_id VARCHAR(100) PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    run_id VARCHAR(100) NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    published_by VARCHAR(255) NOT NULL DEFAULT 'Exam Superintendent Office',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Schedule Conflicts / Diagnostics Table
CREATE TABLE schedule_conflicts (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    conflict_type VARCHAR(100) NOT NULL,
    subject_id_1 VARCHAR(50) NOT NULL,
    subject_id_2 VARCHAR(50),
    entity_id VARCHAR(100),
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- STEP 3: Create Performance Indexes (DEF-03 Included)
-- ----------------------------------------------------------------------------
CREATE INDEX idx_pg_student_enrollments_group ON student_enrollments(group_id);
CREATE INDEX idx_pg_student_enrollments_backlog ON student_enrollments(has_backlog);

CREATE INDEX idx_pg_sse_roll_no ON student_subject_enrollments(roll_no);
CREATE INDEX idx_pg_sse_subject_id ON student_subject_enrollments(subject_id);

CREATE INDEX idx_pg_se_run_id ON scheduled_exams(run_id);
CREATE INDEX idx_pg_se_slot_room ON scheduled_exams(run_id, slot_id, room_id);
CREATE INDEX idx_pg_se_slot_faculty ON scheduled_exams(run_id, slot_id, assigned_faculty_id);

CREATE INDEX idx_pg_published_schedules_active ON published_schedules(is_active);

-- ----------------------------------------------------------------------------
-- STEP 4: Authentication & User Profiles Table
-- ----------------------------------------------------------------------------
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'STUDENT' CHECK (role IN ('ADMIN', 'FACULTY', 'STUDENT')),
    student_roll_no VARCHAR(50) REFERENCES student_enrollments(roll_no) ON DELETE SET NULL,
    faculty_id VARCHAR(50) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pg_user_profiles_role ON user_profiles(role);
CREATE INDEX idx_pg_user_profiles_roll ON user_profiles(student_roll_no);
CREATE INDEX idx_pg_user_profiles_fac ON user_profiles(faculty_id);

-- ----------------------------------------------------------------------------
-- STEP 5: Security Helper Functions (SECURITY DEFINER with strict search_path)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_current_user_role()
RETURNS VARCHAR(50)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, auth
STABLE
AS $$
    SELECT role FROM public.user_profiles WHERE id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.get_current_student_roll_no()
RETURNS VARCHAR(50)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, auth
STABLE
AS $$
    SELECT student_roll_no FROM public.user_profiles WHERE id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.get_current_faculty_id()
RETURNS VARCHAR(50)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, auth
STABLE
AS $$
    SELECT faculty_id FROM public.user_profiles WHERE id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, auth
STABLE
AS $$
    SELECT COALESCE(
        (SELECT role = 'ADMIN' FROM public.user_profiles WHERE id = auth.uid()),
        (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'role') = 'admin',
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role') = 'service_role',
        FALSE
    );
$$;

-- ----------------------------------------------------------------------------
-- STEP 6: Enable Row Level Security (RLS) Across ALL Tables (DEF-01)
-- ----------------------------------------------------------------------------
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeslots ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_subject_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE faculty ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduling_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE published_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_conflicts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- STEP 7: Least-Privilege RLS Policies
-- ----------------------------------------------------------------------------

-- A. user_profiles
CREATE POLICY "Users can view their own profile"
ON user_profiles FOR SELECT
USING (id = auth.uid() OR public.is_admin());

CREATE POLICY "Only admins can insert or update profiles"
ON user_profiles FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- B. Public Metadata (rooms, timeslots, subjects)
CREATE POLICY "Public read access for rooms"
ON rooms FOR SELECT USING (true);

CREATE POLICY "Admins manage rooms"
ON rooms FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY "Public read access for timeslots"
ON timeslots FOR SELECT USING (true);

CREATE POLICY "Admins manage timeslots"
ON timeslots FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY "Public read access for basic metadata"
ON subjects FOR SELECT USING (true);

CREATE POLICY "Admins manage subjects"
ON subjects FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- C. Student Groups (Authenticated only; Anon blocked)
CREATE POLICY "Authenticated users can view student groups"
ON student_groups FOR SELECT
USING (auth.uid() IS NOT NULL OR public.is_admin());

CREATE POLICY "Admins manage student groups"
ON student_groups FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- D. Student Enrollments (Private: Students view own; Anon blocked)
CREATE POLICY "Students can view only own enrollment"
ON student_enrollments FOR SELECT
USING (roll_no = public.get_current_student_roll_no() OR public.is_admin());

CREATE POLICY "Admins manage student enrollments"
ON student_enrollments FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- E. Student-Subject Junction (Private: Students view own; Anon blocked)
CREATE POLICY "Students can view only own subject enrollments"
ON student_subject_enrollments FOR SELECT
USING (roll_no = public.get_current_student_roll_no() OR public.is_admin());

CREATE POLICY "Admins manage subject enrollments"
ON student_subject_enrollments FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- F. Faculty Roster (Authenticated only; Anon blocked)
CREATE POLICY "Faculty view access"
ON faculty FOR SELECT
USING (auth.uid() IS NOT NULL OR public.is_admin());

CREATE POLICY "Admins manage faculty"
ON faculty FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- G. Scheduling Runs (Admin only; Drafts strictly confidential)
CREATE POLICY "Admins only access scheduling runs"
ON scheduling_runs FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- H. Schedule Conflicts (Admin only; Diagnostic logs strictly confidential)
CREATE POLICY "Admins only access schedule conflicts"
ON schedule_conflicts FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- I. Scheduled Exams (Public can only view exams under ACTIVE published schedules)
CREATE POLICY "Public read access for scheduled exams under published active schedules"
ON scheduled_exams FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM published_schedules ps 
        WHERE ps.run_id = scheduled_exams.run_id AND ps.is_active = TRUE
    )
    OR public.is_admin()
);

CREATE POLICY "Admins manage scheduled exams"
ON scheduled_exams FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- J. Published Schedules (Public can only view active published schedules)
CREATE POLICY "Public read access for published schedules"
ON published_schedules FOR SELECT
USING (is_active = TRUE OR public.is_admin());

CREATE POLICY "Admins manage published schedules"
ON published_schedules FOR ALL
USING (public.is_admin()) WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 8: Grants Configuration
-- ----------------------------------------------------------------------------
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;

-- Allow public read access to course catalog & published timetables
GRANT SELECT ON rooms, timeslots, subjects TO anon, authenticated;
GRANT SELECT ON published_schedules, scheduled_exams TO anon, authenticated;

-- Allow authenticated users to query authorized rows via RLS
GRANT SELECT ON student_groups, student_enrollments, student_subject_enrollments, faculty, user_profiles TO authenticated;

-- Service role and admin maintain complete control
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role, authenticated, anon;
