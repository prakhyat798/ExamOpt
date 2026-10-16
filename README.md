# ExamOpt — Intelligent Examination Timetable Optimization System
### GLA HackVision 2.0 | Problem Statement C10
**Domain**: Web Development, Algorithms, Constraint Optimization  
**Context**: GLA University, Mathura (CSED Block AB-XI, BCA / BCA-DS / MCA Programs)

---

## 1. System Overview

**ExamOpt** is an intelligent, constraint-based university examination timetable optimization platform. Preparing examination timetables manually in universities is an NP-hard combinatorial problem: hundreds of courses and student groups compete for limited examination halls, specialized computer laboratories, and faculty invigilators. 

ExamOpt eliminates examination clashes, room-capacity violations, laboratory bottlenecks, and faculty scheduling conflicts using **three genuine, deterministic optimization algorithms** paired with an interactive Web Dashboard and responsive Mobile PWA for students and faculty.

> [!IMPORTANT]
> **Zero LLM Scheduling**: The scheduling engine uses our own deterministic algorithms (First-Fit baseline, Welsh–Powell graph coloring, and Constraint-Aware Backtracking with MRV and forward checking). No generative AI or external LLM API is responsible for scheduling decisions.

---

## 2. Architecture & Monorepo Structure

```
hackvision/
├── backend/
│   ├── app/
│   │   ├── algorithms/
│   │   │   ├── conflict_graph.py      # Student-conflict graph & cross-semester backlog edges
│   │   │   ├── baseline_first_fit.py  # Algorithm A: First-Fit greedy baseline
│   │   │   ├── welsh_powell.py        # Algorithm B: Degree-based graph coloring
│   │   │   ├── backtracking.py        # Algorithm C: MRV + Forward Checking constraint search
│   │   │   ├── room_allocator.py      # Best-Fit room packing & lab matching
│   │   │   └── faculty_allocator.py   # Workload-balanced invigilator assignment
│   │   └── services/
│   │       ├── optimizer.py           # Multi-algorithm comparison & benchmark service
│   │       └── exporter.py            # Timetable & room allocation CSV exporters
│   ├── sample_datasets/
│   │   ├── normal_gla_dataset/        # 100% schedulable, 0 conflict baseline
│   │   │   ├── rooms.csv (15 rooms)
│   │   │   ├── timeslots.csv (10 slots across 5 days)
│   │   │   ├── faculty.csv (20 invigilators)
│   │   │   ├── subjects.csv (24 courses across BCA, BCA-DS, MCA)
│   │   │   ├── student_groups.csv (8 groups including 3 backlog cohorts)
│   │   │   └── student_enrollments.csv (355 students, 1,735 enrollments)
│   │   ├── edge_case_lab_bottleneck.csv   # 6 lab exams locked to slot D1-M (exceeds 5 labs)
│   │   ├── edge_case_capacity_overflow.csv # Course with 650 students exceeding room capacity
│   │   └── invalid_corrupted_input.csv    # Duplicate IDs, negative counts, contradictory slots
│   ├── tests/
│   │   ├── test_data_validation.py    # Quality report & edge-case rejection tests
│   │   ├── test_algorithms.py         # Clash-free validation & algorithm benchmarks
│   │   └── test_api.py                # FastAPI endpoint integration tests
│   ├── examopt.db                     # Local SQLite database
│   ├── schema.sql                     # SQLite/PostgreSQL DDL schema
│   ├── seed_generator.py              # Deterministic generator (random.seed(42))
│   ├── validator.py                   # Data quality inspection engine
│   └── main.py                        # FastAPI unified application server
├── frontend/
│   ├── src/
│   │   ├── services/api.ts            # Typed backend API client
│   │   ├── App.tsx                    # Admin Dashboard, Grid, Benchmark, Student/Faculty views
│   │   ├── index.css                  # Modern Tailwind design tokens & Inter font
│   │   └── main.tsx
│   ├── public/manifest.json           # Progressive Web App (PWA) manifest
│   ├── tailwind.config.js
│   └── vite.config.ts
├── supabase/
│   └── migrations/
│       └── 20261016000000_create_examopt_schema.sql  # Supabase PostgreSQL migration with RLS
├── docs/
│   └── IMPLEMENTATION_STATUS.md       # Verification & test ledger
├── run_dev.py                         # Single-command unified development runner
├── .env.example                       # Environment configuration template
└── .gitignore
```

---

## 3. Scheduling Constraints & Problem Formulation

### 3.1 Hard Constraints (Must NEVER be Violated)
1. **Student Conflict-Free Guarantee**: No student may be scheduled for more than one examination in the same time slot ($Slot(u) \neq Slot(v)$ if $(u, v) \in E_{conflict}$).
2. **Cross-Semester Backlog Conflicts**: Backlog students who repeat previous-semester courses (e.g. BCA Sem 5 students taking a Sem 3 course) create real cross-semester conflict edges.
3. **Room Capacity**: The number of students taking an exam in a room must not exceed the room's physical capacity ($Students(u) \le Capacity(Room)$).
4. **Room Type Matching**: Practical/laboratory examinations (`requires_lab=True`) must only be assigned to specialized `LAB` rooms; theory exams to `THEORY` lecture halls.
5. **No Room Double-Booking**: A physical room cannot host multiple examinations in the same slot.
6. **Room Availability**: Rooms cannot be scheduled during declared `unavailable_slots` (e.g. maintenance windows).
7. **Fixed Administrative Slots**: Subjects locked by university administration to a specific `fixed_slot` must remain locked to that slot.
8. **Faculty Invigilation Integrity**: An invigilator cannot be assigned to overlapping examinations, during `unavailable_slots`, or exceed their configured `max_duties`.

