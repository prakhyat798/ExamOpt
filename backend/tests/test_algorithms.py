"""
ExamOpt — Scheduling Algorithms Test Suite
Verifies conflict graph, First-Fit baseline, Welsh-Powell coloring, and Constraint Backtracking.
"""

import pytest
import sqlite3
from pathlib import Path
from main import get_active_dataset_records
from app.algorithms.conflict_graph import SubjectConflictGraph
from app.algorithms.baseline_first_fit import FirstFitScheduler
from app.algorithms.welsh_powell import WelshPowellScheduler
from app.algorithms.backtracking import ConstraintBacktrackingScheduler
from app.services.optimizer import TimetableOptimizerService


@pytest.fixture
def dataset():
    rooms, timeslots, faculty, subjects, groups, enrollments = get_active_dataset_records()
    return {
        "rooms": rooms,
        "timeslots": timeslots,
        "faculty": faculty,
        "subjects": subjects,
        "groups": groups,
        "enrollments": enrollments
    }


def test_conflict_graph_backlog_edges(dataset):
    """Verify that backlog cohorts produce real cross-semester conflict edges."""
    graph = SubjectConflictGraph(dataset["subjects"], dataset["enrollments"])
    # BCA-101 and MCA-101 share bridge students from GRP-BL-MCA-BCA
    assert "BCA-101" in graph.get_conflicts("MCA-101")
    assert graph.get_shared_count("MCA-101", "BCA-101") == 20

    # BCADS-301 and BCADS-501 share backlog students from GRP-BL-S5-S3
    assert "BCADS-301" in graph.get_conflicts("BCADS-501")
    assert graph.get_shared_count("BCADS-501", "BCADS-301") == 25


def test_welsh_powell_produces_no_student_clashes(dataset):
    """Verify that Welsh-Powell produces a timetable where no conflicting exams share a slot."""
    scheduler = WelshPowellScheduler(
        dataset["subjects"], dataset["rooms"], dataset["timeslots"], dataset["faculty"], dataset["enrollments"]
    )
    res = scheduler.solve()
    assert res["is_feasible"] is True
    assert res["hard_conflicts"] == 0
    assert res["scheduled_exams"] == len(dataset["subjects"])

    # Double-check conflict graph constraints
    graph = scheduler.conflict_graph
    slot_map = {}
    for a in res["allocations"]:
        slot_map[a["subject_id"]] = a["slot_id"]

    for u in graph.subjects:
        for v in graph.get_conflicts(u):
            assert slot_map[u] != slot_map[v], f"Clash detected between {u} and {v} in slot {slot_map[u]}!"


def test_backtracking_solver_correctness(dataset):
    """Verify that constraint backtracking finds a valid clash-free timetable."""
    scheduler = ConstraintBacktrackingScheduler(
        dataset["subjects"], dataset["rooms"], dataset["timeslots"], dataset["faculty"], dataset["enrollments"]
    )
    res = scheduler.solve()
    assert res["is_feasible"] is True
    assert res["hard_conflicts"] == 0
    assert res["scheduled_exams"] == len(dataset["subjects"])
    assert res["nodes_explored"] > 0

    # Verify room capacities are never exceeded
    for a in res["allocations"]:
        assert a["room_capacity"] >= a["assigned_students"]
        if a["requires_lab"]:
            assert "LAB" in a["room_id"]


def test_algorithm_benchmark_comparison(dataset):
    """Verify comparison benchmark executes all 3 algorithms and computes comparative metrics."""
    service = TimetableOptimizerService(
        dataset["subjects"], dataset["rooms"], dataset["timeslots"], dataset["faculty"], dataset["enrollments"]
    )
    comp = service.compare_all()
    assert "comparison" in comp
    assert len(comp["comparison"]) == 3

    alg_names = {c["algorithm"] for c in comp["comparison"]}
    assert "FIRST_FIT" in alg_names
    assert "WELSH_POWELL" in alg_names
    assert "BACKTRACKING" in alg_names
