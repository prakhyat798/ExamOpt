"""
ExamOpt — Algorithm A: First-Fit Baseline Scheduler
Deterministic baseline scheduler that assigns each exam to the first feasible slot and room.
"""

import time
from typing import Dict, List, Set, Any
from collections import defaultdict
from .conflict_graph import SubjectConflictGraph
from .room_allocator import RoomAllocator
from .faculty_allocator import FacultyAllocator


class FirstFitScheduler:
    """Algorithm A: Simple deterministic First-Fit baseline scheduler."""

    def __init__(
        self,
        subjects: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        timeslots: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        enrollments: List[Dict[str, Any]]
    ):
        self.subjects = subjects
        self.rooms = rooms
        self.timeslots = sorted(timeslots, key=lambda t: (int(t.get("day_number", 1)), t.get("session", "")))
        self.faculty = faculty
        self.enrollments = enrollments

        self.conflict_graph = SubjectConflictGraph(subjects, enrollments)
        self.room_allocator = RoomAllocator(rooms)
        self.faculty_allocator = FacultyAllocator(faculty)

    def solve(self) -> Dict[str, Any]:
        start_time = time.perf_counter()

        # Slot -> list of scheduled subject_ids
        slot_subjects: Dict[str, List[str]] = defaultdict(list)
        # Slot -> set of occupied room_ids
        slot_occupied_rooms: Dict[str, Set[str]] = defaultdict(set)
        # Slot -> set of occupied faculty_ids
        slot_occupied_faculty: Dict[str, Set[str]] = defaultdict(set)
        faculty_duties: Dict[str, int] = defaultdict(int)

        scheduled_allocations = []
        unscheduled_exams = []
        conflicts_logged = []

        # Maintain natural/input order for baseline
        for subj in self.subjects:
            s_id = subj["subject_id"]
            fixed_slot = str(subj.get("fixed_slot", "") or "").strip()
            unav_str = str(subj.get("unavailable_slots", "") or "").strip()
            unav_slots = set(s.strip() for s in unav_str.split("|") if s.strip())

            # Determine candidate slots
            candidate_slots = []
            if fixed_slot:
                candidate_slots = [t for t in self.timeslots if t["slot_id"] == fixed_slot]
            else:
                candidate_slots = [t for t in self.timeslots if t["slot_id"] not in unav_slots]

            assigned = False
            reasons_tried = []

            for t in candidate_slots:
                slot_id = t["slot_id"]

                # 1. Hard Constraint: Student Clash Check
                existing_in_slot = slot_subjects[slot_id]
                clash_found = False
                for other_s_id in existing_in_slot:
                    if other_s_id in self.conflict_graph.get_conflicts(s_id):
                        shared = self.conflict_graph.get_shared_count(s_id, other_s_id)
                        reasons_tried.append(f"Student clash with '{other_s_id}' ({shared} shared students) in slot '{slot_id}'")
                        clash_found = True
                        break
                if clash_found:
                    continue

                # 2. Hard Constraint: Room Allocation Check
                best_room, room_reason = self.room_allocator.find_best_room(
                    subj, slot_id, slot_occupied_rooms[slot_id]
                )
                if not best_room:
                    reasons_tried.append(f"Room allocation failed in slot '{slot_id}': {room_reason}")
                    continue

                # 3. Faculty Allocation Check
                best_faculty, fac_reason = self.faculty_allocator.allocate_faculty(
                    subj, slot_id, slot_occupied_faculty[slot_id], faculty_duties
                )
                # If faculty is not strictly mandatory, we can assign None or best available
                fac_id = best_faculty["faculty_id"] if best_faculty else None

                # Commit allocation
                slot_subjects[slot_id].append(s_id)
                slot_occupied_rooms[slot_id].add(best_room["room_id"])
                if fac_id:
                    slot_occupied_faculty[slot_id].add(fac_id)
                    faculty_duties[fac_id] += 1

                scheduled_allocations.append({
                    "subject_id": s_id,
                    "subject_name": subj.get("name", ""),
                    "program": subj.get("program", ""),
                    "semester": subj.get("semester", 1),
                    "slot_id": slot_id,
                    "exam_date": t["exam_date"],
                    "session": t["session"],
                    "time_range": t["time_range"],
                    "room_id": best_room["room_id"],
                    "room_name": best_room.get("name", ""),
                    "room_capacity": best_room.get("capacity", 0),
                    "assigned_faculty_id": fac_id,
                    "assigned_faculty_name": best_faculty.get("name", "TBD") if best_faculty else "TBD",
                    "assigned_students": int(subj.get("enrolled_students", 0)),
                    "duration_hours": int(subj.get("duration_hours", 3)),
                    "requires_lab": bool(subj.get("requires_lab", 0))
                })
                assigned = True
                break

            if not assigned:
                unscheduled_exams.append({
                    "subject_id": s_id,
                    "subject_name": subj.get("name", ""),
                    "enrolled_students": int(subj.get("enrolled_students", 0)),
                    "requires_lab": bool(subj.get("requires_lab", 0)),
                    "fixed_slot": fixed_slot,
                    "reasons": reasons_tried[:3] if reasons_tried else ["No feasible slot and room combination found."]
                })
                conflicts_logged.append({
                    "conflict_type": "UNSCHEDULED_EXAM",
                    "subject_id_1": s_id,
                    "description": f"First-Fit could not find a clash-free slot/room for '{s_id}'. Reasons: {'; '.join(reasons_tried[:2])}"
                })

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        total_exams = len(self.subjects)
        scheduled_count = len(scheduled_allocations)
        unscheduled_count = len(unscheduled_exams)
        is_feasible = (unscheduled_count == 0)

        # Calculate metrics
        slots_used = len(set(a["slot_id"] for a in scheduled_allocations))
        total_assigned_students = sum(a["assigned_students"] for a in scheduled_allocations)
        total_room_capacity_used = sum(a["room_capacity"] for a in scheduled_allocations)
        unused_seats = total_room_capacity_used - total_assigned_students
        room_utilization_pct = (total_assigned_students / total_room_capacity_used * 100.0) if total_room_capacity_used > 0 else 0.0

        return {
            "algorithm": "FIRST_FIT",
            "status": "FEASIBLE" if is_feasible else "PARTIAL",
            "is_feasible": is_feasible,
            "total_exams": total_exams,
            "scheduled_exams": scheduled_count,
            "unscheduled_exams": unscheduled_count,
            "hard_conflicts": 0 if is_feasible else unscheduled_count,
            "slots_used": slots_used,
            "room_utilization_pct": round(room_utilization_pct, 2),
            "unused_capacity_seats": unused_seats,
            "execution_time_ms": round(duration_ms, 2),
            "allocations": scheduled_allocations,
            "unscheduled_details": unscheduled_exams,
            "conflicts_log": conflicts_logged
        }
