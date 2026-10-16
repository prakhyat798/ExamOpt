-- ============================================================================
-- ExamOpt Migration: 20261016000001_harden_rls_and_indexes.sql
-- Problem Statement C10: Intelligent Examination Timetable Optimization System
-- GLA University Context (CSED Block AB-XI, BCA / BCA-DS / MCA Programs)
--
-- PURPOSE:
-- 1. DEF-03: Add missing index on student_enrollments(group_id)
-- 2. DEF-01: Harden Row Level Security (RLS) across all 11 application tables
-- 3. Define least-privilege role-based access policies (Admin, Faculty, Student, Public)
-- 4. Establish user_profiles table and helper functions for identity mapping
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1: DEF-03 — Add Missing Performance Index
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_pg_student_enrollments_group 
ON student_enrollments(group_id);

-- Additional indexing for query optimization
CREATE INDEX IF NOT EXISTS idx_pg_student_enrollments_backlog 
ON student_enrollments(has_backlog);

CREATE INDEX IF NOT EXISTS idx_pg_published_schedules_active 
ON published_schedules(is_active);

-- ----------------------------------------------------------------------------
-- STEP 2: Identity & Role-Based Access Control (RBAC) Mapping
-- ----------------------------------------------------------------------------
-- Mapping table between Supabase auth.users and ExamOpt application roles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'STUDENT' CHECK (role IN ('ADMIN', 'FACULTY', 'STUDENT')),
    student_roll_no VARCHAR(50) REFERENCES student_enrollments(roll_no) ON DELETE SET NULL,
    faculty_id VARCHAR(50) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pg_user_profiles_role ON user_profiles(role);
CREATE INDEX IF NOT EXISTS idx_pg_user_profiles_roll ON user_profiles(student_roll_no);
CREATE INDEX IF NOT EXISTS idx_pg_user_profiles_fac ON user_profiles(faculty_id);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Security helper functions (SECURITY DEFINER with strict search_path to prevent recursion & search-path injection)
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
-- STEP 3: Enable RLS on All Tables (Resolving DEF-01)
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

-- ----------------------------------------------------------------------------
-- STEP 4: Access Policies for user_profiles
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their own profile" ON user_profiles;
CREATE POLICY "Users can view their own profile"
ON user_profiles FOR SELECT
USING (id = auth.uid() OR public.is_admin());

-- Ordinary users CANNOT grant themselves administrator privileges
DROP POLICY IF EXISTS "Only admins can insert or update profiles" ON user_profiles;
CREATE POLICY "Only admins can insert or update profiles"
ON user_profiles FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 5: Public Catalog Tables (rooms, timeslots, subjects)
-- Read: Public (anon and authenticated)
-- Write: Admins and service_role only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read access for rooms" ON rooms;
CREATE POLICY "Public read access for rooms"
ON rooms FOR SELECT
USING (true);

DROP POLICY IF EXISTS "Admins manage rooms" ON rooms;
CREATE POLICY "Admins manage rooms"
ON rooms FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS "Public read access for timeslots" ON timeslots;
CREATE POLICY "Public read access for timeslots"
ON timeslots FOR SELECT
USING (true);

DROP POLICY IF EXISTS "Admins manage timeslots" ON timeslots;
CREATE POLICY "Admins manage timeslots"
ON timeslots FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS "Public read access for basic metadata" ON subjects;
CREATE POLICY "Public read access for basic metadata"
ON subjects FOR SELECT
USING (true);

DROP POLICY IF EXISTS "Admins manage subjects" ON subjects;
CREATE POLICY "Admins manage subjects"
ON subjects FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 6: Student Cohorts (student_groups)
-- Read: Authenticated users only (anon blocked)
-- Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Authenticated users can view student groups" ON student_groups;
CREATE POLICY "Authenticated users can view student groups"
ON student_groups FOR SELECT
USING (auth.uid() IS NOT NULL OR public.is_admin());

DROP POLICY IF EXISTS "Admins manage student groups" ON student_groups;
CREATE POLICY "Admins manage student groups"
ON student_groups FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 7: Private Student Data (student_enrollments)
-- Read: 
--   - Students can ONLY read their own enrollment record
--   - Admins can read all records
--   - Unauthenticated anon users are strictly BLOCKED
-- Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Students can view only own enrollment" ON student_enrollments;
CREATE POLICY "Students can view only own enrollment"
ON student_enrollments FOR SELECT
USING (
    roll_no = public.get_current_student_roll_no()
    OR public.is_admin()
);

