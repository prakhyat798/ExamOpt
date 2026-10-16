-- ExamOpt Database Schema (SQLite & PostgreSQL Compatible)
-- Problem Statement C10: Intelligent Examination Timetable Optimization System
-- GLA University Context: CSED Block AB-XI, BCA / BCA-DS / MCA Programs

PRAGMA foreign_keys = ON;

-- 1. Examination Rooms Table
CREATE TABLE IF NOT EXISTS rooms (
    room_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    building TEXT NOT NULL DEFAULT 'AB-XI CSED Block',
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    room_type TEXT NOT NULL CHECK (room_type IN ('THEORY', 'LAB')),
    unavailable_slots TEXT DEFAULT '', -- Pipe-separated slot IDs (e.g. 'D2-M|D4-E')
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Examination Time Slots Table
CREATE TABLE IF NOT EXISTS timeslots (
    slot_id TEXT PRIMARY KEY,
    day_number INTEGER NOT NULL CHECK (day_number BETWEEN 1 AND 14),
    exam_date TEXT NOT NULL, -- YYYY-MM-DD
    session TEXT NOT NULL CHECK (session IN ('MORNING', 'EVENING')),
    time_range TEXT NOT NULL, -- e.g. '09:30 AM - 12:30 PM'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exam_date, session)
);

-- 3. Faculty / Invigilators Table
CREATE TABLE IF NOT EXISTS faculty (
    faculty_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL CHECK (department IN ('CSED', 'BCA', 'MCA')),
    unavailable_slots TEXT DEFAULT '', -- Pipe-separated slot IDs
    max_duties INTEGER NOT NULL DEFAULT 4 CHECK (max_duties >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Subjects / Courses Table
CREATE TABLE IF NOT EXISTS subjects (
    subject_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    program TEXT NOT NULL CHECK (program IN ('BCA', 'BCA-DS', 'MCA')),
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    duration_hours INTEGER NOT NULL CHECK (duration_hours IN (2, 3)),
    requires_lab INTEGER NOT NULL DEFAULT 0 CHECK (requires_lab IN (0, 1)), -- 1=True, 0=False
    fixed_slot TEXT DEFAULT NULL REFERENCES timeslots(slot_id) ON DELETE SET NULL,
    unavailable_slots TEXT DEFAULT '', -- Pipe-separated slot IDs
    enrolled_students INTEGER NOT NULL DEFAULT 0 CHECK (enrolled_students >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Student Groups / Cohorts Table
CREATE TABLE IF NOT EXISTS student_groups (
    group_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    program TEXT NOT NULL CHECK (program IN ('BCA', 'BCA-DS', 'MCA')),
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    is_backlog_group INTEGER NOT NULL DEFAULT 0 CHECK (is_backlog_group IN (0, 1)),
    student_count INTEGER NOT NULL DEFAULT 0 CHECK (student_count >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Individual Student Enrollments Table
CREATE TABLE IF NOT EXISTS student_enrollments (
    roll_no TEXT PRIMARY KEY,
    student_name TEXT NOT NULL,
    group_id TEXT NOT NULL REFERENCES student_groups(group_id) ON DELETE RESTRICT,
    enrolled_subject_ids TEXT NOT NULL, -- Comma-separated subject IDs
    has_backlog INTEGER NOT NULL DEFAULT 0 CHECK (has_backlog IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Normalized Student-to-Subject Enrollment Junction Table
CREATE TABLE IF NOT EXISTS student_subject_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT NOT NULL REFERENCES student_enrollments(roll_no) ON DELETE CASCADE,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(roll_no, subject_id)
);

-- Indexes for lightning fast conflict graph queries
CREATE INDEX IF NOT EXISTS idx_sse_roll_no ON student_subject_enrollments(roll_no);
CREATE INDEX IF NOT EXISTS idx_sse_subject_id ON student_subject_enrollments(subject_id);
CREATE INDEX IF NOT EXISTS idx_student_enrollments_group ON student_enrollments(group_id);

-- 8. Scheduling Runs Table
CREATE TABLE IF NOT EXISTS scheduling_runs (
    run_id TEXT PRIMARY KEY,
    algorithm TEXT NOT NULL CHECK (algorithm IN ('FIRST_FIT', 'WELSH_POWELL', 'BACKTRACKING')),
    status TEXT NOT NULL CHECK (status IN ('FEASIBLE', 'INFEASIBLE', 'PARTIAL', 'TIMEOUT')),
    total_exams INTEGER NOT NULL DEFAULT 0,
    scheduled_exams INTEGER NOT NULL DEFAULT 0,
    unscheduled_exams INTEGER NOT NULL DEFAULT 0,
    hard_conflicts INTEGER NOT NULL DEFAULT 0,
    soft_score REAL NOT NULL DEFAULT 0.0,
    execution_time_ms REAL NOT NULL DEFAULT 0.0,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Scheduled Examination Allocations Table
CREATE TABLE IF NOT EXISTS scheduled_exams (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    slot_id TEXT NOT NULL REFERENCES timeslots(slot_id) ON DELETE CASCADE,
    room_id TEXT NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    assigned_faculty_id TEXT REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    assigned_students INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_se_run_id ON scheduled_exams(run_id);
CREATE INDEX IF NOT EXISTS idx_se_slot_room ON scheduled_exams(run_id, slot_id, room_id);
CREATE INDEX IF NOT EXISTS idx_se_slot_faculty ON scheduled_exams(run_id, slot_id, assigned_faculty_id);

-- 10. Published Schedules Table (Authoritative state visible to Web & Mobile PWA)
CREATE TABLE IF NOT EXISTS published_schedules (
    published_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    run_id TEXT NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    published_by TEXT NOT NULL DEFAULT 'Exam Superintendent Office',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Schedule Audit & Conflict Log Table
CREATE TABLE IF NOT EXISTS schedule_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    conflict_type TEXT NOT NULL, -- STUDENT_CLASH, ROOM_OVERFLOW, ROOM_UNAVAILABLE, FACULTY_CLASH, FIXED_SLOT_VIOLATION
    subject_id_1 TEXT NOT NULL,
    subject_id_2 TEXT DEFAULT NULL,
    entity_id TEXT DEFAULT NULL, -- roll_no, room_id, faculty_id
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
