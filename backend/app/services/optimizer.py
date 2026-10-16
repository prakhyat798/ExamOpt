"""
ExamOpt — Timetable Optimization & Multi-Algorithm Benchmark Service
Executes and compares First-Fit Baseline, Welsh-Powell Coloring, and Constraint Backtracking.
"""

from typing import Dict, List, Any, Optional
from ..algorithms.baseline_first_fit import FirstFitScheduler
from ..algorithms.welsh_powell import WelshPowellScheduler
from ..algorithms.backtracking import ConstraintBacktrackingScheduler


class TimetableOptimizerService:
    """Orchestrates timetable scheduling algorithms and computes comparative metrics."""

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
        self.timeslots = timeslots
        self.faculty = faculty
        self.enrollments = enrollments

    def run_algorithm(self, algorithm_name: str) -> Dict[str, Any]:
        """Runs a single designated algorithm."""
        alg = algorithm_name.upper().replace("-", "_")

        if alg == "FIRST_FIT":
            scheduler = FirstFitScheduler(
                self.subjects, self.rooms, self.timeslots, self.faculty, self.enrollments
            )
            result = scheduler.solve()
        elif alg == "WELSH_POWELL":
            scheduler = WelshPowellScheduler(
                self.subjects, self.rooms, self.timeslots, self.faculty, self.enrollments
            )
            result = scheduler.solve()
        elif alg in ("BACKTRACKING", "CONSTRAINT_BACKTRACKING"):
            scheduler = ConstraintBacktrackingScheduler(
                self.subjects, self.rooms, self.timeslots, self.faculty, self.enrollments
            )
            result = scheduler.solve()
        else:
            raise ValueError(f"Unknown algorithm '{algorithm_name}'. Expected FIRST_FIT, WELSH_POWELL, or BACKTRACKING.")

        # Compute soft score
        result["soft_score"] = self._compute_soft_score(result)
        return result

    def compare_all(self) -> Dict[str, Any]:
        """Executes all three algorithms on the exact same dataset and returns side-by-side comparison."""
        first_fit_res = self.run_algorithm("FIRST_FIT")
        welsh_powell_res = self.run_algorithm("WELSH_POWELL")
        backtracking_res = self.run_algorithm("BACKTRACKING")

        comparison_table = [
            self._extract_metrics(first_fit_res),
            self._extract_metrics(welsh_powell_res),
            self._extract_metrics(backtracking_res)
        ]

        # Determine winner based on feasibility, soft score, and room utilization
        feasible_runs = [r for r in comparison_table if r["is_feasible"]]
        best_run = max(feasible_runs, key=lambda r: (r["soft_score"], r["room_utilization_pct"])) if feasible_runs else comparison_table[0]

        return {
            "summary": {
                "total_exams_to_schedule": len(self.subjects),
                "total_available_slots": len(self.timeslots),
                "total_available_rooms": len(self.rooms),
                "best_performing_algorithm": best_run["algorithm"],
                "best_soft_score": best_run["soft_score"]
            },
            "comparison": comparison_table,
            "detailed_results": {
                "FIRST_FIT": first_fit_res,
                "WELSH_POWELL": welsh_powell_res,
                "BACKTRACKING": backtracking_res
            }
        }

    def _extract_metrics(self, res: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "algorithm": res["algorithm"],
            "status": res["status"],
            "is_feasible": res["is_feasible"],
            "scheduled_exams": res["scheduled_exams"],
            "unscheduled_exams": res["unscheduled_exams"],
            "hard_conflicts": res["hard_conflicts"],
            "slots_used": res["slots_used"],
            "room_utilization_pct": res["room_utilization_pct"],
            "unused_capacity_seats": res["unused_capacity_seats"],
            "execution_time_ms": res["execution_time_ms"],
            "soft_score": res["soft_score"]
        }

    def _compute_soft_score(self, res: Dict[str, Any]) -> float:
        """
        Calculates normalized soft objective score (0 to 100):
        + Higher room utilization percentage (40% weight)
        + Compact slots utilization (30% weight: using fewer slots out of total available)
        + Zero unscheduled examinations (30% weight)
        """
        if not res.get("is_feasible", False):
            # Penalty for infeasibility
            scheduled_ratio = res.get("scheduled_exams", 0) / max(1, res.get("total_exams", 1))
            return round(scheduled_ratio * 40.0, 2)

        util_score = min(100.0, res.get("room_utilization_pct", 0.0)) * 0.40
        
        total_slots = max(1, len(self.timeslots))
        slots_used = res.get("slots_used", total_slots)
        slot_efficiency = max(0.0, (1.0 - (slots_used / total_slots))) * 100.0 * 0.30

        completeness_score = 30.0

        return round(util_score + slot_efficiency + completeness_score, 2)
