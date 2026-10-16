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
from app.database import (
    DatabaseBackend,
    DatabaseConfig,
    DatabaseRepository,
    get_repository,
    ConfigurationError,
    DatabaseConnectionError,
    EntityNotFoundError,
    DatabaseIntegrityError
)

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
    """Backward-compatible direct SQLite connection helper."""
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
    """Fetches foundation records using the configured repository (SQLite or Supabase)."""
    repo = get_repository()
    return repo.get_active_dataset_records()


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
    """
    Observable health check that verifies connectivity of the configured database backend.
    Never exposes passwords, tokens, connection strings, or private keys.
    """
    cfg = DatabaseConfig()
    try:
        repo = get_repository()
        repo_health = repo.health_check()
    except ConfigurationError as e:
        return {
            "status": "misconfigured",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {
                "configured_backend": cfg.backend.value,
                "is_cloud": cfg.backend == DatabaseBackend.SUPABASE,
                "connected": False,
                "error": str(e)
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {
                "configured_backend": cfg.backend.value,
                "is_cloud": cfg.backend == DatabaseBackend.SUPABASE,
                "connected": False,
                "error": str(e)
            }
        }

    is_connected = repo_health.get("connected", False)
    safe_cfg = cfg.get_safe_status()

    return {
        "status": "healthy" if is_connected else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "configured_backend": cfg.backend.value,
            "is_cloud": cfg.backend == DatabaseBackend.SUPABASE,
            "connected": is_connected,
            "sqlite_connected": is_connected if cfg.backend == DatabaseBackend.SQLITE else False,
            "sqlite_path": str(cfg.sqlite_db_path),
            "supabase_cloud_configured": safe_cfg["supabase"]["configured"],
            "active_preset": ACTIVE_STATE["preset"],
            "backend_details": repo_health
        }
    }


# -------------------------------------------------------------
# Phase 1 Data Endpoints
# -------------------------------------------------------------
@app.get("/api/data/summary", tags=["Phase 1 Data Foundation"])
def get_data_summary():
    """Returns counts of rooms, slots, subjects, student groups, individual students, and backlog students."""
    try:
        repo = get_repository()
        summary = repo.get_summary()
        summary["active_preset"] = ACTIVE_STATE["preset"]
        return summary
    except DatabaseConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data summary: {str(e)}")


@app.get("/api/data/tables/{table_name}", tags=["Phase 1 Data Foundation"])
def get_table_data(table_name: str, limit: int = Query(500, ge=1, le=2000)):
    """Returns all rows for a requested table."""
    try:
        repo = get_repository()
        return repo.get_table_data(table_name, limit)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve table data: {str(e)}")


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
    repo = get_repository()
    rooms, timeslots, faculty, subjects, groups, enrollments = repo.get_active_dataset_records()

    service = TimetableOptimizerService(subjects, rooms, timeslots, faculty, enrollments)
    result = service.run_algorithm(req.algorithm)

    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    result["run_id"] = run_id
    ACTIVE_STATE["last_run_id"] = run_id

    # Persist in active repository
    run_record = {
        "run_id": run_id,
        "algorithm": result["algorithm"],
        "status": result["status"],
        "total_exams": result["total_exams"],
        "scheduled_exams": result["scheduled_exams"],
        "unscheduled_exams": result["unscheduled_exams"],
        "hard_conflicts": result["hard_conflicts"],
        "soft_score": result["soft_score"],
        "execution_time_ms": result["execution_time_ms"],
        "metadata": {
            "slots_used": result["slots_used"],
            "room_utilization_pct": result["room_utilization_pct"]
        }
    }

    try:
        repo.save_scheduling_run(run_record, result.get("allocations", []), result.get("conflicts_log", []))
    except DatabaseIntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return result


@app.post("/api/v1/schedules/compare", tags=["Scheduling Engine"])
def compare_schedules():
    """Executes First-Fit, Welsh-Powell, and Backtracking on active data and returns side-by-side benchmark."""
    repo = get_repository()
    rooms, timeslots, faculty, subjects, groups, enrollments = repo.get_active_dataset_records()
    service = TimetableOptimizerService(subjects, rooms, timeslots, faculty, enrollments)
    return service.compare_all()


@app.get("/api/v1/schedules", tags=["Scheduling Engine"])
def list_schedule_runs():
    """Lists historical scheduling runs."""
    repo = get_repository()
    runs = repo.list_scheduling_runs()
    return {"runs": runs}


@app.get("/api/v1/schedules/active-published", tags=["Timetable Access"])
def get_active_published_schedule():
    """Returns the currently active published timetable for students, faculty, and web dashboard."""
    repo = get_repository()
    details = repo.get_active_published_schedule()
    if not details:
        # If none published yet, generate and publish automatically for zero-config demo experience
        gen_res = generate_schedule(GenerateScheduleRequest(algorithm="BACKTRACKING"))
        publish_schedule(gen_res["run_id"])
        details = repo.get_active_published_schedule()

    return details


@app.get("/api/v1/schedules/{run_id}", tags=["Scheduling Engine"])
def get_schedule_run_details(run_id: str):
    """Returns allocations and details for a specific run."""
    repo = get_repository()
    details = repo.get_schedule_run_details(run_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Schedule run '{run_id}' not found.")
    return details


@app.post("/api/v1/schedules/{run_id}/publish", tags=["Publishing"])
def publish_schedule(run_id: str):
    """Atomically publishes a candidate schedule (rejects if hard conflicts exist)."""
    repo = get_repository()
    try:
        return repo.publish_schedule(run_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseIntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


# -------------------------------------------------------------
# Student & Faculty Personalized Timetable Endpoints
# -------------------------------------------------------------
@app.get("/api/v1/timetable/student", tags=["Mobile Timetable Access"])
def get_student_timetable(roll_no: Optional[str] = Query(None, description="e.g. GLA26-BCA-0001")):
    """Returns the personalized examination schedule for a specific student's roll number."""
    repo = get_repository()
    if not roll_no:
        active_pub = repo.get_active_published_schedule()
        allocations = active_pub.get("allocations", []) if active_pub else []
        return {"roll_no": None, "message": "Provide ?roll_no=... for personalized view.", "timetable": allocations}

    try:
        res = repo.get_student_timetable(roll_no)
        if not res:
            raise HTTPException(status_code=404, detail=f"Student with Roll Number '{roll_no}' not found.")
        return res
    except DatabaseConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/timetable/faculty", tags=["Mobile Timetable Access"])
def get_faculty_timetable(faculty_id: Optional[str] = Query(None, description="e.g. FAC-101")):
    """Returns assigned examination duties for a specific faculty member."""
    repo = get_repository()
    if not faculty_id:
        active_pub = repo.get_active_published_schedule()
        allocations = active_pub.get("allocations", []) if active_pub else []
        return {"faculty_id": None, "message": "Provide ?faculty_id=... for duty view.", "duties": allocations}

    try:
        res = repo.get_faculty_timetable(faculty_id)
        if not res:
            raise HTTPException(status_code=404, detail=f"Faculty with ID '{faculty_id}' not found.")
        return res
    except DatabaseConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/v1/timetable/export/csv", tags=["Exports"])
def export_timetable_csv(run_id: Optional[str] = None):
    """Downloads examination timetable as a CSV file."""
    repo = get_repository()
    if run_id:
        details = repo.get_schedule_run_details(run_id)
    else:
        details = repo.get_active_published_schedule()

    if not details:
        raise HTTPException(status_code=404, detail="No schedule available for export.")

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
