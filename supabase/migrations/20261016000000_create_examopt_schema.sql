-- ExamOpt PostgreSQL Schema Migration for Supabase
-- Problem Statement C10: Intelligent Examination Timetable Optimization System

-- Enable pgcrypto / uuid-ossp if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Examination Rooms Table
CREATE TABLE IF NOT EXISTS rooms (
    room_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    building VARCHAR(255) NOT NULL DEFAULT 'AB-XI CSED Block',
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    room_type VARCHAR(20) NOT NULL CHECK (room_type IN ('THEORY', 'LAB')),
    unavailable_slots TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Examination Time Slots Table
CREATE TABLE IF NOT EXISTS timeslots (
    slot_id VARCHAR(50) PRIMARY KEY,
    day_number INTEGER NOT NULL CHECK (day_number BETWEEN 1 AND 14),
    exam_date DATE NOT NULL,
    session VARCHAR(20) NOT NULL CHECK (session IN ('MORNING', 'EVENING')),
    time_range VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(exam_date, session)
);

-- 3. Faculty / Invigilators Table
CREATE TABLE IF NOT EXISTS faculty (
    faculty_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(50) NOT NULL CHECK (department IN ('CSED', 'BCA', 'MCA')),
    unavailable_slots TEXT DEFAULT '',
    max_duties INTEGER NOT NULL DEFAULT 4 CHECK (max_duties >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Subjects / Courses Table
CREATE TABLE IF NOT EXISTS subjects (
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

-- 5. Student Groups Table
CREATE TABLE IF NOT EXISTS student_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    program VARCHAR(50) NOT NULL CHECK (program IN ('BCA', 'BCA-DS', 'MCA')),
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    is_backlog_group BOOLEAN NOT NULL DEFAULT FALSE,
    student_count INTEGER NOT NULL DEFAULT 0 CHECK (student_count >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Student Enrollments Table
CREATE TABLE IF NOT EXISTS student_enrollments (
    roll_no VARCHAR(50) PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    group_id VARCHAR(50) NOT NULL REFERENCES student_groups(group_id) ON DELETE RESTRICT,
    enrolled_subject_ids TEXT NOT NULL,
    has_backlog BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Normalized Student-Subject Junction
CREATE TABLE IF NOT EXISTS student_subject_enrollments (
    id BIGSERIAL PRIMARY KEY,
    roll_no VARCHAR(50) NOT NULL REFERENCES student_enrollments(roll_no) ON DELETE CASCADE,
    subject_id VARCHAR(50) NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(roll_no, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_pg_sse_roll_no ON student_subject_enrollments(roll_no);
CREATE INDEX IF NOT EXISTS idx_pg_sse_subject_id ON student_subject_enrollments(subject_id);

-- 8. Scheduling Runs Table
CREATE TABLE IF NOT EXISTS scheduling_runs (
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
CREATE TABLE IF NOT EXISTS scheduled_exams (
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

CREATE INDEX IF NOT EXISTS idx_pg_se_run_id ON scheduled_exams(run_id);
CREATE INDEX IF NOT EXISTS idx_pg_se_slot_room ON scheduled_exams(run_id, slot_id, room_id);
CREATE INDEX IF NOT EXISTS idx_pg_se_slot_faculty ON scheduled_exams(run_id, slot_id, assigned_faculty_id);

-- 10. Published Schedules Table
CREATE TABLE IF NOT EXISTS published_schedules (
    published_id VARCHAR(100) PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    run_id VARCHAR(100) NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    published_by VARCHAR(255) NOT NULL DEFAULT 'Exam Superintendent Office',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Conflicts / Diagnostics Log Table
CREATE TABLE IF NOT EXISTS schedule_conflicts (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    conflict_type VARCHAR(100) NOT NULL,
    subject_id_1 VARCHAR(50) NOT NULL,
    subject_id_2 VARCHAR(50),
    entity_id VARCHAR(100),
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security (RLS) Configuration
ALTER TABLE published_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeslots ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;

-- Allow public read access to published active timetables
CREATE POLICY "Public read access for published schedules" 
ON published_schedules FOR SELECT USING (is_active = TRUE);

CREATE POLICY "Public read access for scheduled exams under published active schedules" 
ON scheduled_exams FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM published_schedules ps 
        WHERE ps.run_id = scheduled_exams.run_id AND ps.is_active = TRUE
    )
);

CREATE POLICY "Public read access for basic metadata" 
ON subjects FOR SELECT USING (true);

CREATE POLICY "Public read access for timeslots" 
ON timeslots FOR SELECT USING (true);

CREATE POLICY "Public read access for rooms" 
ON rooms FOR SELECT USING (true);
