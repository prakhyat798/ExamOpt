# ExamOpt — Task 2 Implementation & Verification Report
**Task**: Supabase Security Hardening, Index Creation & Cloud Database Integration  
**Date**: 2026-10-16  
**Project**: [https://github.com/prakhyat798/ExamOpt](https://github.com/prakhyat798/ExamOpt)  
**Author**: Systems & Database Lead Agent  

---

## 1. Executive Summary

Task 2 resolved the three critical defects identified in `docs/AUDIT_REPORT.md` while preserving 100% of the verified local functionality and passing automated test suites:
1. **DEF-01 (Row Level Security)**: Created forward-only migration `20261016000001_harden_rls_and_indexes.sql` enabling RLS across all 11 application tables and establishing least-privilege, role-based access policies with non-recursive security helper functions.
2. **DEF-03 (Missing Index)**: Added the missing performance index `idx_pg_student_enrollments_group` on `student_enrollments(group_id)` to the PostgreSQL migration.
3. **DEF-02 (Cloud Database Integration)**: Implemented a clean, modular repository abstraction in `backend/app/database/` supporting both local SQLite and remote Supabase PostgREST cloud operations. Cloud failures are surfaced transparently and never silently fall back to SQLite.

All 14 baseline Phase 1 tests continue to pass without regression, 13 new adapter and security tests have been added (27 total tests passing), and the React frontend production build compiles cleanly in 406ms.

---

## 2. Files Changed and Created

| File Path | Nature of Change | Description |
| :--- | :--- | :--- |
| `supabase/migrations/20261016000001_harden_rls_and_indexes.sql` | **NEW** | Forward-only migration adding `group_id` index, enabling RLS on all 11 tables, creating `user_profiles`, and defining least-privilege policies. |
| `backend/app/database/__init__.py` | **NEW** | Package entry point exporting configuration, exceptions, repositories, and factory. |
| `backend/app/database/exceptions.py` | **NEW** | Typed exceptions: `ConfigurationError`, `DatabaseConnectionError`, `DatabaseAuthenticationError`, `EntityNotFoundError`, `DatabaseIntegrityError`. |
| `backend/app/database/config.py` | **NEW** | Backend selector (`DatabaseBackend.SQLITE` vs `DatabaseBackend.SUPABASE`), credential validation, and secret-free status reporting. |
| `backend/app/database/base.py` | **NEW** | Abstract `DatabaseRepository` interface defining the unified data access contract. |
| `backend/app/database/sqlite_repository.py` | **NEW** | SQLite repository preserving exact local development, transaction, and test behavior. |
| `backend/app/database/supabase_repository.py` | **NEW** | PostgREST HTTP REST cloud repository using `httpx` with parameterization, error mapping, and user token support. |
| `backend/app/database/factory.py` | **NEW** | Instantiation factory and singleton cache with fail-fast validation. |
| `backend/main.py` | **MODIFIED** | Refactored to delegate data access to `get_repository()`; updated `/health` to report safe backend status. |
| `backend/tests/test_database_adapters.py` | **NEW** | 7 automated tests covering adapter selection, fail-fast configuration, connection errors, and mocked PostgREST CRUD operations. |
| `backend/tests/test_supabase_security.py` | **NEW** | 6 automated tests statically verifying RLS activation, index creation, role-based protection, and fixed search paths. |
| `.env.example` | **MODIFIED** | Documented `DATABASE_BACKEND=sqlite` and `DATABASE_BACKEND=supabase` options with clean placeholders. |
| `docs/TASK_2_REPORT.md` | **NEW** | Comprehensive Task 2 audit and delivery record. |
| `docs/IMPLEMENTATION_STATUS.md` | **MODIFIED** | Updated with Task 2 progress, test results, and defect resolution ledger. |

---

## 3. Database Architecture & Adapter Strategy

### Strategy Choice: PostgREST HTTP API (`httpx`)
For the cloud adapter, the Supabase PostgREST REST interface (`httpx`) was selected for the following architectural reasons:
1. **RLS Enforcement**: Supabase's PostgREST server natively evaluates PostgreSQL Row Level Security for incoming requests using the `Authorization: Bearer <JWT>` header. Direct PostgreSQL connections using administrative credentials bypass RLS unless specifically configured with session roles.
2. **Zero Native C Dependencies**: Standard PostgreSQL client drivers (`psycopg2`) require compilation tools or binary wheels on Windows. `httpx` is already a core, pinned dependency in `backend/requirements.txt` and is fully installed in the project virtual environment.
3. **Fail-Fast Boundary**: PostgREST HTTP error responses (401, 403, 404, 409, 422, 500) are explicitly translated into typed Python database exceptions (`DatabaseAuthenticationError`, `DatabaseIntegrityError`, etc.), preventing silent failures.
4. **Deterministic Mocking**: Facilitates isolated unit testing using `httpx.MockTransport` without requiring a live PostgreSQL cloud connection during local test execution.

---

## 4. Configuration and Credential Handling

### Supported Settings:
- `DATABASE_BACKEND`: `sqlite` (default) or `supabase`.
- `SQLITE_DB_PATH`: Path to local SQLite file (`backend/examopt.db`).
- `SUPABASE_URL`: HTTPS URL of the Supabase project (`https://<project-ref>.supabase.co`).
- `SUPABASE_PUBLISHABLE_KEY`: Public anon key for client-scoped access.
- `SUPABASE_SECRET_KEY`: Server-side service-role key for privileged administrative operations.

### Security Guarantees:
- **No Silent Fallback**: If `DATABASE_BACKEND=supabase` is set, missing credentials or connection failures immediately raise `ConfigurationError` or `DatabaseConnectionError`. The system will **never** silently substitute SQLite data.
- **Safe Introspection**: Health endpoints (`/health` and `/api/v1/health`) return only non-sensitive boolean flags (`"is_cloud"`, `"connected"`, `"configured"`). Raw API keys, connection strings, and passwords are never exposed.
- **Git Hygiene**: `.gitignore` strictly excludes `.env`, `*.db`, and secret files. `.env.example` contains only sanitized placeholders.

---

## 5. Migration & Row Level Security Details (DEF-01 & DEF-03)

Migration file created: `supabase/migrations/20261016000001_harden_rls_and_indexes.sql`

### 5.1 Missing Index (DEF-03)
```sql
CREATE INDEX IF NOT EXISTS idx_pg_student_enrollments_group 
ON student_enrollments(group_id);
```
Also added indexes for backlog queries and active published timetables:
- `idx_pg_student_enrollments_backlog` on `student_enrollments(has_backlog)`
- `idx_pg_published_schedules_active` on `published_schedules(is_active)`

### 5.2 Identity & Role-Based Access Control (RBAC) Mapping
Created `user_profiles` table linked to Supabase `auth.users(id)`:
```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'STUDENT' CHECK (role IN ('ADMIN', 'FACULTY', 'STUDENT')),
    student_roll_no VARCHAR(50) REFERENCES student_enrollments(roll_no) ON DELETE SET NULL,
    faculty_id VARCHAR(50) REFERENCES faculty(faculty_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.3 Non-Recursive Helper Functions with Strict Search Path
Helper functions specify `SECURITY DEFINER` with `SET search_path = public, auth` to prevent search-path injection and recursive policy loops:
- `public.get_current_user_role()`: Returns `'ADMIN'`, `'FACULTY'`, or `'STUDENT'`.
- `public.get_current_student_roll_no()`: Returns linked roll number.
- `public.get_current_faculty_id()`: Returns linked faculty ID.
- `public.is_admin()`: Evaluates admin status via profile role, JWT claims, or service role.

### 5.4 RLS Activation & Policy Matrix (DEF-01)

| Table Name | RLS Enabled | Anon Read Access | Authenticated Read Access | Write Access |
| :--- | :---: | :---: | :---: | :---: |
| `rooms` | **YES** | **ALLOWED** (Public catalog) | **ALLOWED** | Admin / Service Role |
| `timeslots` | **YES** | **ALLOWED** (Public catalog) | **ALLOWED** | Admin / Service Role |
| `subjects` | **YES** | **ALLOWED** (Course catalog) | **ALLOWED** | Admin / Service Role |
| `student_groups` | **YES** | **BLOCKED** | Authenticated users only | Admin / Service Role |
| `student_enrollments` | **YES** | **BLOCKED** | Own roll number only (`roll_no = get_current_student_roll_no()`) or Admin | Admin / Service Role |
| `student_subject_enrollments` | **YES** | **BLOCKED** | Own enrollments only or Admin | Admin / Service Role |
| `faculty` | **YES** | **BLOCKED** | Authenticated users view name/dept; own record for duty limits; Admin views all | Admin / Service Role |
| `scheduling_runs` | **YES** | **BLOCKED** | **BLOCKED** (Admin only; drafts are strictly confidential) | Admin / Service Role |
| `scheduled_exams` | **YES** | Restricted to active published schedules only | Active published schedules or Admin | Admin / Service Role |
| `published_schedules` | **YES** | Restricted to `is_active = TRUE` only | `is_active = TRUE` or Admin | Admin / Service Role |
| `schedule_conflicts` | **YES** | **BLOCKED** | **BLOCKED** (Admin diagnostic log only) | Admin / Service Role |
| `user_profiles` | **YES** | **BLOCKED** | Own profile only (`id = auth.uid()`) or Admin | Admin / Service Role (self-assignment blocked) |

---

## 6. Verification Results

### 6.1 Backend Test Suite (Pytest)
- **Command**:
  ```powershell
  $env:PYTHONPATH = "backend"
  backend/.venv/Scripts/pytest -v backend/tests/
  ```
- **Results**: **27 PASSED, 0 FAILED, 0 SKIPPED** (Execution time: 0.60s)
  - Baseline Phase 1 tests (14): **PASS**
  - Database adapter & fail-fast tests (7): **PASS**
  - Supabase migration & RLS static policy tests (6): **PASS**

### 6.2 Frontend Production Build
- **Command**:
  ```powershell
  npm --prefix frontend run build
  ```
- **Result**: **SUCCESS** in 406ms (0 TypeScript errors, 0 Vite compilation warnings).

### 6.3 Test Verification Level Ledger

| Verification Scope | Verification Status | Verification Methodology |
| :--- | :---: | :--- |
| **Local SQLite Backend** | **PASS** | Direct runtime tests against `backend/examopt.db`. |
| **Backend Selector & Validation** | **PASS** | Direct runtime tests verifying config errors and fail-fast behavior. |
| **Supabase PostgREST Adapter CRUD** | **PASS** | Mocked HTTP transport (`httpx.MockTransport`) testing full CRUD cycle. |
| **Error Status Mapping** | **PASS** | Mocked HTTP transport asserting 401, 403, 404, 409, 422 exception mapping. |
| **Migration DDL & Index Syntax** | **PASS** | Static regex AST verification of migration SQL file. |
| **RLS Policy Coverage (All 11 Tables)** | **PASS** | Static SQL analysis verifying policy definitions and grants revocation. |
| **Live Supabase Cloud Connectivity** | **BLOCKED** | Awaiting rotated credentials from user before applying migrations or running cloud tests. |

---

## 7. Remaining Blockers & User Next Steps

Per strict credential security rules:
1. **Rotate Credentials**: The user must rotate the compromised Supabase service-role secret key in the [Supabase Project Dashboard](https://supabase.com/dashboard/project/tvyiqyngqehrxrcxqwei/settings/api).
2. **Local Environment Setup**: The user should add the rotated credentials to their local `.env` file (never commit to git):
   ```env
   DATABASE_BACKEND=supabase
   SUPABASE_URL=https://tvyiqyngqehrxrcxqwei.supabase.co
   SUPABASE_PUBLISHABLE_KEY=your-rotated-anon-key
   SUPABASE_SECRET_KEY=your-rotated-service-role-key
   ```
3. **Cloud Migration Authorization**: Once credentials are configured, the user can review and apply the forward migration:
   - File: `supabase/migrations/20261016000001_harden_rls_and_indexes.sql`
   - Application method: via Supabase CLI (`supabase db push`) or SQL Editor in the Supabase Dashboard.

---

## 8. Exact Recommended Next Task

**Task 3: Cloud Verification & End-to-End Live Synchronization**
1. Once the user provides authorization and rotated local credentials, execute live read-only verification against the Supabase project.
2. Seed the cloud database using `seed_generator.py` targeting Supabase.
3. Validate synchronization between the React web dashboard and cloud database.
