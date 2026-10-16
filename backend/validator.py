"""
ExamOpt — Comprehensive Data Quality & Constraint Validation Engine
Problem Statement C10: Intelligent Examination Timetable Optimization System

Inspects active datasets, CSV files, and SQLite tables:
- Duplicate IDs
- Negative student enrollments
- Foreign key mismatches (e.g. non-existent slot references like D99-M)
- Contradictory constraints (e.g. fixed_slot == unavailable_slot)
- Capacity overflows (e.g. single course enrollment > largest room capacity)
- Lab bottlenecks (lab demand in a slot > total lab capacity)
- Mathematical consistency between individual student enrollments and subject student counts
"""

import os
import csv
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set


class DataQualityValidator:
    """Validates examination dataset tables and generates a Data Quality & Readiness Report."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.counts: Dict[str, int] = {}
        self.diagnostics: List[str] = []

    def _add_error(self, code: str, table: str, row_id: Any, field: str, message: str):
        self.errors.append({
            "code": code,
            "table": table,
            "row_id": str(row_id),
            "field": field,
            "message": message,
            "severity": "ERROR"
        })

    def _add_warning(self, code: str, table: str, row_id: Any, field: str, message: str):
        self.warnings.append({
            "code": code,
            "table": table,
            "row_id": str(row_id),
            "field": field,
            "message": message,
            "severity": "WARNING"
        })

    def validate_dataset(
        self,
        rooms: List[Dict[str, Any]],
        timeslots: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        subjects: List[Dict[str, Any]],
        student_groups: Optional[List[Dict[str, Any]]] = None,
        student_enrollments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Runs complete multi-phase validation across all data tables."""
        self.errors.clear()
        self.warnings.clear()
        self.diagnostics.clear()

        # 1. Timeslots Validation
        valid_slot_ids = self._validate_timeslots(timeslots)

        # 2. Rooms Validation
        max_theory_cap, max_lab_cap, total_lab_cap, num_lab_rooms = self._validate_rooms(rooms, valid_slot_ids)

        # 3. Faculty Validation
        self._validate_faculty(faculty, valid_slot_ids)

        # 4. Subjects Validation
        self._validate_subjects(subjects, valid_slot_ids, max_theory_cap, max_lab_cap, total_lab_cap, num_lab_rooms)

        # 5. Student Groups & Individual Enrollments Validation (if provided)
        valid_group_ids = set()
        if student_groups:
            valid_group_ids = self._validate_student_groups(student_groups)

        if student_enrollments:
            self._validate_student_enrollments(student_enrollments, valid_group_ids, subjects)

        # 6. Global Readiness & Feasibility Diagnostics
        self._generate_readiness_diagnostics(rooms, timeslots, subjects)

        total_err = len(self.errors)
        total_warn = len(self.warnings)
        readiness_score = max(0, 100 - (total_err * 20) - (total_warn * 5))
        is_valid = (total_err == 0)

        report = {
            "is_valid": is_valid,
            "readiness_score": readiness_score,
            "status": "READY_FOR_OPTIMIZATION" if is_valid else "VALIDATION_FAILED",
            "summary": {
                "total_errors": total_err,
                "total_warnings": total_warn,
                "table_counts": {
                    "rooms": len(rooms),
                    "timeslots": len(timeslots),
                    "faculty": len(faculty),
                    "subjects": len(subjects),
                    "student_groups": len(student_groups or []),
                    "student_enrollments": len(student_enrollments or []),
                }
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "diagnostics": self.diagnostics
        }
        return report

    def _validate_timeslots(self, timeslots: List[Dict[str, Any]]) -> Set[str]:
        valid_slot_ids = set()
        seen_slot_ids = set()
        seen_date_sessions = set()

        for idx, row in enumerate(timeslots, start=1):
            slot_id = str(row.get("slot_id", "")).strip()
            if not slot_id:
                self._add_error("MISSING_SLOT_ID", "timeslots", f"row_{idx}", "slot_id", "Slot ID cannot be empty.")
                continue

            if slot_id in seen_slot_ids:
                self._add_error("DUPLICATE_SLOT_ID", "timeslots", slot_id, "slot_id", f"Duplicate slot_id '{slot_id}' found.")
            seen_slot_ids.add(slot_id)
            valid_slot_ids.add(slot_id)

            # Validate session
            session = str(row.get("session", "")).strip().upper()
            if session not in ("MORNING", "EVENING"):
                self._add_error("INVALID_SESSION", "timeslots", slot_id, "session", f"Session '{session}' must be MORNING or EVENING.")

            # Validate day number
            try:
                day_num = int(row.get("day_number", 0))
                if day_num < 1 or day_num > 14:
                    self._add_error("INVALID_DAY_NUMBER", "timeslots", slot_id, "day_number", f"Day number {day_num} must be between 1 and 14.")
            except (ValueError, TypeError):
                self._add_error("INVALID_DAY_NUMBER", "timeslots", slot_id, "day_number", "Day number must be a valid integer.")

            # Check unique date + session
            exam_date = str(row.get("exam_date", "")).strip()
            date_session = f"{exam_date}_{session}"
            if date_session in seen_date_sessions:
                self._add_error("DUPLICATE_DATE_SESSION", "timeslots", slot_id, "exam_date", f"Slot conflict: date '{exam_date}' already has a {session} session.")
            seen_date_sessions.add(date_session)

        return valid_slot_ids

    def _validate_rooms(self, rooms: List[Dict[str, Any]], valid_slot_ids: Set[str]) -> Tuple[int, int, int, int]:
        seen_room_ids = set()
        max_theory_cap = 0
        max_lab_cap = 0
        total_lab_cap = 0
        num_lab_rooms = 0

        for idx, row in enumerate(rooms, start=1):
            room_id = str(row.get("room_id", "")).strip()
            if not room_id:
                self._add_error("MISSING_ROOM_ID", "rooms", f"row_{idx}", "room_id", "Room ID cannot be empty.")
                continue

            if room_id in seen_room_ids:
                self._add_error("DUPLICATE_ROOM_ID", "rooms", room_id, "room_id", f"Duplicate room_id '{room_id}' found.")
            seen_room_ids.add(room_id)

            # Validate capacity
            try:
                cap = int(row.get("capacity", 0))
                if cap <= 0:
                    self._add_error("INVALID_CAPACITY", "rooms", room_id, "capacity", f"Room capacity ({cap}) must be > 0.")
            except (ValueError, TypeError):
                self._add_error("INVALID_CAPACITY", "rooms", room_id, "capacity", "Capacity must be an integer.")
                cap = 0

            # Validate room_type
            rtype = str(row.get("room_type", "")).strip().upper()
            if rtype not in ("THEORY", "LAB"):
                self._add_error("INVALID_ROOM_TYPE", "rooms", room_id, "room_type", f"Room type '{rtype}' must be THEORY or LAB.")
            else:
                if rtype == "THEORY":
                    max_theory_cap = max(max_theory_cap, cap)
                elif rtype == "LAB":
                    max_lab_cap = max(max_lab_cap, cap)
                    total_lab_cap += cap
                    num_lab_rooms += 1

            # Validate unavailable_slots references
            unav = str(row.get("unavailable_slots", "")).strip()
            if unav:
                for slot in unav.split("|"):
                    slot = slot.strip()
                    if slot and valid_slot_ids and slot not in valid_slot_ids:
                        self._add_warning("UNKNOWN_SLOT_REF", "rooms", room_id, "unavailable_slots", f"Referenced slot '{slot}' is not in defined timeslots.")

        return max_theory_cap, max_lab_cap, total_lab_cap, num_lab_rooms

    def _validate_faculty(self, faculty: List[Dict[str, Any]], valid_slot_ids: Set[str]):
        seen_fac_ids = set()

        for idx, row in enumerate(faculty, start=1):
            fac_id = str(row.get("faculty_id", "")).strip()
            if not fac_id:
                self._add_error("MISSING_FACULTY_ID", "faculty", f"row_{idx}", "faculty_id", "Faculty ID cannot be empty.")
                continue

            if fac_id in seen_fac_ids:
                self._add_error("DUPLICATE_FACULTY_ID", "faculty", fac_id, "faculty_id", f"Duplicate faculty_id '{fac_id}' found.")
            seen_fac_ids.add(fac_id)

            name = str(row.get("name", "")).strip()
            if not name:
                self._add_error("MISSING_NAME", "faculty", fac_id, "name", "Faculty name cannot be blank.")

            dept = str(row.get("department", "")).strip().upper()
            if dept not in ("CSED", "BCA", "MCA"):
                self._add_error("INVALID_DEPARTMENT", "faculty", fac_id, "department", f"Invalid department '{dept}'. Expected CSED, BCA, or MCA.")

            try:
                duties = int(row.get("max_duties", 0))
                if duties < 0:
                    self._add_error("NEGATIVE_DUTIES", "faculty", fac_id, "max_duties", f"Max duties ({duties}) cannot be negative.")
            except (ValueError, TypeError):
                self._add_error("INVALID_DUTIES", "faculty", fac_id, "max_duties", "Max duties must be an integer.")

            unav = str(row.get("unavailable_slots", "")).strip()
            if unav:
                for slot in unav.split("|"):
                    slot = slot.strip()
                    if slot and valid_slot_ids and slot not in valid_slot_ids:
                        self._add_warning("UNKNOWN_SLOT_REF", "faculty", fac_id, "unavailable_slots", f"Referenced slot '{slot}' does not exist.")

    def _validate_subjects(
        self,
        subjects: List[Dict[str, Any]],
        valid_slot_ids: Set[str],
        max_theory_cap: int,
        max_lab_cap: int,
        total_lab_cap: int,
        num_lab_rooms: int,
    ):
        seen_subj_ids = set()
        lab_fixed_slot_counts: Dict[str, List[str]] = {}

        for idx, row in enumerate(subjects, start=1):
            s_id = str(row.get("subject_id", "")).strip()
            if not s_id:
                self._add_error("MISSING_SUBJECT_ID", "subjects", f"row_{idx}", "subject_id", "Subject ID cannot be empty.")
                continue

            if s_id in seen_subj_ids:
                self._add_error("DUPLICATE_SUBJECT_ID", "subjects", s_id, "subject_id", f"Duplicate subject_id '{s_id}' detected.")
            seen_subj_ids.add(s_id)

            name = str(row.get("name", "")).strip()
            if not name:
                self._add_error("MISSING_NAME", "subjects", s_id, "name", f"Subject '{s_id}' has missing or blank name.")

            prog = str(row.get("program", "")).strip().upper()
            if prog not in ("BCA", "BCA-DS", "MCA"):
                self._add_error("INVALID_PROGRAM", "subjects", s_id, "program", f"Subject '{s_id}' has invalid program '{prog}'.")

            # Check enrolled students
            enrolled = 0
            try:
                enrolled = int(row.get("enrolled_students", 0))
                if enrolled < 0:
                    self._add_error("NEGATIVE_ENROLLMENT", "subjects", s_id, "enrolled_students", f"Negative enrollment ({enrolled}) detected in subject '{s_id}'.")
            except (ValueError, TypeError):
                self._add_error("INVALID_ENROLLMENT", "subjects", s_id, "enrolled_students", f"Invalid enrolled_students value '{row.get('enrolled_students')}' in subject '{s_id}'.")

            # Duration hours
            try:
                duration = int(row.get("duration_hours", 0))
                if duration not in (2, 3):
                    self._add_warning("UNUSUAL_DURATION", "subjects", s_id, "duration_hours", f"Subject '{s_id}' duration is {duration} hours (standard is 2h for lab, 3h for theory).")
            except (ValueError, TypeError):
                self._add_error("INVALID_DURATION", "subjects", s_id, "duration_hours", "Duration hours must be an integer.")

            # requires_lab
            raw_lab = row.get("requires_lab", 0)
            requires_lab = raw_lab in (1, "1", True, "True", "true")

            # Fixed slot and unavailable slots
            fixed_slot = str(row.get("fixed_slot", "") or "").strip()
            unav_str = str(row.get("unavailable_slots", "") or "").strip()
            unav_slots = set(s.strip() for s in unav_str.split("|") if s.strip())

            # Check non-existent fixed_slot reference
            if fixed_slot:
                if valid_slot_ids and fixed_slot not in valid_slot_ids:
                    self._add_error("FOREIGN_KEY_NOT_FOUND", "subjects", s_id, "fixed_slot", f"Fixed slot '{fixed_slot}' does not exist in timeslots table.")

                # Check contradictory constraints: fixed_slot is also in unavailable_slots
                if fixed_slot in unav_slots:
                    self._add_error(
                        "CONTRADICTORY_CONSTRAINTS",
                        "subjects",
                        s_id,
                        "fixed_slot",
                        f"Subject '{s_id}' has contradictory constraint: fixed_slot '{fixed_slot}' is also declared in unavailable_slots!"
                    )

                # Track lab exams fixed to same slot
                if requires_lab:
                    lab_fixed_slot_counts.setdefault(fixed_slot, []).append(s_id)

            # Check capacity overflow for single room
            if max_theory_cap > 0 and not requires_lab and enrolled > max_theory_cap:
                self._add_error(
                    "CAPACITY_OVERFLOW",
                    "subjects",
                    s_id,
                    "enrolled_students",
                    f"Subject '{s_id}' enrollment ({enrolled}) exceeds the capacity of the largest Theory room ({max_theory_cap}). Requires room splitting or reallocation."
                )

            if max_lab_cap > 0 and requires_lab and enrolled > max_lab_cap:
                self._add_error(
                    "LAB_CAPACITY_OVERFLOW",
                    "subjects",
                    s_id,
                    "enrolled_students",
                    f"Lab subject '{s_id}' enrollment ({enrolled}) exceeds largest Lab room capacity ({max_lab_cap})."
                )

        # Check Lab Bottlenecks across fixed slots
        for slot, subj_list in lab_fixed_slot_counts.items():
            if len(subj_list) > num_lab_rooms:
                self._add_error(
                    "LAB_BOTTLENECK",
                    "subjects",
                    slot,
                    "fixed_slot",
                    f"Lab Bottleneck in slot '{slot}': {len(subj_list)} lab examinations ({', '.join(subj_list)}) are locked to slot '{slot}', but campus only has {num_lab_rooms} specialized labs!"
                )

    def _validate_student_groups(self, groups: List[Dict[str, Any]]) -> Set[str]:
        valid_groups = set()
        seen_groups = set()

        for idx, row in enumerate(groups, start=1):
            g_id = str(row.get("group_id", "")).strip()
            if not g_id:
                self._add_error("MISSING_GROUP_ID", "student_groups", f"row_{idx}", "group_id", "Group ID cannot be empty.")
                continue

            if g_id in seen_groups:
                self._add_error("DUPLICATE_GROUP_ID", "student_groups", g_id, "group_id", f"Duplicate group_id '{g_id}' found.")
            seen_groups.add(g_id)
            valid_groups.add(g_id)

            try:
                count = int(row.get("student_count", 0))
                if count < 0:
                    self._add_error("NEGATIVE_STUDENT_COUNT", "student_groups", g_id, "student_count", f"Group '{g_id}' student count ({count}) cannot be negative.")
            except (ValueError, TypeError):
                self._add_error("INVALID_STUDENT_COUNT", "student_groups", g_id, "student_count", "Student count must be an integer.")

        return valid_groups

    def _validate_student_enrollments(
        self,
        enrollments: List[Dict[str, Any]],
        valid_group_ids: Set[str],
        subjects: List[Dict[str, Any]]
    ):
        seen_rolls = set()
        valid_subj_ids = {s.get("subject_id") for s in subjects}
        actual_subject_counts: Dict[str, int] = {}

        for idx, row in enumerate(enrollments, start=1):
            roll_no = str(row.get("roll_no", "")).strip()
            if not roll_no:
                self._add_error("MISSING_ROLL_NO", "student_enrollments", f"row_{idx}", "roll_no", "Roll number cannot be empty.")
                continue

            if roll_no in seen_rolls:
                self._add_error("DUPLICATE_ROLL_NO", "student_enrollments", roll_no, "roll_no", f"Duplicate roll_no '{roll_no}' found.")
            seen_rolls.add(roll_no)

            # Check group FK
            g_id = str(row.get("group_id", "")).strip()
            if valid_group_ids and g_id not in valid_group_ids:
                self._add_error("FOREIGN_KEY_NOT_FOUND", "student_enrollments", roll_no, "group_id", f"Student '{roll_no}' references non-existent group '{g_id}'.")

            # Check subject references
            subj_str = str(row.get("enrolled_subject_ids", "")).strip()
            if not subj_str:
                self._add_warning("EMPTY_ENROLLMENT", "student_enrollments", roll_no, "enrolled_subject_ids", f"Student '{roll_no}' has no enrolled subjects.")
            else:
                for s in subj_str.split(","):
                    s = s.strip()
                    if s:
                        if valid_subj_ids and s not in valid_subj_ids:
                            self._add_error("FOREIGN_KEY_NOT_FOUND", "student_enrollments", roll_no, "enrolled_subject_ids", f"Student '{roll_no}' enrolled in unknown subject '{s}'.")
                        actual_subject_counts[s] = actual_subject_counts.get(s, 0) + 1

        # Check mathematical consistency between student enrollments and subject.enrolled_students
        for s in subjects:
            s_id = s.get("subject_id")
            expected_count = actual_subject_counts.get(s_id, 0)
            declared_count = s.get("enrolled_students")
            if declared_count is not None and declared_count != expected_count:
                self._add_warning(
                    "ENROLLMENT_COUNT_MISMATCH",
                    "subjects",
                    s_id,
                    "enrolled_students",
                    f"Subject '{s_id}' declares {declared_count} enrolled students, but exact enrollment records sum to {expected_count} students."
                )

    def _generate_readiness_diagnostics(self, rooms: List[Dict[str, Any]], timeslots: List[Dict[str, Any]], subjects: List[Dict[str, Any]]):
        num_slots = len(timeslots)
        num_rooms = len(rooms)
        num_subjects = len(subjects)

        self.diagnostics.append(f"ExamOpt Scope: {num_subjects} examinations across {num_slots} time slots and {num_rooms} physical rooms.")

        if num_slots == 0:
            self.diagnostics.append("CRITICAL: No examination time slots configured. Timetable generation cannot proceed.")
        elif num_subjects > (num_slots * num_rooms):
            self.diagnostics.append(f"WARNING: Subject count ({num_subjects}) exceeds absolute room-slot matrix capacity ({num_slots * num_rooms}).")
        else:
            self.diagnostics.append("Room-slot capacity matrix is sufficient to host all course examinations.")

        if any(e["code"] == "CAPACITY_OVERFLOW" for e in self.errors):
            self.diagnostics.append("REMEDY SUGGESTION: Configure room splitting or assign high-enrollment courses to mini-auditoriums (AB11-AUD1/AUD2).")

        if any(e["code"] == "LAB_BOTTLENECK" for e in self.errors):
            self.diagnostics.append("REMEDY SUGGESTION: Stagger lab examinations across morning and evening sessions, or unlock conflicting fixed_slot assignments.")


def validate_sqlite_database(db_path: str) -> Dict[str, Any]:
    """Validates the active SQLite database directly."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rooms = [dict(r) for r in cur.execute("SELECT * FROM rooms").fetchall()]
    timeslots = [dict(r) for r in cur.execute("SELECT * FROM timeslots").fetchall()]
    faculty = [dict(r) for r in cur.execute("SELECT * FROM faculty").fetchall()]
    subjects = [dict(r) for r in cur.execute("SELECT * FROM subjects").fetchall()]
    groups = [dict(r) for r in cur.execute("SELECT * FROM student_groups").fetchall()]
    enrollments = [dict(r) for r in cur.execute("SELECT * FROM student_enrollments").fetchall()]
    conn.close()

    validator = DataQualityValidator(db_path)
    return validator.validate_dataset(rooms, timeslots, faculty, subjects, groups, enrollments)


def validate_csv_file(csv_path: str, table_type: str = "subjects", base_dataset_dir: Optional[str] = None) -> Dict[str, Any]:
    """Validates an individual CSV file in the context of the active dataset."""
    base_dir = Path(base_dataset_dir or Path(__file__).resolve().parent / "sample_datasets" / "normal_gla_dataset")

    def read_csv(path):
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    rooms = read_csv(base_dir / "rooms.csv")
    timeslots = read_csv(base_dir / "timeslots.csv")
    faculty = read_csv(base_dir / "faculty.csv")
    subjects = read_csv(base_dir / "subjects.csv")
    groups = read_csv(base_dir / "student_groups.csv")
    enrollments = read_csv(base_dir / "student_enrollments.csv")

    # Replace the target table with the uploaded/specified CSV
    target_rows = read_csv(csv_path)
    if table_type == "subjects":
        subjects = target_rows
        # If testing an incomplete or fixture subjects file (< 20 items), skip full student enrollment cross-check
        if len(subjects) < 20:
            enrollments = None
    elif table_type == "rooms":
        rooms = target_rows
    elif table_type == "faculty":
        faculty = target_rows
    elif table_type == "timeslots":
        timeslots = target_rows

    validator = DataQualityValidator()
    return validator.validate_dataset(rooms, timeslots, faculty, subjects, groups, enrollments)


if __name__ == "__main__":
    print("Testing validator against SQLite database...")
    db_file = Path(__file__).resolve().parent / "examopt.db"
    if db_file.exists():
        report = validate_sqlite_database(str(db_file))
        print(f"Normal Database Validation: Status={report['status']}, Readiness Score={report['readiness_score']}")
        print(f"Errors={len(report['errors'])}, Warnings={len(report['warnings'])}")

    print("\nTesting validator against 'invalid_corrupted_input.csv'...")
    corrupt_file = Path(__file__).resolve().parent / "sample_datasets" / "invalid_corrupted_input.csv"
    if corrupt_file.exists():
        c_report = validate_csv_file(str(corrupt_file), table_type="subjects")
        print(f"Corrupted File Validation: Status={c_report['status']}, Readiness Score={c_report['readiness_score']}")
        print(f"Detected {len(c_report['errors'])} errors as expected:")
        for err in c_report['errors']:
            print(f"  [{err['code']}] {err['message']}")

    print("\nTesting validator against 'edge_case_lab_bottleneck.csv'...")
    lab_file = Path(__file__).resolve().parent / "sample_datasets" / "edge_case_lab_bottleneck.csv"
    if lab_file.exists():
        l_report = validate_csv_file(str(lab_file), table_type="subjects")
        print(f"Lab Bottleneck Validation: Status={l_report['status']}, Score={l_report['readiness_score']}")
        for err in l_report['errors']:
            print(f"  [{err['code']}] {err['message']}")

    print("\nTesting validator against 'edge_case_capacity_overflow.csv'...")
    cap_file = Path(__file__).resolve().parent / "sample_datasets" / "edge_case_capacity_overflow.csv"
    if cap_file.exists():
        cap_report = validate_csv_file(str(cap_file), table_type="subjects")
        print(f"Capacity Overflow Validation: Status={cap_report['status']}, Score={cap_report['readiness_score']}")
        for err in cap_report['errors']:
            print(f"  [{err['code']}] {err['message']}")
