"""
ExamOpt — FastAPI Backend Server
Problem Statement C10: Intelligent Examination Timetable Optimization System
GLA University Context: CSED Block AB-XI, BCA / BCA-DS / MCA Programs
"""

import os
import csv
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from validator import DataQualityValidator, validate_sqlite_database, validate_csv_file
from app.services.optimizer import TimetableOptimizerService
from app.services.exporter import ExporterService

# Paths
BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = BASE_DIR / "examopt.db"
DATASETS_DIR = BASE_DIR / "sample_datasets"
NORMAL_DIR = DATASETS_DIR / "normal_gla_dataset"

# Active state configuration
ACTIVE_STATE = {
    "preset": "normal",
    "last_validated": None,
    "last_run_id": None
}

app = FastAPI(
    title="ExamOpt API",
    description="Intelligent Examination Timetable Optimization System — GLA University",
    version="1.0.0"
)

# CORS Middleware
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection() -> sqlite3.Connection:
    if not SQLITE_DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Database file 'examopt.db' not found. Please run 'python seed_generator.py' first."
        )
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_active_dataset_records():
    conn = get_db_connection()
    cur = conn.cursor()
    rooms = [dict(r) for r in cur.execute("SELECT * FROM rooms").fetchall()]
    timeslots = [dict(r) for r in cur.execute("SELECT * FROM timeslots").fetchall()]
    faculty = [dict(r) for r in cur.execute("SELECT * FROM faculty").fetchall()]
    subjects = [dict(r) for r in cur.execute("SELECT * FROM subjects").fetchall()]
    groups = [dict(r) for r in cur.execute("SELECT * FROM student_groups").fetchall()]
    enrollments = [dict(r) for r in cur.execute("SELECT * FROM student_enrollments").fetchall()]
    conn.close()
    return rooms, timeslots, faculty, subjects, groups, enrollments


# -------------------------------------------------------------
# Pydantic Request Models
# -------------------------------------------------------------
class GenerateScheduleRequest(BaseModel):
    algorithm: str = Field(default="BACKTRACKING", description="FIRST_FIT, WELSH_POWELL, or BACKTRACKING")


class ValidateRequest(BaseModel):
    preset_name: Optional[str] = Field(default=None, description="normal, lab_bottleneck, capacity_overflow, invalid_corrupted")


# -------------------------------------------------------------
# Health & Status Endpoints
# -------------------------------------------------------------
@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    db_ok = SQLITE_DB_PATH.exists()
    supabase_configured = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SECRET_KEY"))
    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "sqlite_connected": db_ok,
            "sqlite_path": str(SQLITE_DB_PATH),
            "supabase_cloud_configured": supabase_configured,
            "active_preset": ACTIVE_STATE["preset"]
        }
    }


# -------------------------------------------------------------
# Phase 1 Data Endpoints
# -------------------------------------------------------------
@app.get("/api/data/summary", tags=["Phase 1 Data Foundation"])
def get_data_summary():
    """Returns counts of rooms, slots, subjects, student groups, individual students, and backlog students."""
    conn = get_db_connection()
    cur = conn.cursor()
    summary = {
        "active_preset": ACTIVE_STATE["preset"],
        "counts": {
            "rooms": cur.execute("SELECT COUNT(*) FROM rooms;").fetchone()[0],
            "timeslots": cur.execute("SELECT COUNT(*) FROM timeslots;").fetchone()[0],
            "faculty": cur.execute("SELECT COUNT(*) FROM faculty;").fetchone()[0],
            "subjects": cur.execute("SELECT COUNT(*) FROM subjects;").fetchone()[0],
            "student_groups": cur.execute("SELECT COUNT(*) FROM student_groups;").fetchone()[0],
            "student_enrollments": cur.execute("SELECT COUNT(*) FROM student_enrollments;").fetchone()[0],
            "student_subject_enrollments": cur.execute("SELECT COUNT(*) FROM student_subject_enrollments;").fetchone()[0],
            "backlog_students": cur.execute("SELECT COUNT(*) FROM student_enrollments WHERE has_backlog = 1;").fetchone()[0]
        },
        "campus_capacity": {
            "total_theory_seats": cur.execute("SELECT SUM(capacity) FROM rooms WHERE room_type = 'THEORY';").fetchone()[0] or 0,
            "total_lab_seats": cur.execute("SELECT SUM(capacity) FROM rooms WHERE room_type = 'LAB';").fetchone()[0] or 0,
            "total_rooms": cur.execute("SELECT COUNT(*) FROM rooms;").fetchone()[0]
        }
    }
    conn.close()
    return summary


