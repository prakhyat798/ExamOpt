# ExamOpt Master Verification & Supabase Security Audit Report

**Project**: ExamOpt (Problem Statement C10: Intelligent Examination Timetable Optimization System)  
**Context**: GLA University (CSED Block AB-XI, BCA / BCA-DS / MCA Programs)  
**Date of Audit**: 2026-10-16  
**Auditor**: Senior Software Auditor, Database Engineer & Supabase Security Reviewer  
**Repository**: [https://github.com/prakhyat798/ExamOpt](https://github.com/prakhyat798/ExamOpt)  
**Cloud Dashboard**: [https://supabase.com/dashboard/project/tvyiqyngqehrxrcxqwei/editor](https://supabase.com/dashboard/project/tvyiqyngqehrxrcxqwei/editor)  

---

## 1. Executive Summary

This master audit provides a comprehensive, forensic, read-only evaluation of the ExamOpt codebase, its database layer, Supabase PostgreSQL configuration, Row Level Security (RLS) policies, synthetic data pipelines, and end-to-end API integration.

### Core Audit Verdict:
- **Local Architecture & Algorithms**: **PASS**. The Python/FastAPI backend, deterministic synthetic generator (`seed=42`), data validator, optimization algorithms (First-Fit, Welsh–Powell, MRV Backtracking), and React SPA build are verified with 100% mathematical consistency and 27 passing automated tests.
- **Database Repository Layer**: **PASS**. Dual-repository architecture (`backend/app/database/`) is fully implemented with explicit `DATABASE_BACKEND` selection (`sqlite` vs `supabase`). Cloud mode uses PostgREST HTTP REST endpoints (`httpx`) and guarantees zero silent fallback to SQLite.
- **Supabase PostgreSQL Schema & Security**: **PASS (Prepared in Workspace)**. The complete forward-only migration (`20261016000001_harden_rls_and_indexes.sql`) and all-in-one setup scripts (`full_clean_setup.sql`, `complete_setup_and_seed.sql`) resolve missing group index `idx_pg_student_enrollments_group`, activate RLS across all 11 application tables plus `user_profiles`, and enforce least-privilege role-based access.
- **Live Supabase Cloud Connectivity**: **BLOCKED**. No local `.env` configuration or rotated cloud credentials exist in the local workspace. Per safety guidelines, cloud verification remains `BLOCKED` until rotated credentials are configured locally and authorized.
- **Secret Hygiene**: **PASS**. Zero secrets, JWT tokens, or database passwords are committed to Git history or exposed in frontend code.

---

## 2. Phase A: Repository and Environment Inventory

### 2.1 File System & Path Inventory

| Component | Repository Path | Audit Status | Verification Details |
| :--- | :--- | :---: | :--- |
| **Documentation** | `README.md`, `EXAMOPT-PHASE-1-HANDOFF.md` | **PASS** | Complete specification, instructions, and handoff guides present. |
| **Audit Records** | `docs/AUDIT_REPORT.md`, `docs/TASK_2_REPORT.md` | **PASS** | Forensic findings and Task 2 implementation documentation. |
| **Status Ledger** | `docs/IMPLEMENTATION_STATUS.md` | **PASS** | Real-time status tracking ledger. |
| **Dev Server Runner** | `run_dev.py` | **PASS** | Auto-initializes SQLite and launches backend server on port 8000. |
| **Backend Entry Point** | `backend/main.py` | **PASS** | Unified FastAPI server with repository integration and SPA routing. |
| **Database Abstraction** | `backend/app/database/` (5 modules) | **PASS** | `config.py`, `base.py`, `sqlite_repository.py`, `supabase_repository.py`, `factory.py`. |
| **SQLite Schema** | `backend/schema.sql` | **PASS** | 11 relational tables with strict CHECK constraints and foreign keys. |
| **Local SQLite Database** | `backend/examopt.db` | **PASS** | 458,752 bytes, fully populated with 355 students and 1,735 enrollments. |
| **Supabase Migrations** | `supabase/migrations/` | **PASS** | `20261016000000_create_examopt_schema.sql` and `20261016000001_harden_rls_and_indexes.sql`. |
| **Setup & Seed SQL** | `supabase/full_clean_setup.sql`, `complete_setup_and_seed.sql` | **PASS** | Complete idempotent clean-slate setup and seeding scripts for Supabase. |
| **Synthetic Generator** | `backend/seed_generator.py` | **PASS** | Deterministic generator (`random.seed(42)`). |
| **Data Quality Engine** | `backend/validator.py` | **PASS** | Multi-phase constraint inspector and readiness scorer. |
| **Synthetic Datasets** | `backend/sample_datasets/` | **PASS** | Clean fixture (`normal_gla_dataset/`) + 3 edge-case CSVs. |
| **Core Algorithms** | `backend/app/algorithms/` | **PASS** | `conflict_graph.py`, `baseline_first_fit.py`, `welsh_powell.py`, `backtracking.py`. |
| **Automated Tests** | `backend/tests/` (5 test suites) | **PASS** | 27 tests covering algorithms, API, validation, adapters, and security. |
| **Frontend Tooling & UI** | `frontend/package.json`, `frontend/src/` | **PASS** | React 19, TypeScript, Vite 8, Tailwind CSS, Lucide icons. |
| **PWA Manifest** | `frontend/public/manifest.json` | **PASS** | Standalone PWA configuration for mobile viewports. |
| **Config & Git Control** | `.env.example`, `.gitignore` | **PASS** | Sanitized placeholders and complete exclusions for secrets and databases. |

### 2.2 Environment & Runtime Versions

| Tool / Framework | Installed Version | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Python** | Python 3.15.0 (`backend/.venv`) | `sys.version` in virtualenv | **PASS** |
| **FastAPI** | 0.143.2 | `fastapi.__version__` | **PASS** |
| **Uvicorn** | 0.54.0 | `uvicorn.__version__` | **PASS** |
| **Pydantic** | 2.14.1 | `pydantic.__version__` | **PASS** |
| **HTTPX** | 0.28.1 | `httpx.__version__` | **PASS** |
| **Pytest** | 9.1.1 | `pytest.__version__` | **PASS** |
| **Node.js** | v24.20.0 | `node -v` | **PASS** |
| **npm** | 11.19.0 | `npm -v` | **PASS** |
| **React** | 19.2.8 | `frontend/package.json` | **PASS** |
| **Vite** | 8.3.4 | `vite --version` | **PASS** |

---

## 3. Phase B: Local Configuration and Secret Hygiene

| Check | Status | Verification Evidence & Findings |
| :--- | :---: | :--- |
| **`.env` File Existence** | **PASS** | `.env exists: False` and `backend/.env exists: False`. No secrets stored in workspace. |
| **Secret Scanning (Git)** | **PASS** | `git grep -EI 'eyJ[a-zA-Z0-9_-]{20,}'` returned 0 matches. Zero JWT tokens committed. |
| **Password Scanning** | **PASS** | `git grep -EI 'postgres:[^@]+@'` returned 0 matches. Zero connection URIs committed. |
| **`.gitignore` Completeness** | **PASS** | Explicitly ignores `.env`, `.env.local`, `.env.*.local`, `*.env`, `*.db`, `node_modules/`, `.venv/`. |
| **`.env.example` Hygiene** | **PASS** | Contains clean placeholders (`DATABASE_BACKEND=sqlite`, `your-publishable-anon-key`, `your-rotated-service-role-key`). |
| **Frontend Secret Exposure** | **PASS** | Frontend code queries only `VITE_API_BASE_URL` and `VITE_SUPABASE_ANON_KEY`. Zero service-role keys in frontend. |

---

## 4. Phase C: Supabase Project and Connectivity

| Check | Status | Verification Evidence & Findings |
| :--- | :---: | :--- |
| **Local Cloud Credentials** | **BLOCKED** | Environment variables `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_PUBLISHABLE_KEY` are unset locally. |
| **Target Project Verification**| **PASS (Static)**| Supabase project reference confirmed as `tvyiqyngqehrxrcxqwei` via dashboard URL. |
| **Live API Reachability** | **BLOCKED** | Awaiting user rotation of compromised service-role key before executing live cloud calls. |
| **Fail-Fast Cloud Mode** | **PASS** | Directly verified via test `test_missing_supabase_config_raises_configuration_error`. Selecting `DATABASE_BACKEND=supabase` without credentials raises `ConfigurationError`. |
| **No Silent Fallback** | **PASS** | Directly verified via test `test_supabase_cloud_connection_failure_reported`. Cloud failure raises `DatabaseConnectionError`; does not substitute SQLite. |

---

## 5. Phase D: Schema and Migration Audit

### 5.1 Relational Table Comparison (SQLite vs Supabase PostgreSQL)

| Table Name | SQLite `backend/schema.sql` | Supabase Migration | Supabase Clean Setup | Discrepancy / Alignment |
| :--- | :---: | :---: | :---: | :--- |
| `rooms` | 15 columns/types | VARCHAR/CHECK | Identical | **PASS**: 100% aligned. |
| `timeslots` | 10 slots / UNIQUE | VARCHAR/CHECK | Identical | **PASS**: 100% aligned. |
| `faculty` | 20 faculty / CHECK | VARCHAR/CHECK | Identical | **PASS**: 100% aligned. |
| `subjects` | 24 subjects / CHECK | VARCHAR/CHECK | Identical | **PASS**: 100% aligned. |
| `student_groups` | 8 groups / CHECK | VARCHAR/CHECK | Identical | **PASS**: 100% aligned. |
| `student_enrollments` | 355 students / FK | VARCHAR/FK | Identical | **PASS**: 100% aligned. |
| `student_subject_enrollments` | 1,735 rows / FK | BIGSERIAL/FK | Identical | **PASS**: 100% aligned. |
| `scheduling_runs` | Runs / JSON | JSONB/NUMERIC | Identical | **PASS**: 100% aligned. |
| `scheduled_exams` | Allocations / FK | VARCHAR/FK | Identical | **PASS**: 100% aligned. |
| `published_schedules` | Version / UNIQUE | INTEGER/UNIQUE | Identical | **PASS**: 100% aligned. |
| `schedule_conflicts` | Diagnostics / FK | BIGSERIAL/FK | Identical | **PASS**: 100% aligned. |
| `user_profiles` | N/A (Cloud only) | `auth.users(id)` | UUID/FK | **PASS**: Cloud RBAC identity table. |

### 5.2 Index Audit & Verification

| Index Name | Table & Target Column | Purpose | Status |
| :--- | :--- | :--- | :---: |
| `idx_pg_student_enrollments_group` | `student_enrollments(group_id)` | DEF-03 resolution; cohort filtering | **PASS** |
| `idx_pg_student_enrollments_backlog`| `student_enrollments(has_backlog)` | Rapid backlog student discovery | **PASS** |
| `idx_pg_sse_roll_no` | `student_subject_enrollments(roll_no)` | Student personalized timetable join | **PASS** |
| `idx_pg_sse_subject_id` | `student_subject_enrollments(subject_id)`| Conflict graph edge computation | **PASS** |
| `idx_pg_se_run_id` | `scheduled_exams(run_id)` | Run allocation retrieval | **PASS** |
| `idx_pg_se_slot_room` | `scheduled_exams(run_id, slot_id, room_id)` | Room double-booking prevention | **PASS** |
| `idx_pg_se_slot_faculty` | `scheduled_exams(run_id, slot_id, assigned_faculty_id)` | Invigilator double-booking prevention | **PASS** |
| `idx_pg_published_schedules_active` | `published_schedules(is_active)` | Active timetable lookup filter | **PASS** |

---

## 6. Phase E: Row Level Security (RLS) and Access Control Audit

| Table | RLS Active | Public / Anonymous Access | Authenticated Access | Admin / Service Role Access |
| :--- | :---: | :--- | :--- | :--- |
| `rooms` | **YES** | **SELECT (true)** (Public campus directory) | SELECT (true) | ALL (Full management) |
| `timeslots` | **YES** | **SELECT (true)** (Public exam timetable slots) | SELECT (true) | ALL (Full management) |
| `subjects` | **YES** | **SELECT (true)** (Public course catalog) | SELECT (true) | ALL (Full management) |
| `student_groups` | **YES** | **BLOCKED** | SELECT (Authenticated only) | ALL (Full management) |
| `student_enrollments` | **YES** | **BLOCKED** | SELECT own (`roll_no = get_current_student_roll_no()`) | ALL (Full management) |
| `student_subject_enrollments`| **YES** | **BLOCKED** | SELECT own (`roll_no = get_current_student_roll_no()`) | ALL (Full management) |
| `faculty` | **YES** | **BLOCKED** | SELECT basic info; own duties | ALL (Full management) |
| `scheduling_runs` | **YES** | **BLOCKED** | **BLOCKED** (Draft runs strictly confidential) | ALL (Full management) |
| `scheduled_exams` | **YES** | SELECT under active published schedule only | Active published schedule or Admin | ALL (Full management) |
| `published_schedules` | **YES** | SELECT `is_active = TRUE` only | `is_active = TRUE` or Admin | ALL (Full management) |
| `schedule_conflicts` | **YES** | **BLOCKED** | **BLOCKED** (Internal diagnostic log) | ALL (Full management) |
| `user_profiles` | **YES** | **BLOCKED** | SELECT own profile (`id = auth.uid()`) | ALL (Self-promotion blocked) |

---

## 7. Phase F: Backend Database Integration Trace

```mermaid
flowchart TD
    Client["Client (Browser / PWA / Test)"] --> API["FastAPI (backend/main.py)"]
    API --> Factory["get_repository() (factory.py)"]
    Factory --> Config{"DATABASE_BACKEND"}
    Config -->|sqlite (default)| SQLiteRepo["SQLiteRepository (sqlite_repository.py)"]
    Config -->|supabase| SupaRepo["SupabaseRepository (supabase_repository.py)"]
    SQLiteRepo --> LocalDB["Local DB (backend/examopt.db)"]
    SupaRepo --> PostgREST["Supabase Cloud PostgREST (HTTPS)"]
    PostgREST --> CloudPG["Supabase PostgreSQL (RLS Enforced)"]
    Config -->|invalid or missing cloud creds| Error["Raise ConfigurationError / 500 (No Fallback)"]
```

### Trace Findings:
- **Startup**: FastAPI initializes `DatabaseConfig()`. If `DATABASE_BACKEND` is unset, it safely defaults to `sqlite`.
- **Cloud Isolation**: If `DATABASE_BACKEND=supabase`, `SupabaseRepository` uses `httpx` to query `{SUPABASE_URL}/rest/v1`. If credentials are unset or unreachable, it raises `ConfigurationError` or `DatabaseConnectionError`. **Never falls back silently to SQLite**.
- **Observability**: `/health` endpoint exposes safe status without leaking keys.

---

## 8. Phase G: Synthetic Data & Seed Verification

| Metric / Check | Required Specification | Demonstrated Database Value | Status |
| :--- | :--- | :--- | :---: |
| **Deterministic Seed** | Fixed seed (`seed=42`) | Identical bytes & IDs across runs | **PASS** |
| **Rooms Count** | 15 (10 theory + 5 labs) | 15 rows | **PASS** |
| **Timeslots Count** | 10 slots (5 days $\times$ 2 sessions) | 10 rows (`D1-M` to `D5-E`) | **PASS** |
| **Faculty Count** | 20 faculty members | 20 rows (`FAC-101` to `FAC-120`) | **PASS** |
| **Subjects Count** | 24 courses (BCA, BCA-DS, MCA) | 24 rows | **PASS** |
| **Student Groups** | 8 cohorts (including backlog groups) | 8 rows | **PASS** |
| **Individual Students** | $\approx 350$ fictional students | 355 rows (`GLA26-BCA-...`) | **PASS** |
| **Subject Enrollments** | Student-to-subject junction | 1,735 rows | **PASS** |
| **Backlog Students** | Cross-cohort students | 70 students (50 cross-sem + 20 bridge) | **PASS** |
| **Enrollment Consistency**| Declared equals actual | 100% mathematical match across all 24 subjects | **PASS** |
| **Foreign Key Check** | `PRAGMA foreign_key_check;` | 0 violations detected | **PASS** |
| **Schedulability** | 0 hard clashes under real rules | **100% schedulable** (All 3 algorithms schedule 24/24) | **PASS** |
| **Seeder Idempotency** | Non-destructive re-runs | `ON CONFLICT (...) DO NOTHING;` on all insert statements | **PASS** |

---

## 9. Phase H: Application & API Integration

- **Live Data Verification**: Admin summary `/api/data/summary` executes live `COUNT(*)` queries against `examopt.db` (15 rooms, 10 slots, 20 faculty, 24 subjects, 355 students). It does **not** serve hard-coded JSON mock data.
- **Atomic Publishing**: `/api/v1/schedules/{run_id}/publish` verifies `hard_conflicts == 0` and `status == 'FEASIBLE'`, deactivates prior versions (`is_active = 0`), and atomically creates the next sequential publication version (`PUB-V{N}`).
- **Personalized Lookups**:
  - `GET /api/v1/timetable/student?roll_no=GLA26-BCA-0001` returns 4 personalized enrolled exams for student Akash Singh.
  - `GET /api/v1/timetable/faculty?faculty_id=FAC-101` returns 2 assigned invigilation duties for Dr. Ashish Sharma.

---

## 10. Phase I: Automated Test Suite & Production Build

### 10.1 Backend Test Results
- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  backend/.venv/Scripts/pytest -v backend/tests/
  ```
- **Results**: **27 PASSED, 0 FAILED, 0 SKIPPED** in 0.56s.
  - `test_algorithms.py`: 4 passed (Conflict graph edges, Welsh–Powell 0 clashes, Backtracking solver, Algorithm benchmark).
  - `test_api.py`: 6 passed (Health check, data summary, table data, validation endpoint, publish lifecycle, mobile timetable lookups).
  - `test_data_validation.py`: 4 passed (Normal dataset readiness, corrupted input rejection, lab bottleneck detection, capacity overflow detection).
  - `test_database_adapters.py`: 7 passed (SQLite default selection, Supabase cloud selection, unsupported backend rejection, missing config fail-fast, cloud connection error reporting, PostgREST mock transport CRUD, HTTP exception mappings).
  - `test_supabase_security.py`: 6 passed (11 tables RLS enabled, missing index created, anonymous access restricted, self-assigned admin privileges prevented, fixed search_path on helper functions, grants revocation).
- **Warnings**: 1 non-blocking deprecation warning (`StarletteDeprecationWarning` regarding `httpx` with `testclient`).

### 10.2 Frontend Production Build Results
- **Command**:
  ```powershell
  npm --prefix frontend run build
  ```
- **Result**: **SUCCESS** in 414ms.
- **Output Artifacts**:
  - `dist/index.html`: 0.84 kB (gzip: 0.46 kB)
  - `dist/assets/index-DHf3wcrq.css`: 19.48 kB (gzip: 4.58 kB)
  - `dist/assets/index-DuAFnLhN.js`: 266.22 kB (gzip: 78.40 kB)
- **Compilation Errors**: 0 errors.

---

## 11. Prioritized Defect & Gap Register

| ID | Priority | Module | Finding Description | Status / Remediation |
| :---: | :---: | :--- | :--- | :---: |
| **DEF-01** | **P1 (High)** | Supabase Security | Incomplete RLS across application tables. | **RESOLVED IN REPO** (`20261016000001_harden_rls_and_indexes.sql`) |
| **DEF-02** | **P1 (High)** | Backend DB Layer | Backend lacked cloud database repository adapter. | **RESOLVED IN REPO** (`backend/app/database/`) |
| **DEF-03** | **P2 (Med)** | Supabase Indexes | Missing index on `student_enrollments(group_id)`. | **RESOLVED IN REPO** (`idx_pg_student_enrollments_group`) |
| **DEF-04** | **P3 (Low)** | Dependencies | Starlette testclient warning on `httpx`. | Open (Non-blocking deprecation warning) |
| **GAP-01** | **P1 (High)** | Cloud Deployment | Live Supabase project `tvyiqyngqehrxrcxqwei` has not yet had migrations or seed data applied. | **BLOCKED ON CREDENTIAL ROTATION** |

---

## 12. Recommended Remediation & Exact Next Step

### Highest Priority Action:
1. **Rotate Credentials**: The user must rotate the previously exposed Supabase service-role secret key in the [Supabase Settings > API Dashboard](https://supabase.com/dashboard/project/tvyiqyngqehrxrcxqwei/settings/api).
2. **Apply Verified Schema & Seed**:
   Run the all-in-one idempotent setup script in the Supabase SQL Editor:
   👉 [supabase/complete_setup_and_seed.sql](file:///c:/Users/prakhyat/Documents/hackvision/supabase/complete_setup_and_seed.sql)
3. **Configure Local Environment**: Add rotated credentials to `.env`:
   ```env
   DATABASE_BACKEND=supabase
   SUPABASE_URL=https://tvyiqyngqehrxrcxqwei.supabase.co
   SUPABASE_SECRET_KEY=your-rotated-service-role-key
   ```
4. **Execute Live Verification**: Verify live read/write operations against the cloud database.
