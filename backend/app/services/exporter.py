"""
ExamOpt — Timetable & Reporting Exporter Service
Exports schedule results to CSV and structured JSON formats.
"""

import io
import csv
from typing import Dict, List, Any


class ExporterService:
    """Generates downloadable CSV and JSON exports of examination schedules."""

    @staticmethod
    def export_timetable_csv(allocations: List[Dict[str, Any]]) -> str:
        """Exports complete timetable grid to CSV."""
        output = io.StringIO()
        fieldnames = [
            "exam_date", "day_session", "slot_id", "time_range",
            "subject_id", "subject_name", "program", "semester",
            "room_id", "room_name", "room_capacity",
            "assigned_faculty_name", "assigned_students", "duration_hours"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for a in sorted(allocations, key=lambda x: (x.get("exam_date", ""), x.get("slot_id", ""), x.get("room_id", ""))):
            writer.writerow({
                "exam_date": a.get("exam_date", ""),
                "day_session": f"{a.get('session', '')}",
                "slot_id": a.get("slot_id", ""),
                "time_range": a.get("time_range", ""),
                "subject_id": a.get("subject_id", ""),
                "subject_name": a.get("subject_name", ""),
                "program": a.get("program", ""),
                "semester": a.get("semester", ""),
                "room_id": a.get("room_id", ""),
                "room_name": a.get("room_name", ""),
                "room_capacity": a.get("room_capacity", ""),
                "assigned_faculty_name": a.get("assigned_faculty_name", "TBD"),
                "assigned_students": a.get("assigned_students", 0),
                "duration_hours": a.get("duration_hours", 3)
            })

        return output.getvalue()

    @staticmethod
    def export_room_allocations_csv(allocations: List[Dict[str, Any]]) -> str:
        """Exports room-wise allocations to CSV."""
        output = io.StringIO()
        fieldnames = ["room_id", "room_name", "slot_id", "exam_date", "time_range", "subject_id", "enrolled_students", "room_capacity", "empty_seats"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for a in sorted(allocations, key=lambda x: (x.get("room_id", ""), x.get("exam_date", ""))):
            cap = int(a.get("room_capacity", 0))
            studs = int(a.get("assigned_students", 0))
            writer.writerow({
                "room_id": a.get("room_id", ""),
                "room_name": a.get("room_name", ""),
                "slot_id": a.get("slot_id", ""),
                "exam_date": a.get("exam_date", ""),
                "time_range": a.get("time_range", ""),
                "subject_id": a.get("subject_id", ""),
                "enrolled_students": studs,
                "room_capacity": cap,
                "empty_seats": max(0, cap - studs)
            })

        return output.getvalue()
