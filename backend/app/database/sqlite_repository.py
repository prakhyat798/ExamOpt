"""
ExamOpt SQLite Repository Implementation
Local offline-first database adapter for development, testing, and edge-case benchmarking.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from app.database.base import DatabaseRepository
from app.database.exceptions import (
    DatabaseConnectionError,
    EntityNotFoundError,
    DatabaseIntegrityError
)


class SQLiteRepository(DatabaseRepository):
    """SQLite implementation of ExamOpt database operations."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise DatabaseConnectionError(
                f"SQLite database file not found at '{self.db_path}'. Run seed generator first."
            )
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except sqlite3.Error as e:
            raise DatabaseConnectionError(f"Failed to connect to SQLite: {e}") from e

    def health_check(self) -> Dict[str, Any]:
        exists = self.db_path.exists()
        healthy = False
        tables_count = 0
        if exists:
            try:
                conn = self._get_connection()
                cur = conn.cursor()
                res = cur.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
                ).fetchone()
                tables_count = res[0] if res else 0
                healthy = tables_count >= 11
                conn.close()
            except Exception:
                healthy = False

        return {
            "backend": "sqlite",
            "is_cloud": False,
            "connected": healthy,
            "database_exists": exists,
            "tables_count": tables_count
        }

    def get_summary(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            summary = {
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
            return summary
        finally:
            conn.close()

    def get_table_data(self, table_name: str, limit: int = 500) -> Dict[str, Any]:
        allowed_tables = {
            "rooms", "timeslots", "faculty", "subjects",
            "student_groups", "student_enrollments", "student_subject_enrollments",
            "scheduling_runs", "scheduled_exams", "published_schedules", "schedule_conflicts"
        }
        if table_name not in allowed_tables:
            raise EntityNotFoundError(f"Table '{table_name}' is not allowed or not found.")

        conn = self._get_connection()
        cur = conn.cursor()
        try:
            rows = cur.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,)).fetchall()
            return {"table": table_name, "count": len(rows), "rows": [dict(r) for r in rows]}
        finally:
            conn.close()

    def get_active_dataset_records(self) -> Tuple[
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]]
    ]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            rooms = [dict(r) for r in cur.execute("SELECT * FROM rooms").fetchall()]
            timeslots = [dict(r) for r in cur.execute("SELECT * FROM timeslots").fetchall()]
            faculty = [dict(r) for r in cur.execute("SELECT * FROM faculty").fetchall()]
            subjects = [dict(r) for r in cur.execute("SELECT * FROM subjects").fetchall()]
            groups = [dict(r) for r in cur.execute("SELECT * FROM student_groups").fetchall()]
            enrollments = [dict(r) for r in cur.execute("SELECT * FROM student_enrollments").fetchall()]
            return rooms, timeslots, faculty, subjects, groups, enrollments
        finally:
            conn.close()

    def save_scheduling_run(
        self,
        run_data: Dict[str, Any],
        allocations: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> str:
        conn = self._get_connection()
        cur = conn.cursor()
        run_id = run_data["run_id"]

        try:
            cur.execute(
                """INSERT INTO scheduling_runs
                   (run_id, algorithm, status, total_exams, scheduled_exams, unscheduled_exams, hard_conflicts, soft_score, execution_time_ms, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    run_data["algorithm"],
                    run_data["status"],
                    run_data["total_exams"],
                    run_data["scheduled_exams"],
                    run_data["unscheduled_exams"],
                    run_data["hard_conflicts"],
                    run_data["soft_score"],
                    run_data["execution_time_ms"],
                    json.dumps(run_data.get("metadata", {}))
                )
            )

            for alloc in allocations:
                alloc_id = alloc.get("id") or f"ALLOC-{uuid.uuid4().hex[:8]}"
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

            for conf in conflicts:
                cur.execute(
                    """INSERT INTO schedule_conflicts
                       (run_id, conflict_type, subject_id_1, description)
                       VALUES (?, ?, ?, ?)""",
                    (run_id, conf["conflict_type"], conf["subject_id_1"], conf["description"])
                )

            conn.commit()
            return run_id
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise DatabaseIntegrityError(f"Integrity error saving run '{run_id}': {e}") from e
        finally:
            conn.close()

    def list_scheduling_runs(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            runs = cur.execute("SELECT * FROM scheduling_runs ORDER BY created_at DESC;").fetchall()
            return [dict(r) for r in runs]
        finally:
            conn.close()

    def get_schedule_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            run = cur.execute("SELECT * FROM scheduling_runs WHERE run_id = ?", (run_id,)).fetchone()
            if not run:
                return None

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

            return {
                "run": dict(run),
                "allocations": allocations,
                "conflicts": conflicts
            }
        finally:
            conn.close()

    def publish_schedule(self, run_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            run = cur.execute("SELECT * FROM scheduling_runs WHERE run_id = ?", (run_id,)).fetchone()
            if not run:
                raise EntityNotFoundError(f"Run '{run_id}' not found.")

            if run["hard_conflicts"] > 0 or run["status"] != "FEASIBLE":
                raise DatabaseIntegrityError(
                    f"Cannot publish schedule '{run_id}' with status '{run['status']}' and {run['hard_conflicts']} hard conflicts!"
                )

            # Atomic transaction: deactivate prior published versions
            cur.execute("UPDATE published_schedules SET is_active = 0;")

            max_v = cur.execute("SELECT MAX(version) FROM published_schedules;").fetchone()[0] or 0
            new_version = max_v + 1
            pub_id = f"PUB-V{new_version}-{uuid.uuid4().hex[:6]}"
            pub_title = title or f"GLA University Autumn 2026 Examination Timetable (Version {new_version})"

            cur.execute(
                """INSERT INTO published_schedules (published_id, version, run_id, title, is_active)
                   VALUES (?, ?, ?, ?, 1)""",
                (pub_id, new_version, run_id, pub_title)
            )
            conn.commit()

            return {
                "message": f"Schedule '{run_id}' successfully published as Version {new_version}.",
                "published_id": pub_id,
                "version": new_version,
                "run_id": run_id,
                "title": pub_title,
                "is_active": True
            }
        finally:
            conn.close()

    def get_active_published_schedule(self) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            pub = cur.execute("SELECT * FROM published_schedules WHERE is_active = 1 ORDER BY version DESC LIMIT 1;").fetchone()
            if not pub:
                return None
            run_id = pub["run_id"]
            details = self.get_schedule_run_details(run_id)
            if details:
                details["publication"] = dict(pub)
            return details
        finally:
            conn.close()

    def get_student_timetable(self, roll_no: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            student = cur.execute("SELECT * FROM student_enrollments WHERE roll_no = ?", (roll_no,)).fetchone()
            if not student:
                return None

            student_dict = dict(student)
            enrolled_subj_ids = set(s.strip() for s in student_dict["enrolled_subject_ids"].split(",") if s.strip())

            active_pub = self.get_active_published_schedule()
            allocations = active_pub.get("allocations", []) if active_pub else []

            student_exams = [a for a in allocations if a["subject_id"] in enrolled_subj_ids]
            student_exams.sort(key=lambda x: (x["exam_date"], x["slot_id"]))

            return {
                "student": student_dict,
                "total_enrolled_exams": len(enrolled_subj_ids),
                "scheduled_exams_count": len(student_exams),
                "schedule": student_exams
            }
        finally:
            conn.close()

    def get_faculty_timetable(self, faculty_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            fac = cur.execute("SELECT * FROM faculty WHERE faculty_id = ?", (faculty_id,)).fetchone()
            if not fac:
                return None

            faculty_dict = dict(fac)
            active_pub = self.get_active_published_schedule()
            allocations = active_pub.get("allocations", []) if active_pub else []

            assigned_duties = [a for a in allocations if a.get("assigned_faculty_id") == faculty_id]
            assigned_duties.sort(key=lambda x: (x["exam_date"], x["slot_id"]))

            return {
                "faculty": faculty_dict,
                "assigned_duties_count": len(assigned_duties),
                "max_duties": faculty_dict["max_duties"],
                "duties": assigned_duties
            }
        finally:
            conn.close()
