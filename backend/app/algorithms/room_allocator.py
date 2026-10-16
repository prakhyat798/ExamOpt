"""
ExamOpt — Best-Fit Room Allocation Engine
Allocates examination halls and specialized laboratories while respecting capacity and slot availability.
"""

from typing import Dict, List, Optional, Set, Any, Tuple


class RoomAllocator:
    """Allocates rooms deterministically using Best-Fit capacity packing."""

    def __init__(self, rooms: List[Dict[str, Any]]):
        self.rooms = {r["room_id"]: r for r in rooms}
        # Pre-parse unavailable slots
        self.unavailable_by_room: Dict[str, Set[str]] = {}
        for r in rooms:
            unav = str(r.get("unavailable_slots", "") or "").strip()
            self.unavailable_by_room[r["room_id"]] = set(s.strip() for s in unav.split("|") if s.strip())

    def find_best_room(
        self,
        subject: Dict[str, Any],
        slot_id: str,
        occupied_rooms_in_slot: Set[str]
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Finds the optimal room for a subject in a slot.
        Returns: (room_dict or None, diagnostic_reason)
        """
        requires_lab = bool(subject.get("requires_lab", 0))
        target_type = "LAB" if requires_lab else "THEORY"
        enrolled = int(subject.get("enrolled_students", 0))

        candidate_rooms = []
        for r_id, r in self.rooms.items():
            # 1. Room type must match
            if r.get("room_type", "THEORY").upper() != target_type:
                continue

            # 2. Room must not be occupied in this slot
            if r_id in occupied_rooms_in_slot:
                continue

            # 3. Room must not be declared unavailable in this slot
            if slot_id in self.unavailable_by_room.get(r_id, set()):
                continue

            # 4. Capacity check
            cap = int(r.get("capacity", 0))
            if cap >= enrolled:
                wasted_seats = cap - enrolled
                candidate_rooms.append((wasted_seats, cap, r_id, r))

        if not candidate_rooms:
            # Diagnose why no room is found
            all_type_rooms = [r for r in self.rooms.values() if r.get("room_type", "THEORY").upper() == target_type]
            available_in_slot = [
                r for r in all_type_rooms
                if r["room_id"] not in occupied_rooms_in_slot and slot_id not in self.unavailable_by_room.get(r["room_id"], set())
            ]
            if not available_in_slot:
                return None, f"All {target_type} rooms are either occupied in slot '{slot_id}' or unavailable."
            
            max_avail_cap = max((int(r.get("capacity", 0)) for r in available_in_slot), default=0)
            return None, f"Required capacity {enrolled} exceeds largest available {target_type} room ({max_avail_cap} seats) in slot '{slot_id}'."

        # Best-Fit: minimize wasted_seats, break ties deterministically by room_id
        candidate_rooms.sort(key=lambda item: (item[0], item[2]))
        best_room = candidate_rooms[0][3]
        return best_room, "SUCCESS"
