"""
ExamOpt — Algorithm C: Constraint-Aware Backtracking with MRV & Forward Checking
Explores assignment search tree using Minimum Remaining Values (MRV), forward checking, and room checks.
"""

import time
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
from .conflict_graph import SubjectConflictGraph
from .room_allocator import RoomAllocator
from .faculty_allocator import FacultyAllocator


class ConstraintBacktrackingScheduler:
    """Algorithm C: Constraint-aware backtracking with MRV and forward checking."""

    def __init__(
        self,
        subjects: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        timeslots: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        enrollments: List[Dict[str, Any]],
        max_nodes: int = 5000,
        time_limit_sec: float = 5.0
    ):
        self.subjects = {s["subject_id"]: s for s in subjects}
        self.rooms = rooms
        self.timeslots = sorted(timeslots, key=lambda t: (int(t.get("day_number", 1)), t.get("session", "")))
        self.slot_map = {t["slot_id"]: t for t in self.timeslots}
        self.all_slot_ids = [t["slot_id"] for t in self.timeslots]
        self.faculty = faculty
        self.enrollments = enrollments
        self.max_nodes = max_nodes
        self.time_limit_sec = time_limit_sec

        self.conflict_graph = SubjectConflictGraph(subjects, enrollments)
        self.room_allocator = RoomAllocator(rooms)
        self.faculty_allocator = FacultyAllocator(faculty)

        self.nodes_explored = 0
        self.start_time = 0.0
        self.timed_out = False

    def solve(self) -> Dict[str, Any]:
        self.start_time = time.perf_counter()
        self.nodes_explored = 0
        self.timed_out = False

        # 1. Initialize Domains for each subject
        domains: Dict[str, List[str]] = {}
        for s_id, subj in self.subjects.items():
            fixed = str(subj.get("fixed_slot", "") or "").strip()
            unav_str = str(subj.get("unavailable_slots", "") or "").strip()
            unav_slots = set(s.strip() for s in unav_str.split("|") if s.strip())

            if fixed:
                domains[s_id] = [fixed] if fixed in self.slot_map else []
            else:
                domains[s_id] = [s for s in self.all_slot_ids if s not in unav_slots]

        # Initial assignment state
        assignment: Dict[str, str] = {}  # subject_id -> slot_id
        slot_occupied_rooms: Dict[str, Set[str]] = defaultdict(set)
        room_assignments: Dict[str, Dict[str, Any]] = {}

        # 2. Fixed slot propagation at the root
        for s_id, subj in self.subjects.items():
            fixed = str(subj.get("fixed_slot", "") or "").strip()
            if fixed:
                assignment[s_id] = fixed
                best_room, _ = self.room_allocator.find_best_room(subj, fixed, slot_occupied_rooms[fixed])
                if not best_room:
                    # Infeasible fixed slot allocation
                    duration_ms = (time.perf_counter() - self.start_time) * 1000.0
                    return self._build_result(False, {}, {}, duration_ms, "Proven Infeasibility: Fixed slot has no available room.")
                room_assignments[s_id] = best_room
                slot_occupied_rooms[fixed].add(best_room["room_id"])

                # Forward check to prune conflicting neighbors
                for neighbor in self.conflict_graph.get_conflicts(s_id):
                    if neighbor in domains and fixed in domains[neighbor]:
                        domains[neighbor] = [slot for slot in domains[neighbor] if slot != fixed]
                        if not domains[neighbor] and neighbor not in assignment:
                            duration_ms = (time.perf_counter() - self.start_time) * 1000.0
                            return self._build_result(False, {}, {}, duration_ms, f"Proven Infeasibility: Fixed slot '{fixed}' for '{s_id}' empties domain of conflicting neighbor '{neighbor}'.")

        # 3. Recursive Backtracking Search
        unassigned = [s_id for s_id in self.subjects if s_id not in assignment]
        success = self._backtrack(assignment, domains, slot_occupied_rooms, room_assignments, unassigned)

        duration_ms = (time.perf_counter() - self.start_time) * 1000.0

        if success:
            return self._build_result(True, assignment, room_assignments, duration_ms, "Optimal Feasible Solution Found")
        elif self.timed_out:
            return self._build_result(False, assignment, room_assignments, duration_ms, f"Search Exhausted (Node limit of {self.max_nodes} or time limit reached). NOT proven infeasible.")
        else:
            return self._build_result(False, assignment, room_assignments, duration_ms, "Proven Infeasibility under current constraints.")

    def _backtrack(
        self,
        assignment: Dict[str, str],
        domains: Dict[str, List[str]],
        slot_occupied_rooms: Dict[str, Set[str]],
        room_assignments: Dict[str, Dict[str, Any]],
        unassigned: List[str]
    ) -> bool:
        if not unassigned:
            return True

        self.nodes_explored += 1
        if self.nodes_explored > self.max_nodes or (time.perf_counter() - self.start_time) > self.time_limit_sec:
            self.timed_out = True
            return False

        # MRV Heuristic: Choose variable with Minimum Remaining Values
        # Tie-breaker: Degree heuristic (highest degree first)
        var = min(
            unassigned,
            key=lambda s_id: (len(domains[s_id]), -self.conflict_graph.get_degree(s_id), s_id)
        )

        subj = self.subjects[var]
        var_domain = list(domains[var])

        for slot_id in var_domain:
            # 1. Check student clash with assigned exams in this slot
            clash = False
            for neighbor in self.conflict_graph.get_conflicts(var):
                if assignment.get(neighbor) == slot_id:
                    clash = True
                    break
            if clash:
                continue

            # 2. Check room feasibility
            best_room, _ = self.room_allocator.find_best_room(subj, slot_id, slot_occupied_rooms[slot_id])
            if not best_room:
                continue

            # Forward check: simulate pruning slot_id from neighbors
            pruned: Dict[str, bool] = {}
            forward_check_ok = True
            for neighbor in self.conflict_graph.get_conflicts(var):
                if neighbor not in assignment and slot_id in domains[neighbor]:
                    domains[neighbor].remove(slot_id)
                    pruned[neighbor] = True
                    if not domains[neighbor]:
                        forward_check_ok = False
                        break

            if forward_check_ok:
                # Commit trial assignment
                assignment[var] = slot_id
                room_assignments[var] = best_room
                slot_occupied_rooms[slot_id].add(best_room["room_id"])
                next_unassigned = [s for s in unassigned if s != var]

                if self._backtrack(assignment, domains, slot_occupied_rooms, room_assignments, next_unassigned):
                    return True

                # Undo trial assignment
                del assignment[var]
                del room_assignments[var]
                slot_occupied_rooms[slot_id].remove(best_room["room_id"])

            # Undo forward checking pruning
            for neighbor, _ in pruned.items():
                domains[neighbor].append(slot_id)

        return False

    def _build_result(
        self,
        is_feasible: bool,
        assignment: Dict[str, str],
        room_assignments: Dict[str, Dict[str, Any]],
        duration_ms: float,
        diagnostic_message: str
    ) -> Dict[str, Any]:
        # Assign faculty to allocations
        slot_occupied_faculty: Dict[str, Set[str]] = defaultdict(set)
        faculty_duties: Dict[str, int] = defaultdict(int)

        scheduled_allocations = []
        for s_id, slot_id in assignment.items():
            subj = self.subjects[s_id]
            t = self.slot_map[slot_id]
            room = room_assignments[s_id]

            best_faculty, _ = self.faculty_allocator.allocate_faculty(
                subj, slot_id, slot_occupied_faculty[slot_id], faculty_duties
            )
            fac_id = best_faculty["faculty_id"] if best_faculty else None
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
                "room_id": room["room_id"],
                "room_name": room.get("name", ""),
                "room_capacity": room.get("capacity", 0),
                "assigned_faculty_id": fac_id,
                "assigned_faculty_name": best_faculty.get("name", "TBD") if best_faculty else "TBD",
                "assigned_students": int(subj.get("enrolled_students", 0)),
                "duration_hours": int(subj.get("duration_hours", 3)),
                "requires_lab": bool(subj.get("requires_lab", 0))
            })

        unscheduled_exams = [
            {
                "subject_id": s_id,
                "subject_name": subj.get("name", ""),
                "enrolled_students": int(subj.get("enrolled_students", 0)),
                "requires_lab": bool(subj.get("requires_lab", 0)),
                "reasons": [diagnostic_message]
            }
            for s_id, subj in self.subjects.items() if s_id not in assignment
        ]

        slots_used = len(set(assignment.values()))
        total_assigned_students = sum(a["assigned_students"] for a in scheduled_allocations)
        total_room_capacity_used = sum(a["room_capacity"] for a in scheduled_allocations)
        unused_seats = total_room_capacity_used - total_assigned_students
        room_utilization_pct = (total_assigned_students / total_room_capacity_used * 100.0) if total_room_capacity_used > 0 else 0.0

        status = "FEASIBLE" if is_feasible else ("TIMEOUT" if self.timed_out else "INFEASIBLE")

        return {
            "algorithm": "BACKTRACKING",
            "status": status,
            "is_feasible": is_feasible,
            "total_exams": len(self.subjects),
            "scheduled_exams": len(scheduled_allocations),
            "unscheduled_exams": len(unscheduled_exams),
            "hard_conflicts": 0 if is_feasible else len(unscheduled_exams),
            "slots_used": slots_used,
            "room_utilization_pct": round(room_utilization_pct, 2),
            "unused_capacity_seats": unused_seats,
            "execution_time_ms": round(duration_ms, 2),
            "nodes_explored": self.nodes_explored,
            "allocations": scheduled_allocations,
            "unscheduled_details": unscheduled_exams,
            "diagnostic_message": diagnostic_message,
            "conflicts_log": [
                {
                    "conflict_type": "UNSCHEDULED_EXAM",
                    "subject_id_1": u["subject_id"],
                    "description": diagnostic_message
                }
                for u in unscheduled_exams
            ]
        }
