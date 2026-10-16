# ExamOpt — Implementation Status & Forensic Verification Ledger

**Project**: ExamOpt (Problem Statement C10: Intelligent Examination Timetable Optimization System)  
**Institution**: GLA University Context (CSED Block AB-XI, BCA / BCA-DS / MCA Programs)  
**Audit Phase**: Task 1 Forensic Audit and Verification  
**Last Updated**: 2026-10-16  

---

## 1. Audit Verification Matrix

Statuses:
- **PASS**: Directly verified via runtime test or programmatic assertion.
- **FAIL**: Verified defect or missing integration.
- **BLOCKED**: Could not verify due to a specific missing prerequisite.
- **NOT TESTED**: Intentionally not attempted.

| Module / Component | Audit Status | Verified Runtime Evidence | Cloud Status | Defect Reference | Notes |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **Workspace & Tooling** | **PASS** | Python 3.11 (.venv), Node v24.2.0, Vite v8.3.4 | N/A | None | Toolchain and dependencies fully operational |
| **SQLite Schema (`backend/schema.sql`)** | **PASS** | 11 tables, PKs, FKs, CHECK constraints, indexes | N/A | None | Enforces `PRAGMA foreign_keys = ON;` |
| **Supabase PG Migration** | **FAIL** | DDL parsed; table schemas match SQLite | Incomplete RLS | **DEF-01, DEF-03** | 6 tables lack RLS; missing `group_id` index |
| **Deterministic Generator (`seed_generator.py`)** | **PASS** | `seed=42` produces identical row counts and IDs | N/A | None | 15 rooms, 10 slots, 20 faculty, 24 subjects, 8 groups, 355 students, 1735 enrollments |
| **Data Quality Validation (`validator.py`)** | **PASS** | Clean score 100/100; catches all 4 error classes | N/A | None | Correctly flags `LAB_BOTTLENECK`, `CAPACITY_OVERFLOW`, and syntax corruption |
| **Synthetic Fixtures (`backend/sample_datasets/`)** | **PASS** | Clean fixtures isolated from 3 malformed edge cases | N/A | None | Mathematical enrollment consistency 100% |
| **Conflict Graph & Backlog Edges** | **PASS** | 70 backlog students (50 cross-sem + 20 bridge) | N/A | None | Confirmed conflict edges across cohorts |
| **Scheduling Algorithms (A, B, C)** | **PASS** | First-Fit, Welsh–Powell, MRV Backtracking tested | N/A | None | 24/24 scheduled with **0 hard conflicts** |
| **FastAPI Backend Server (`backend/main.py`)** | **PASS** | Unified server, Phase 1 `/api/data/*`, `/api/v1/*` | N/A | None | Resolves active published timetable, student/faculty filters |
| **Web Dashboard (React + Vite + Tailwind)** | **PASS** | Vite production build passed (427ms) | N/A | None | Interactive admin overview, timetable grid, validation panel, benchmark table |
| **Mobile / PWA View** | **PASS** | `manifest.json`, responsive student/faculty lookup | N/A | None | Direct lookup by Roll Number / Faculty ID |
| **Cloud Database Integration** | **FAIL** | Backend queries SQLite only (`examopt.db`) | Not Connected | **DEF-02** | No Supabase client/adapter in `main.py` |
| **Repository Hygiene & Secret Scan** | **PASS** | 0 secrets or real `.env` committed in git history | N/A | None | `.gitignore` and `.env.example` verified |

---

## 2. Automated Test Suite Results

- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  backend/.venv/Scripts/pytest -v backend/tests/
  ```
- **Execution Date**: 2026-10-16
- **Results**: **14 PASSED, 0 FAILED, 0 SKIPPED** (Execution time: 0.41s)
  1. `test_conflict_graph_backlog_edges`: **PASS** (Verifies cross-semester conflict edges)
  2. `test_welsh_powell_produces_no_student_clashes`: **PASS** (0 student clashes guaranteed)
  3. `test_backtracking_solver_correctness`: **PASS** (Optimal room & faculty assignment with MRV & forward checking)
  4. `test_algorithm_benchmark_comparison`: **PASS** (Side-by-side execution of all 3 algorithms)
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

---

## 3. Production Build & Server Status

- **Frontend Production Build**: Vite compiled in 427ms (`dist/index.html`, `dist/assets/`).
- **Live Server**: Uvicorn running on `http://0.0.0.0:8000`:
  - Web & Mobile PWA App: `http://localhost:8000/`
  - Interactive API Docs: `http://localhost:8000/docs`
  - Health Endpoint: `http://localhost:8000/health`
- **Benchmark Evaluation Verified (0 Hard Conflicts on 24 Exams)**:
  - First-Fit Baseline: Soft Score = 76.70 (0 hard conflicts, 24/24 scheduled, 10 slots utilized)
  - Welsh–Powell Coloring: Soft Score = 77.05 (0 hard conflicts, 24/24 scheduled, 10 slots utilized)
  - MRV Backtracking: Soft Score = 76.88 (0 hard conflicts, 24/24 scheduled, 10 slots utilized)

---

## 4. Prioritized Defect Register (Identified in Task 1 Audit)

| ID | Priority | Module | Description | Remediation Plan |
| :--- | :---: | :--- | :--- | :--- |
| **DEF-01** | **P1 (High)** | Supabase Migration | 6 tables lack RLS activation (`student_enrollments`, `faculty`, `student_subject_enrollments`, etc.). | Add `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` and authenticated-only / role-based policies for all 6 tables. |
| **DEF-02** | **P1 (High)** | Backend Architecture | Backend lacks Supabase PostgreSQL repository/client adapter; only connects to local SQLite. | Implement a database repository layer supporting Supabase PostgreSQL alongside SQLite fallback. |
| **DEF-03** | **P2 (Med)** | Supabase Migration | Missing index on `student_enrollments(group_id)` in `20261016000000_create_examopt_schema.sql`. | Add `CREATE INDEX idx_pg_student_enrollments_group ON student_enrollments(group_id);` to migration. |
| **DEF-04** | **P3 (Low)** | Backend Dependencies | Starlette testclient warning regarding `httpx` in test suite. | Update testclient initialization or upgrade to `httpx2` when compatible. |

---

## 5. Next Planned Action

**Task 2: Supabase Security Hardening & Dual-Database Repository Layer**
1. Harden `supabase/migrations/20261016000000_create_examopt_schema.sql` with RLS on all 11 tables and add missing index.
2. Build database repository abstraction in `backend/app/database/` supporting both SQLite (offline) and Supabase (cloud).
3. Verify dual-mode test suite without breaking any Phase 1 functionality.

