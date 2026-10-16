# ExamOpt — Forensic Audit & Verification Report (Task 1)
**Project**: ExamOpt (Problem Statement C10: Intelligent Examination Timetable Optimization System)  
**Repository**: [https://github.com/prakhyat798/ExamOpt](https://github.com/prakhyat798/ExamOpt)  
**Date of Audit**: 2026-10-16  
**Auditor**: Lead Full-Stack & Systems Verification Agent  

---

## 1. Executive Summary

This forensic audit evaluates the Phase 1 implementation of **ExamOpt**, an intelligent examination timetable optimization platform tailored to the GLA University context (CSED Block AB-XI, BCA / BCA-DS / MCA programs).

### Key Audit Findings:
- **Core Functionality & Local Stack**: **PASS**. The local data engineering, deterministic dataset generation, data quality validation, three deterministic scheduling algorithms (First-Fit, Welsh–Powell, MRV Backtracking), FastAPI backend, and React/Tailwind frontend are fully implemented, verified, and passing all automated test suites.
- **Data Integrity**: **PASS**. 15 rooms, 10 slots, 20 faculty, 24 courses, 8 student groups, 355 individual students, 1,735 subject enrollments, and 70 backlog students are verified with 100% mathematical consistency and 0 foreign key violations.
- **Schedulability**: **PASS**. The baseline dataset is proven 100% schedulable with 0 student clashes across all 3 optimization algorithms.
- **Supabase Cloud Architecture**: **DEFECT / ARCHITECTURAL GAP**. While the PostgreSQL migration file exists with preliminary RLS policies, the backend currently operates solely against local SQLite (`examopt.db`) and has no active database client or repository layer for remote Supabase PostgreSQL.
- **Security & RLS**: **DEFECT (P1)**. 6 out of 11 tables in the Supabase PostgreSQL migration lack Row Level Security (RLS) activation, which would allow unauthenticated read access to student personal data (`student_enrollments`) and faculty records (`faculty`) if migrated without revision.
- **Repository Hygiene**: **PASS**. Zero `.env` files, API keys, or secrets are committed to version control.

---

## 2. Verified Files and Modules

| File Path | Type | Audit Status | Demonstrated Runtime Behavior |
| :--- | :--- | :--- | :--- |
| `README.md` | Documentation | **PASS** | Complete architectural blueprint, constraint definitions, and start commands. |
| `EXAMOPT-PHASE-1-HANDOFF.md` | Collaboration Guide | **PASS** | Defines separation of responsibilities for 2 developers, API routes, and schema reference. |
| `docs/IMPLEMENTATION_STATUS.md` | Status Tracking | **PASS** | Up to date with test results and verification matrix. |
| `.env.example` | Config Template | **PASS** | Contains clean placeholders only; zero real secrets. |
| `.gitignore` | Git Hygiene | **PASS** | Properly excludes `.env`, `*.db`, `node_modules/`, `.venv/`, `dist/`. |
| `run_dev.py` | Command Runner | **PASS** | Auto-checks database existence, seeds if missing, and launches unified Uvicorn server on port 8000. |
| `backend/schema.sql` | SQLite DDL | **PASS** | Normalized schema with 11 tables, PKs, FKs, CHECK constraints, and indexes. |
| `supabase/migrations/20261016000000_create_examopt_schema.sql` | PG Migration | **PASS (with findings)** | PostgreSQL DDL matching SQLite tables, but has incomplete RLS table coverage. |
| `backend/seed_generator.py` | Synthetic Generator | **PASS** | Deterministic generator (`random.seed(42)`); populates SQLite and generates clean & edge-case CSVs. |
| `backend/validator.py` | Data Quality Engine | **PASS** | Multi-phase constraint inspector returning structured JSON reports with readiness scores. |
| `backend/sample_datasets/normal_gla_dataset/` | Clean Fixtures | **PASS** | 6 CSVs (`rooms`, `timeslots`, `faculty`, `subjects`, `student_groups`, `student_enrollments`). Score: 100/100. |
| `backend/sample_datasets/edge_case_lab_bottleneck.csv` | Infeasible Fixture | **PASS** | 6 lab exams locked to D1-M; correctly flagged as `LAB_BOTTLENECK`. |
| `backend/sample_datasets/edge_case_capacity_overflow.csv` | Infeasible Fixture | **PASS** | 650 enrolled students; correctly flagged as `CAPACITY_OVERFLOW`. |
| `backend/sample_datasets/invalid_corrupted_input.csv` | Corrupt Fixture | **PASS** | Catches 6 errors: duplicates, negative counts, contradictory slots, missing fields, invalid slots. |
| `backend/app/algorithms/conflict_graph.py` | Algorithm Layer | **PASS** | Builds weighted student conflict graph; connects cross-semester backlog edges. |
| `backend/app/algorithms/baseline_first_fit.py` | Algorithm Layer | **PASS** | Algorithm A: Greedy first-fit scheduler; achieves 0 student clashes. |
| `backend/app/algorithms/welsh_powell.py` | Algorithm Layer | **PASS** | Algorithm B: Welsh–Powell degree ordering + Best-Fit room packing. |
| `backend/app/algorithms/backtracking.py` | Algorithm Layer | **PASS** | Algorithm C: MRV constraint backtracking with forward checking & room feasibility. |
| `backend/app/algorithms/room_allocator.py` | Algorithm Layer | **PASS** | Best-Fit capacity packing respecting `THEORY` vs `LAB` type and availability. |
| `backend/app/algorithms/faculty_allocator.py` | Algorithm Layer | **PASS** | Workload balancing invigilator assignment respecting duty limits and department alignment. |
| `backend/app/services/optimizer.py` | Service Layer | **PASS** | Multi-algorithm comparison engine computing soft scores, runtimes, and room utilization. |
| `backend/app/services/exporter.py` | Service Layer | **PASS** | Generates formatted CSV exports for timetables and room allocations. |
| `backend/main.py` | API Server | **PASS** | Unified FastAPI server hosting Phase 1 `/api/data/*`, `/api/v1/*`, and serving React SPA static build. |
| `backend/tests/` (3 test files) | Automated Suite | **PASS** | 14 automated tests covering data quality, algorithm correctness, and API endpoints. |
| `frontend/package.json` | Client Tooling | **PASS** | React 18, TypeScript, Vite, Tailwind CSS, Lucide React. |
| `frontend/src/App.tsx` | Client UI | **PASS** | Full Admin overview, Timetable Grid with filters, Validation Panel, Benchmark table, Student & Faculty views. |
| `frontend/src/services/api.ts` | Client API Layer | **PASS** | Typed fetch wrappers for all FastAPI endpoints. |
| `frontend/public/manifest.json` | Mobile PWA | **PASS** | Standalone PWA web app manifest. |

---

## 3. Synthetic Data Verification Results

Programmatic assertions were executed directly against the database and generated datasets:

| Verification Check | Programmatic Assertion | Status | Details |
| :--- | :--- | :--- | :--- |
| **Deterministic Generation** | `students_run1 == students_run2` | **PASS** | Seed `42` produces 100% byte-identical student and junction records across runs. |
| **Expected Row Counts** | `assert counts == expected` | **PASS** | Rooms: 15, Timeslots: 10, Faculty: 20, Subjects: 24, Groups: 8, Students: 355, Enrollments: 1,735. |
| **Primary Key Uniqueness** | `total_rows == distinct_pk_count` | **PASS** | 0 duplicate primary keys across all 6 operational tables. |
| **Foreign Key Integrity** | `PRAGMA foreign_key_check;` | **PASS** | Exactly 0 foreign key violations detected. |
| **Valid Timeslot References** | `fixed_slot in valid_slots` | **PASS** | All fixed slots and unavailable slot pipes resolve to defined slot IDs (`D1-M` to `D5-E`). |
| **Positive Room Capacities** | `capacity > 0` | **PASS** | All 15 rooms have positive capacity (range: 50 to 150). Total theory: 1,040 seats; lab: 440 seats. |
| **Enrollment Consistency** | `subject.enrolled == count(sse)` | **PASS** | **100% mathematical consistency**. Every subject's declared enrollment matches actual student records. |
| **Cross-Semester Backlog** | `count(cross_cohort_edges)` | **PASS** | **70 backlog students** create verified clash edges: 50 cross-semester + 20 cross-program bridge students. |
| **Laboratory Requirements** | `enrolled <= max_lab_capacity` | **PASS** | All 8 practical/lab courses require $\le 85$ seats, fitting into physical labs (max: 100 seats). |
| **Clean vs Malformed Separation**| Separate directory isolation | **PASS** | Clean dataset is isolated in `normal_gla_dataset/`; corrupt fixtures in `sample_datasets/` root. |
| **Infeasible vs Malformed Distinction** | Validator error classifications | **PASS** | `LAB_BOTTLENECK` and `CAPACITY_OVERFLOW` are classified as valid-but-infeasible constraint failures; `invalid_corrupted_input.csv` is rejected for syntactic/type corruption. |
| **True Schedulability** | Execution of all 3 algorithms | **PASS** | **Verified 100% schedulable**. All 3 algorithms schedule 24/24 exams with **0 hard conflicts**. |

---

## 4. SQLite versus Supabase Architecture Findings

### Current Data Access Flow
- The application currently accesses data **exclusively through SQLite** via `backend/examopt.db`.
- `backend/main.py` connects using Python's standard `sqlite3` module (`sqlite3.connect(SQLITE_DB_PATH)` with `PRAGMA foreign_keys = ON;`).
- Algorithm modules receive in-memory dictionaries and lists from `main.py`, making them database-agnostic.

### Supabase / PostgreSQL Integration Status
- **Current Status**: **DEFECT / INCOMPLETE WIRING**.
- An environment variable check exists in `GET /health` (`supabase_cloud_configured: bool`), but there is **no database client library** (such as `supabase-py`, `psycopg2`, `asyncpg`, or `SQLAlchemy`) installed or wired in `main.py` to query remote PostgreSQL tables.
- **Offline / Cloud Independence**: The application runs completely and reliably without Supabase credentials.
- **Failure Transparency**: The `/health` endpoint transparently surfaces `"supabase_cloud_configured": false`. It does not report false success.

### Schema Comparison (SQLite `schema.sql` vs Supabase Migration)

| Feature / Table | SQLite `backend/schema.sql` | Supabase Migration `20261016...sql` | Discrepancy / Finding |
| :--- | :--- | :--- | :--- |
| **Table Count** | 11 tables | 11 tables | Names and foreign-key graph match exactly. |
| **Boolean Types** | `INTEGER CHECK (col IN (0, 1))` | `BOOLEAN DEFAULT FALSE` | Handled natively by respective SQL dialects. |
| **Timestamp Types** | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMPTZ DEFAULT NOW()` | Compatible. |
| **String Types** | `TEXT` | `VARCHAR(50)`, `VARCHAR(255)`, `TEXT` | PostgreSQL enforces maximum string lengths. |
| **JSON Metadata** | `TEXT DEFAULT '{}'` | `JSONB DEFAULT '{}'::jsonb` | PostgreSQL leverages binary JSON. |
| **Group Enrollment Index** | `CREATE INDEX idx_student_enrollments_group ON student_enrollments(group_id);` | **MISSING** | **Discrepancy**: Supabase migration is missing index on `student_enrollments(group_id)`. |
| **Foreign Keys** | Enabled via `PRAGMA foreign_keys = ON;` | Enforced natively by PostgreSQL engine | Verified enforced in SQLite via tests. |

---

## 5. Migration and Row Level Security (RLS) Findings

### RLS Activation Status

| Table Name | RLS Enabled in Migration? | Security Evaluation |
| :--- | :---: | :--- |
| `published_schedules` | **YES** | **PASS**: Public read restricted to `is_active = TRUE`. |
| `scheduled_exams` | **YES** | **PASS**: Public read restricted to active published runs via subquery. |
| `subjects` | **YES** | **PASS**: Public read permitted for course catalog metadata. |
| `timeslots` | **YES** | **PASS**: Public read permitted for timetable slot metadata. |
| `rooms` | **YES** | **PASS**: Public read permitted for room and facility metadata. |
| `student_enrollments` | **NO** | **DEFECT (P1)**: Unprotected. Unauthenticated users with Anon key can read all student roll numbers and names. |
| `student_groups` | **NO** | **DEFECT (P2)**: Unprotected. Public read access to internal cohort metadata. |
| `student_subject_enrollments` | **NO** | **DEFECT (P1)**: Unprotected. Full student-to-subject enrollment graph exposed publicly. |
| `faculty` | **NO** | **DEFECT (P1)**: Unprotected. Unauthenticated users can read faculty names, departments, and duty limits. |
| `scheduling_runs` | **NO** | **DEFECT (P2)**: Unprotected. Unpublished draft runs, soft scores, and run parameters visible to public. |
| `schedule_conflicts` | **NO** | **DEFECT (P2)**: Unprotected. Internal conflict logs exposed publicly. |

### RLS Policy Analysis:
- The existing policy for `scheduled_exams` correctly prevents draft timetables from being exposed:
  ```sql
  CREATE POLICY "Public read access for scheduled exams under published active schedules" 
  ON scheduled_exams FOR SELECT USING (
      EXISTS (
          SELECT 1 FROM published_schedules ps 
          WHERE ps.run_id = scheduled_exams.run_id AND ps.is_active = TRUE
      )
  );
  ```
- **Finding**: While published schedule protection is sound, RLS must be enabled on all 11 tables before connecting to Supabase in production, with restrictive policies added for student and faculty data.

---

## 6. Actual Test Results & Build Status

### 6.1 Backend Automated Tests
- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  backend/.venv/Scripts/pytest -v backend/tests/
  ```
- **Execution Date**: 2026-10-16
- **Results**: **14 PASSED, 0 FAILED, 0 SKIPPED** (Execution time: 0.41s)
- **Detailed Test Breakdown**:
  1. `test_conflict_graph_backlog_edges`: **PASS** (Verifies cross-semester conflict edges)
  2. `test_welsh_powell_produces_no_student_clashes`: **PASS** (0 clashes verified)
  3. `test_backtracking_solver_correctness`: **PASS** (Optimal room & faculty assignment verified)
  4. `test_algorithm_benchmark_comparison`: **PASS** (All 3 algorithms benchmarked side-by-side)
  5. `test_health_check`: **PASS** (Health and status reporting verified)
  6. `test_data_summary`: **PASS** (Verified counts: 15 rooms, 10 slots, 20 faculty, 24 subjects, 355 students)
  7. `test_table_data_endpoint`: **PASS** (Raw table data retrieval verified)
  8. `test_validation_endpoint`: **PASS** (JSON readiness score report verified)
  9. `test_schedule_generation_and_publishing`: **PASS** (Schedule generation and atomic publishing verified)
  10. `test_student_and_faculty_mobile_views`: **PASS** (Student and faculty personalized timetable endpoints verified)
  11. `test_sqlite_normal_dataset_readiness`: **PASS** (Score 100/100 on clean baseline)
  12. `test_corrupted_input_rejection`: **PASS** (Rejects duplicates, negative counts, invalid slots)
  13. `test_lab_bottleneck_detection`: **PASS** (Detects lab bottleneck in slot D1-M)
  14. `test_capacity_overflow_detection`: **PASS** (Detects 650-student course exceeding room capacity)
- **Warnings**: 1 warning (`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`). Non-blocking.

### 6.2 Frontend Production Build
- **Command**:
  ```powershell
  npm --prefix frontend run build
  ```
- **Result**: **SUCCESS** (Compiled in 427ms via Vite v8.3.4 and TypeScript `tsc -b`)
- **Bundle Output**:
  - `dist/index.html`: 0.84 kB (gzip: 0.46 kB)
  - `dist/assets/index-DHf3wcrq.css`: 19.48 kB (gzip: 4.58 kB)
  - `dist/assets/index-DuAFnLhN.js`: 266.22 kB (gzip: 78.40 kB)
- **Errors**: 0 compilation errors.

---

## 7. End-to-End Application Wiring Inspection

| Component Link | Actual Implementation Path | Wiring Status | Audit Notes |
| :--- | :--- | :---: | :--- |
| **Synthetic Generation $\rightarrow$ DB** | `seed_generator.py` $\rightarrow$ `examopt.db` | **PASS** | Populates SQLite database with 100% relational integrity. |
| **Data Validation $\rightarrow$ API** | `validator.py` $\rightarrow$ `main.py` (`POST /api/data/validate`) | **PASS** | Direct function call; returns structured quality report. |
| **Backend API $\rightarrow$ Algorithms** | `main.py` $\rightarrow$ `TimetableOptimizerService` | **PASS** | Endpoints trigger First-Fit, Welsh-Powell, or Backtracking. |
| **Algorithms $\rightarrow$ Persistence** | `main.py` $\rightarrow$ `scheduling_runs`, `scheduled_exams` | **PASS** | Unique `run_id` generated; allocations persisted in SQLite. |
| **Persistence $\rightarrow$ Publication** | `main.py` (`POST /api/v1/schedules/{run_id}/publish`) | **PASS** | Atomic version increment; rejects runs with hard conflicts. |
| **Publication $\rightarrow$ Student App** | `main.py` (`GET /api/v1/timetable/student?roll_no=...`) | **PASS** | Queries active publication and filters student enrollments. |
| **Publication $\rightarrow$ Faculty Portal** | `main.py` (`GET /api/v1/timetable/faculty?faculty_id=...`)| **PASS** | Queries active publication and filters faculty duties. |
| **Frontend Client $\rightarrow$ Backend** | `frontend/src/services/api.ts` $\rightarrow$ `http://localhost:8000` | **PASS** | Typed fetch functions wired to every backend route. |
| **Dashboard Metrics** | `App.tsx` $\leftarrow$ `GET /api/data/summary` | **PASS** | **Live Data**. Metrics come from real SQLite SQL count queries. |
| **Mobile PWA Integration** | `manifest.json`, responsive drawer, student lookup | **PASS** | Tested and verified responsive on mobile viewports. |
| **Cloud Database Synchronization** | `main.py` $\rightarrow$ Supabase PostgreSQL | **FAIL** | **Not connected**. Backend queries SQLite only. |

---

## 8. Security and Repository Hygiene Findings

1. **Secret Leak Inspection**:
   - Scanned all Git commits, logs, and workspace files for `.env`, JWT tokens (`eyJ...`), API secrets, and service-role keys.
   - **Finding**: **Zero secrets detected in repository**.
2. **Configuration Templates**:
   - `.env.example` contains sanitized placeholders (`https://your-project-ref.supabase.co`, `your-publishable-anon-key`).
3. **Ignored Artifacts**:
   - `.gitignore` properly excludes `.env`, `*.db`, `node_modules/`, `.venv/`, `dist/`.

---

## 9. Prioritized Defects & Gaps

| ID | Priority | Module | Description | Recommended Remediation |
| :--- | :---: | :--- | :--- | :--- |
| **DEF-01** | **P1 (High)** | Supabase Migration | 6 tables lack RLS activation (`student_enrollments`, `faculty`, `student_subject_enrollments`, etc.). | Add `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` and authenticated-only / role-based policies for all 6 tables. |
| **DEF-02** | **P1 (High)** | Backend Architecture | Backend lacks Supabase PostgreSQL repository/client adapter; only connects to local SQLite. | Implement a database repository layer supporting Supabase PostgreSQL alongside SQLite fallback. |
| **DEF-03** | **P2 (Med)** | Supabase Migration | Missing index on `student_enrollments(group_id)` in `20261016000000_create_examopt_schema.sql`. | Add `CREATE INDEX idx_pg_student_enrollments_group ON student_enrollments(group_id);` to migration. |
| **DEF-04** | **P3 (Low)** | Backend Dependencies | Starlette testclient warning regarding `httpx` in test suite. | Update testclient initialization or upgrade to `httpx2` when compatible. |

---

## 10. Exact Recommended Next Task

**Task 2: Supabase Security Hardening & Dual-Database Repository Layer**
1. Update `supabase/migrations/` to enable RLS across all 11 tables and enforce role-based access so unauthenticated users cannot read student or faculty records.
2. Add the missing `group_id` index to the PostgreSQL migration.
3. Implement a repository abstraction in `backend/app/database/` supporting both local SQLite (offline development) and Supabase PostgreSQL (cloud operations), preserving all existing working functionality.