@app.get("/api/data/tables/{table_name}", tags=["Phase 1 Data Foundation"])
def get_table_data(table_name: str, limit: int = Query(500, ge=1, le=2000)):
    """Returns all rows for a requested table."""
    allowed_tables = {
        "rooms", "timeslots", "faculty", "subjects",
        "student_groups", "student_enrollments", "student_subject_enrollments"
    }
    if table_name not in allowed_tables:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' is not accessible. Allowed: {list(allowed_tables)}")

    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"table": table_name, "count": len(rows), "rows": [dict(r) for r in rows]}


@app.post("/api/data/validate", tags=["Phase 1 Data Foundation"])
def validate_dataset(req: Optional[ValidateRequest] = None):
    """Runs validator on the active dataset or a specified preset and returns the validation report."""
    preset = req.preset_name if req and req.preset_name else ACTIVE_STATE["preset"]

    if preset == "normal":
        report = validate_sqlite_database(str(SQLITE_DB_PATH))
    elif preset == "lab_bottleneck":
        report = validate_csv_file(str(DATASETS_DIR / "edge_case_lab_bottleneck.csv"), table_type="subjects")
    elif preset == "capacity_overflow":
        report = validate_csv_file(str(DATASETS_DIR / "edge_case_capacity_overflow.csv"), table_type="subjects")
    elif preset in ("invalid_corrupted", "invalid"):
        report = validate_csv_file(str(DATASETS_DIR / "invalid_corrupted_input.csv"), table_type="subjects")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown preset '{preset}'. Choose normal, lab_bottleneck, capacity_overflow, or invalid_corrupted.")

    ACTIVE_STATE["last_validated"] = report
    return report


@app.post("/api/data/load-preset/{preset_name}", tags=["Phase 1 Data Foundation"])
def load_preset(preset_name: str):
    """Switches active state between presets for demonstration of edge cases."""
    valid_presets = ["normal", "lab_bottleneck", "capacity_overflow", "invalid_corrupted"]
    if preset_name not in valid_presets:
        raise HTTPException(status_code=400, detail=f"Invalid preset '{preset_name}'. Choose from: {valid_presets}")

    ACTIVE_STATE["preset"] = preset_name

    # If normal, re-seed from clean script if necessary
    if preset_name == "normal":
        import subprocess
        subprocess.run(["python", str(BASE_DIR / "seed_generator.py")], check=True)

    # Immediately validate the newly activated preset
    report = validate_dataset(ValidateRequest(preset_name=preset_name))
    return {
        "message": f"Successfully activated preset '{preset_name}'.",
        "active_preset": preset_name,
        "validation_report": report
    }


