"""
ExamOpt — Faculty Invigilation Allocation Engine
Allocates invigilators respecting availability, maximum duty limits, and department alignment.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from collections import defaultdict


class FacultyAllocator:
    """Allocates invigilators deterministically with workload balancing."""

    def __init__(self, faculty_list: List[Dict[str, Any]]):
        self.faculty = {f["faculty_id"]: f for f in faculty_list}
        self.unavailable_by_faculty: Dict[str, Set[str]] = {}
        for f in faculty_list:
            unav = str(f.get("unavailable_slots", "") or "").strip()
            self.unavailable_by_faculty[f["faculty_id"]] = set(s.strip() for s in unav.split("|") if s.strip())

    def allocate_faculty(
        self,
        subject: Dict[str, Any],
        slot_id: str,
        occupied_faculty_in_slot: Set[str],
        current_duty_counts: Dict[str, int]
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Finds the best available faculty invigilator for an exam in slot_id.
        Returns: (faculty_dict or None, diagnostic_reason)
        """
        prog = str(subject.get("program", "")).upper()
        # Department mapping preference
        target_dept = "MCA" if prog == "MCA" else ("BCA" if prog == "BCA" else "CSED")

        candidates = []
        for f_id, f in self.faculty.items():
            # 1. Not already occupied in this slot
            if f_id in occupied_faculty_in_slot:
                continue

            # 2. Not declared unavailable in this slot
            if slot_id in self.unavailable_by_faculty.get(f_id, set()):
                continue

            # 3. Duty limit check
            assigned_duties = current_duty_counts.get(f_id, 0)
            max_duties = int(f.get("max_duties", 4))
            if assigned_duties >= max_duties:
                continue

            # Preference: department match (0 if matches, 1 if other department)
            dept_mismatch = 0 if f.get("department", "").upper() == target_dept else 1

            candidates.append((dept_mismatch, assigned_duties, f_id, f))

        if not candidates:
            return None, f"No available faculty with remaining duties eligible for slot '{slot_id}'."

        # Sort by: dept match first, then lowest assigned duties (balancing), then deterministic f_id
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        best_faculty = candidates[0][3]
        return best_faculty, "SUCCESS"