DROP POLICY IF EXISTS "Admins manage student enrollments" ON student_enrollments;
CREATE POLICY "Admins manage student enrollments"
ON student_enrollments FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 8: Student-Subject Junction (student_subject_enrollments)
-- Read:
--   - Students can view only their own subject enrollments
--   - Admins can view all
--   - Unauthenticated anon users are strictly BLOCKED
-- Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Students can view only own subject enrollments" ON student_subject_enrollments;
CREATE POLICY "Students can view only own subject enrollments"
ON student_subject_enrollments FOR SELECT
USING (
    roll_no = public.get_current_student_roll_no()
    OR public.is_admin()
);

DROP POLICY IF EXISTS "Admins manage subject enrollments" ON student_subject_enrollments;
CREATE POLICY "Admins manage subject enrollments"
ON student_subject_enrollments FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 9: Faculty Roster (faculty)
-- Read:
--   - Faculty can view their own record and duty limits
--   - Admins can view all
--   - Authenticated students can view basic faculty name/dept for exam information
--   - Unauthenticated anon users are strictly BLOCKED
-- Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Faculty view access" ON faculty;
CREATE POLICY "Faculty view access"
ON faculty FOR SELECT
USING (
    auth.uid() IS NOT NULL 
    OR public.is_admin()
);

DROP POLICY IF EXISTS "Admins manage faculty" ON faculty;
CREATE POLICY "Admins manage faculty"
ON faculty FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 10: Scheduling Runs (scheduling_runs)
-- Draft runs and parameters are strictly confidential
-- Read & Write: Admins only (anon & non-admin blocked)
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Admins only access scheduling runs" ON scheduling_runs;
CREATE POLICY "Admins only access scheduling runs"
ON scheduling_runs FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 11: Schedule Conflicts / Diagnostics (schedule_conflicts)
-- Diagnostic logs must never be exposed publicly
-- Read & Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Admins only access schedule conflicts" ON schedule_conflicts;
CREATE POLICY "Admins only access schedule conflicts"
ON schedule_conflicts FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 12: Scheduled Exams (scheduled_exams)
-- Read:
--   - Public/Anon: ONLY exams belonging to an active published schedule
--   - Admins: All runs (including drafts)
-- Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read access for scheduled exams under published active schedules" ON scheduled_exams;
CREATE POLICY "Public read access for scheduled exams under published active schedules"
ON scheduled_exams FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM published_schedules ps 
        WHERE ps.run_id = scheduled_exams.run_id AND ps.is_active = TRUE
    )
    OR public.is_admin()
);

DROP POLICY IF EXISTS "Admins manage scheduled exams" ON scheduled_exams;
CREATE POLICY "Admins manage scheduled exams"
ON scheduled_exams FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 13: Published Schedules (published_schedules)
-- Read:
--   - Public/Anon: Active published schedules (is_active = TRUE)
--   - Admins: All schedule versions
-- Write: Admins only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read access for published schedules" ON published_schedules;
CREATE POLICY "Public read access for published schedules"
ON published_schedules FOR SELECT
USING (
    is_active = TRUE
    OR public.is_admin()
);

DROP POLICY IF EXISTS "Admins manage published schedules" ON published_schedules;
CREATE POLICY "Admins manage published schedules"
ON published_schedules FOR ALL
USING (public.is_admin())
WITH CHECK (public.is_admin());

-- ----------------------------------------------------------------------------
-- STEP 14: Grants Adjustment
-- Restrict direct modification grants on anon and authenticated roles
-- ----------------------------------------------------------------------------
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;

-- Allow SELECT on public metadata and published schedules
GRANT SELECT ON rooms, timeslots, subjects TO anon, authenticated;
GRANT SELECT ON published_schedules, scheduled_exams TO anon, authenticated;

-- Allow authenticated users to query authorized records through RLS
GRANT SELECT ON student_groups, student_enrollments, student_subject_enrollments, faculty, user_profiles TO authenticated;

-- Admin and service role retain full management privileges
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role, authenticated, anon;