### 3.2 Soft Objectives
1. **Maximize Room Utilization**: Minimize empty seats via Best-Fit packing ($\frac{\sum \text{Enrolled Students}}{\sum \text{Allocated Room Capacity}}$).
2. **Slot Compactness**: Minimize total time slots required to conduct examinations.
3. **Faculty Workload Balance**: Distribute invigilation duties evenly across faculty members.

---

## 4. Optimization Algorithms Implemented

| Feature | Algorithm A: First-Fit Baseline | Algorithm B: Welsh–Powell Coloring | Algorithm C: MRV Backtracking |
| :--- | :--- | :--- | :--- |
| **Strategy** | Greedy sequential placement | Graph degree ordering ($d(v)$) | Constraint satisfaction search |
| **Variable Ordering** | Natural input order | Descending degree (most constrained first) | Minimum Remaining Values (MRV) |
| **Pruning / Checking** | None | Adjacency coloring | Forward checking on neighbor domains |
| **Fixed Slot Handling** | Direct trial | Pre-placed prior to variable color pass | Root propagation + domain pruning |
| **Room Allocation** | Best-Fit packing | Best-Fit packing | Best-Fit room feasibility at each branch |
| **Faculty Allocation** | Workload balanced | Workload balanced | Workload balanced |
| **Time Limit / Budget** | Instant | Instant ($\approx 3$ ms) | Configurable budget ($\le 5,000$ nodes) |

---

## 5. Synthetic Datasets & Rubric Edge Cases

All datasets are generated deterministically (`random.seed(42)`) in `backend/sample_datasets/`:
1. `normal_gla_dataset/`: The clean baseline. 15 rooms (1,340 seats in AB-XI), 10 time slots (5 days), 20 faculty, 24 courses across BCA/MCA, 8 student groups, 355 students, 1,735 enrollments. **Validation Readiness Score: 100/100, 0 clashes.**
2. `edge_case_lab_bottleneck.csv`: 6 lab examinations are forced into fixed slot `D1-M`, exceeding the 5 available physical laboratories in CSED Block AB-XI. The validator identifies `LAB_BOTTLENECK` and suggests session staggering.
3. `edge_case_capacity_overflow.csv`: Course `BCA-101` has enrollment inflated to 650 students, exceeding the largest hall (Mini Auditorium: 150 seats). The validator detects `CAPACITY_OVERFLOW` and recommends room splitting.
4. `invalid_corrupted_input.csv`: Contains duplicate IDs, negative enrollment (`-40`), contradictory constraints (`fixed_slot = D2-M` AND `unavailable_slots = D2-M`), missing fields, and non-existent slot references (`D99-M`). The validator detects all 6 errors and halts scheduling.

---

## 6. Automated Test Suite Results

The automated test suite in `backend/tests/` verifies the entire system:
```bash
$env:PYTHONPATH = "backend"
backend/.venv/Scripts/pytest -v backend/tests/
```
**Results: 14 PASSED, 0 FAILED (0.40s):**
- `test_sqlite_normal_dataset_readiness`: PASSED (Score: 100, 0 errors, 0 warnings)
- `test_corrupted_input_rejection`: PASSED (Rejects duplicate IDs, negative counts, invalid slots)
- `test_lab_bottleneck_detection`: PASSED (Detects lab bottleneck in slot D1-M)
- `test_capacity_overflow_detection`: PASSED (Detects mega-course exceeding room size)
- `test_conflict_graph_backlog_edges`: PASSED (Cross-semester backlog edges verified)
- `test_welsh_powell_produces_no_student_clashes`: PASSED (0 student clashes guaranteed)
- `test_backtracking_solver_correctness`: PASSED (Optimal room & faculty assignment)
- `test_algorithm_benchmark_comparison`: PASSED (Side-by-side benchmark execution)
- `test_health_check`: PASSED
- `test_data_summary`: PASSED
- `test_table_data_endpoint`: PASSED
- `test_validation_endpoint`: PASSED
- `test_schedule_generation_and_publishing`: PASSED
- `test_student_and_faculty_mobile_views`: PASSED

---

## 7. Quickstart Commands

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Launch Everything with One Command
```powershell
python run_dev.py
```
This runs the unified FastAPI application on **http://localhost:8000/**:
- **Web & Mobile Application**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Frontend Hot-Reload Development (Optional)
```powershell
cd frontend
npm run dev
```
Runs Vite dev server at **http://localhost:5173/**.

---

## 8. Supabase Cloud Configuration

To connect the application to your Supabase PostgreSQL cloud project:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set your Supabase URL and rotated Service Role Secret Key:
   ```env
   SUPABASE_URL=https://<your-project-ref>.supabase.co
   SUPABASE_PUBLISHABLE_KEY=<your-publishable-key>
   SUPABASE_SECRET_KEY=<your-rotated-service-role-secret-key>
   ```
3. Apply the versioned database migration in version control:
   Execute `supabase/migrations/20261016000000_create_examopt_schema.sql` via Supabase SQL Editor or CLI.
4. Row Level Security (RLS) is pre-configured to allow public read access only to active published schedules (`is_active = TRUE`), keeping unpublished drafts and sensitive administrative data secure.
