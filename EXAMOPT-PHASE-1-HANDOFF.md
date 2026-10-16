# ExamOpt Phase 1: Data Engineering, Database Schema & Validation Layer
## Team Handoff & Architecture Blueprint (Problem Statement C10: GLA University)

**Date:** 2026-10-16 · **Branch:** `main`  
**Team Collaboration:** 2 Developers (Backend/Optimization Engineer & Frontend/Cloud Engineer)

---

## 1. Division of Responsibility for 2 Developers

To avoid git merge conflicts and ensure efficient pair programming:

| Developer | Primary Responsibility | Owned Directories & Files | Current Status |
| :--- | :--- | :--- | :--- |
| **Developer 1 (Optimization & Backend)** | Optimization algorithms, constraint graph, heuristics, mathematical guarantees, data validator | `backend/app/algorithms/`<br>`backend/app/services/`<br>`backend/validator.py`<br>`backend/tests/` | **Phase 1 Complete** (14 automated tests passing in 0.40s) |
| **Developer 2 (Frontend & Cloud/Database)** | Web Dashboard, Mobile PWA view, API integration, Supabase cloud migration & RLS policies | `frontend/src/`<br>`frontend/tailwind.config.js`<br>`supabase/migrations/`<br>`backend/main.py` | **Phase 1 & Unified SPA Complete** |

---

## 2. Phase 1 Data Contracts & Endpoints

All endpoints are hosted on `http://localhost:8000` (FastAPI):

| Method & Route | Query / Body Params | Returns | Description |
| :--- | :--- | :--- | :--- |
| `GET /api/data/summary` | None | JSON summary object | Real-time counts of rooms, slots, faculty, subjects, groups, and backlog students |
| `GET /api/data/tables/{table}` | `?limit=500` | JSON row array | Full raw database records (`rooms`, `timeslots`, `subjects`, `faculty`, `student_groups`, `student_enrollments`) |
| `POST /api/data/validate` | `{"preset_name": "normal"}` | Validation report JSON | Inspects dataset for duplicates, negative values, FK mismatches, capacity overflows, and lab bottlenecks |
| `POST /api/data/load-preset/{name}`| Path: `normal`, `lab_bottleneck`, etc. | Validation report JSON | Switches active runtime state to demonstrate edge cases |
| `POST /api/v1/schedules/generate` | `{"algorithm": "BACKTRACKING"}` | Allocation list + metrics | Executes algorithm and saves candidate run |
| `POST /api/v1/schedules/compare` | None | 3-algorithm comparison | Side-by-side benchmark (First-Fit, Welsh-Powell, Backtracking) |
| `GET /api/v1/schedules/active-published`| None | Active timetable | Current authoritative published timetable |
| `GET /api/v1/timetable/student` | `?roll_no=GLA26-BCA-0001` | Filtered exam array | Personalized student exam schedule (date, slot, room, hall) |
| `GET /api/v1/timetable/faculty` | `?faculty_id=FAC-101` | Duty list + duty cap | Personalized invigilator assignment schedule |
| `GET /api/v1/timetable/export/csv` | `?run_id=...` (optional) | CSV File download | Downloadable timetable CSV for Excel/Office |

---

## 3. Database Schema Reference

The database models 11 relational entities in both SQLite (`backend/examopt.db`) and PostgreSQL (`supabase/migrations/`):

1. **`rooms`**: `room_id` (PK), `name`, `building`, `capacity`, `room_type` ('THEORY'/'LAB'), `unavailable_slots`.
2. **`timeslots`**: `slot_id` (PK, e.g. D1-M to D5-E), `day_number`, `exam_date`, `session`, `time_range`.
3. **`faculty`**: `faculty_id` (PK), `name`, `department`, `unavailable_slots`, `max_duties`.
4. **`subjects`**: `subject_id` (PK), `name`, `program`, `semester`, `duration_hours`, `requires_lab`, `fixed_slot`, `unavailable_slots`, `enrolled_students`.
5. **`student_groups`**: `group_id` (PK), `name`, `program`, `semester`, `is_backlog_group`, `student_count`.
6. **`student_enrollments`**: `roll_no` (PK), `student_name`, `group_id`, `enrolled_subject_ids`, `has_backlog`.
7. **`student_subject_enrollments`**: `id` (PK), `roll_no` (FK), `subject_id` (FK) with unique index for conflict graph generation.
8. **`scheduling_runs`**: `run_id` (PK), `algorithm`, `status`, `total_exams`, `scheduled_exams`, `unscheduled_exams`, `hard_conflicts`, `soft_score`, `execution_time_ms`.
9. **`scheduled_exams`**: `id` (PK), `run_id`, `subject_id`, `slot_id`, `room_id`, `assigned_faculty_id`, `assigned_students`.
10. **`published_schedules`**: `published_id` (PK), `version`, `run_id`, `title`, `is_active`.
11. **`schedule_conflicts`**: `id` (PK), `run_id`, `conflict_type`, `subject_id_1`, `description`.

---

## 4. How to Verify & Run Locally

### Terminal 1: Run the Unified Server
```powershell
python run_dev.py
```
- Web Application & PWA: `http://localhost:8000/`
- API Swagger Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Terminal 2: Run the Automated Test Suite
```powershell
$env:PYTHONPATH = "backend"
backend/.venv/Scripts/pytest -v backend/tests/
```
All 14 tests pass in 0.40s.

### Frontend Development Server (Optional)
```powershell
cd frontend
npm run dev
```
Runs at `http://localhost:5173/`.
