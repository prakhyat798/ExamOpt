"""
ExamOpt — Conflict Graph Construction Module
Constructs the subject conflict graph based on shared student enrollments.
Backlog students across semesters automatically produce cross-semester conflict edges.
"""

from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


class SubjectConflictGraph:
    """Represents an undirected weighted graph of examination subjects."""

    def __init__(self, subjects: List[Dict[str, Any]], enrollments: List[Dict[str, Any]]):
        self.subjects = {s["subject_id"]: s for s in subjects}
        self.adj: Dict[str, Set[str]] = {s_id: set() for s_id in self.subjects}
        self.edge_weights: Dict[Tuple[str, str], int] = defaultdict(int)
        self.shared_students: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        self._build_graph(enrollments)

    def _build_graph(self, enrollments: List[Dict[str, Any]]):
        # Map student roll_no to set of enrolled subject_ids
        student_courses: Dict[str, List[str]] = defaultdict(list)
        for row in enrollments:
            roll_no = row["roll_no"]
            subj_ids_str = row.get("enrolled_subject_ids", "")
            if isinstance(subj_ids_str, str):
                s_list = [s.strip() for s in subj_ids_str.split(",") if s.strip()]
            elif isinstance(subj_ids_str, list):
                s_list = subj_ids_str
            else:
                s_list = []

            for s_id in s_list:
                if s_id in self.subjects:
                    student_courses[roll_no].append(s_id)

        # For every student, add edges between every pair of their courses
        for roll_no, courses in student_courses.items():
            n = len(courses)
            for i in range(n):
                for j in range(i + 1, n):
                    u, v = courses[i], courses[j]
                    if u != v:
                        self.adj[u].add(v)
                        self.adj[v].add(u)
                        edge_key = tuple(sorted([u, v]))
                        self.edge_weights[edge_key] += 1
                        self.shared_students[edge_key].append(roll_no)

    def get_conflicts(self, subject_id: str) -> Set[str]:
        """Returns the set of conflicting subject IDs."""
        return self.adj.get(subject_id, set())

    def get_shared_count(self, u: str, v: str) -> int:
        """Returns the number of students enrolled in both u and v."""
        edge_key = tuple(sorted([u, v]))
        return self.edge_weights.get(edge_key, 0)

    def get_shared_students(self, u: str, v: str) -> List[str]:
        """Returns roll numbers of students enrolled in both u and v."""
        edge_key = tuple(sorted([u, v]))
        return self.shared_students.get(edge_key, [])

    def get_degree(self, subject_id: str) -> int:
        """Returns the number of conflicting neighbors (graph degree)."""
        return len(self.adj.get(subject_id, set()))

    def get_weighted_degree(self, subject_id: str) -> int:
        """Returns the sum of shared student weights across all incident edges."""
        return sum(self.get_shared_count(subject_id, neighbor) for neighbor in self.adj.get(subject_id, set()))

    def get_sorted_by_degree(self, descending: bool = True) -> List[str]:
        """Returns subject IDs sorted by degree, tie-broken deterministically by subject_id."""
        return sorted(
            self.subjects.keys(),
            key=lambda s: (self.get_degree(s), self.get_weighted_degree(s), s),
            reverse=descending
        )