# -------------------------------------------------------------
# Scheduling & Optimization Endpoints (Phase C/D)
# -------------------------------------------------------------
@app.post("/api/v1/schedules/generate", tags=["Scheduling Engine"])
def generate_schedule(req: GenerateScheduleRequest):
    """Executes a timetable scheduling algorithm and saves the candidate schedule."""
    rooms, timeslots, faculty, subjects, groups, enrollments = get_active_dataset_records()

    service = TimetableOptimizerService(subjects, rooms, timeslots, faculty, enrollments)
    result = service.run_algorithm(req.algorithm)

    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    result["run_id"] = run_id
    ACTIVE_STATE["last_run_id"] = run_id

    # Persist in SQLite
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO scheduling_runs
           (run_id, algorithm, status, total_exams, scheduled_exams, unscheduled_exams, hard_conflicts, soft_score, execution_time_ms, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            result["algorithm"],
            result["status"],
            result["total_exams"],
            result["scheduled_exams"],
            result["unscheduled_exams"],
            result["hard_conflicts"],
            result["soft_score"],
            result["execution_time_ms"],
            json.dumps({"slots_used": result["slots_used"], "room_utilization_pct": result["room_utilization_pct"]})
        )
    )

    for alloc in result.get("allocations", []):
        alloc_id = f"ALLOC-{uuid.uuid4().hex[:8]}"
        cur.execute(
            """INSERT INTO scheduled_exams
               (id, run_id, subject_id, slot_id, room_id, assigned_faculty_id, assigned_students)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                alloc_id,
                run_id,
                alloc["subject_id"],
                alloc["slot_id"],
                alloc["room_id"],
                alloc.get("assigned_faculty_id"),
                alloc["assigned_students"]
            )
        )

    for conf in result.get("conflicts_log", []):
        cur.execute(
            """INSERT INTO schedule_conflicts
               (run_id, conflict_type, subject_id_1, description)
               VALUES (?, ?, ?, ?)""",
            (run_id, conf["conflict_type"], conf["subject_id_1"], conf["description"])
        )

    conn.commit()
    conn.close()

    return result


@app.post("/api/v1/schedules/compare", tags=["Scheduling Engine"])
def compare_schedules():
    """Executes First-Fit, Welsh-Powell, and Backtracking on active data and returns side-by-side benchmark."""
    rooms, timeslots, faculty, subjects, groups, enrollments = get_active_dataset_records()
    service = TimetableOptimizerService(subjects, rooms, timeslots, faculty, enrollments)
    return service.compare_all()


@app.get("/api/v1/schedules", tags=["Scheduling Engine"])
def list_schedule_runs():
    """Lists historical scheduling runs."""
    conn = get_db_connection()
    cur = conn.cursor()
    runs = cur.execute("SELECT * FROM scheduling_runs ORDER BY created_at DESC;").fetchall()
    conn.close()
    return {"runs": [dict(r) for r in runs]}


@app.get("/api/v1/schedules/active-published", tags=["Timetable Access"])
def get_active_published_schedule():
    """Returns the currently active published timetable for students, faculty, and web dashboard."""
    conn = get_db_connection()
    cur = conn.cursor()

    pub = cur.execute("SELECT * FROM published_schedules WHERE is_active = 1 ORDER BY version DESC LIMIT 1;").fetchone()
    if not pub:
        # If none published yet, generate and publish automatically for immediate zero-config demo experience
        conn.close()
        gen_res = generate_schedule(GenerateScheduleRequest(algorithm="BACKTRACKING"))
        pub_res = publish_schedule(gen_res["run_id"])
        return get_schedule_run_details(gen_res["run_id"])

    run_id = pub["run_id"]
    conn.close()
    details = get_schedule_run_details(run_id)
    details["publication"] = dict(pub)
    return details


@app.get("/api/v1/schedules/{run_id}", tags=["Scheduling Engine"])
def get_schedule_run_details(run_id: str):
    """Returns allocations and details for a specific run."""
    conn = get_db_connection()
    cur = conn.cursor()
    run = cur.execute("SELECT * FROM scheduling_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Schedule run '{run_id}' not found.")

    query = """
        SELECT
            se.id, se.run_id, se.subject_id, s.name as subject_name, s.program, s.semester, s.duration_hours, s.requires_lab,
            se.slot_id, t.exam_date, t.session, t.time_range,
            se.room_id, r.name as room_name, r.capacity as room_capacity,
            se.assigned_faculty_id, f.name as assigned_faculty_name,
            se.assigned_students
        FROM scheduled_exams se
        JOIN subjects s ON se.subject_id = s.subject_id
        JOIN timeslots t ON se.slot_id = t.slot_id
        JOIN rooms r ON se.room_id = r.room_id
        LEFT JOIN faculty f ON se.assigned_faculty_id = f.faculty_id
        WHERE se.run_id = ?
        ORDER BY t.exam_date, t.session, se.room_id
    """
    allocations = [dict(row) for row in cur.execute(query, (run_id,)).fetchall()]
    conflicts = [dict(row) for row in cur.execute("SELECT * FROM schedule_conflicts WHERE run_id = ?", (run_id,)).fetchall()]
    conn.close()

    return {
        "run": dict(run),
        "allocations": allocations,
        "conflicts": conflicts
    }


@app.post("/api/v1/schedules/{run_id}/publish", tags=["Publishing"])
def publish_schedule(run_id: str):
    """Atomically publishes a candidate schedule (rejects if hard conflicts exist)."""
    conn = get_db_connection()
    cur = conn.cursor()

    run = cur.execute("SELECT * FROM scheduling_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail="Run not found.")

    if run["hard_conflicts"] > 0 or run["status"] != "FEASIBLE":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish schedule '{run_id}' with status '{run['status']}' and {run['hard_conflicts']} hard conflicts!"
        )

    # Deactivate prior published versions
    cur.execute("UPDATE published_schedules SET is_active = 0;")

    # Fetch next version number
    max_v = cur.execute("SELECT MAX(version) FROM published_schedules;").fetchone()[0] or 0
    new_version = max_v + 1
    pub_id = f"PUB-V{new_version}-{uuid.uuid4().hex[:6]}"

    cur.execute(
        """INSERT INTO published_schedules (published_id, version, run_id, title, is_active)
           VALUES (?, ?, ?, ?, 1)""",
        (pub_id, new_version, run_id, f"GLA University Autumn 2026 Examination Timetable (Version {new_version})")
    )
    conn.commit()
    conn.close()

    return {
        "message": f"Schedule '{run_id}' successfully published as Version {new_version}.",
        "published_id": pub_id,
        "version": new_version,
        "is_active": True
    }


# -------------------------------------------------------------
# Student & Faculty Personalized Timetable Endpoints
# -------------------------------------------------------------
@app.get("/api/v1/timetable/student", tags=["Mobile Timetable Access"])
def get_student_timetable(roll_no: Optional[str] = Query(None, description="e.g. GLA26-BCA-0001")):
    """Returns the personalized examination schedule for a specific student's roll number."""
    active_pub = get_active_published_schedule()
    allocations = active_pub.get("allocations", [])

    if not roll_no:
        return {"roll_no": None, "message": "Provide ?roll_no=... for personalized view.", "timetable": allocations}

    conn = get_db_connection()
    cur = conn.cursor()
    student = cur.execute("SELECT * FROM student_enrollments WHERE roll_no = ?", (roll_no,)).fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Student with Roll Number '{roll_no}' not found.")

    student_dict = dict(student)
    enrolled_subj_ids = set(s.strip() for s in student_dict["enrolled_subject_ids"].split(",") if s.strip())
    conn.close()

    # Filter allocations for enrolled subjects
    student_exams = [a for a in allocations if a["subject_id"] in enrolled_subj_ids]
    student_exams.sort(key=lambda x: (x["exam_date"], x["slot_id"]))

    return {
        "student": student_dict,
        "total_enrolled_exams": len(enrolled_subj_ids),
        "scheduled_exams_count": len(student_exams),
        "schedule": student_exams
    }


@app.get("/api/v1/timetable/faculty", tags=["Mobile Timetable Access"])
def get_faculty_timetable(faculty_id: Optional[str] = Query(None, description="e.g. FAC-101")):
    """Returns assigned examination duties for a specific faculty member."""
    active_pub = get_active_published_schedule()
    allocations = active_pub.get("allocations", [])

    if not faculty_id:
        return {"faculty_id": None, "message": "Provide ?faculty_id=... for duty view.", "duties": allocations}

    conn = get_db_connection()
    cur = conn.cursor()
    fac = cur.execute("SELECT * FROM faculty WHERE faculty_id = ?", (faculty_id,)).fetchone()
    if not fac:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Faculty with ID '{faculty_id}' not found.")

    faculty_dict = dict(fac)
    conn.close()

    assigned_duties = [a for a in allocations if a.get("assigned_faculty_id") == faculty_id]
    assigned_duties.sort(key=lambda x: (x["exam_date"], x["slot_id"]))

    return {
        "faculty": faculty_dict,
        "assigned_duties_count": len(assigned_duties),
        "max_duties": faculty_dict["max_duties"],
        "duties": assigned_duties
    }


@app.get("/api/v1/timetable/export/csv", tags=["Exports"])
def export_timetable_csv(run_id: Optional[str] = None):
    """Downloads examination timetable as a CSV file."""
    if run_id:
        details = get_schedule_run_details(run_id)
    else:
        details = get_active_published_schedule()

    csv_data = ExporterService.export_timetable_csv(details.get("allocations", []))
    filename = f"ExamOpt_Timetable_{run_id or 'Published'}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# -------------------------------------------------------------
# Static Single Page Application (SPA) Serving
# -------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        # Don't intercept API routes or documentation
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "ExamOpt API Server is running. Frontend build in progress."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
