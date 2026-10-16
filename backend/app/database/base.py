"""
ExamOpt Abstract Database Repository
Defines the unified repository contract for both SQLite (local) and Supabase (cloud).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple


class DatabaseRepository(ABC):
    """Abstract interface for ExamOpt data operations."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Checks connectivity and returns status of the database backend."""
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """Returns entity counts and campus seat capacity metrics."""
        pass

    @abstractmethod
    def get_table_data(self, table_name: str, limit: int = 500) -> Dict[str, Any]:
        """Retrieves rows for a specified table."""
        pass

    @abstractmethod
    def get_active_dataset_records(self) -> Tuple[
        List[Dict[str, Any]],  # rooms
        List[Dict[str, Any]],  # timeslots
        List[Dict[str, Any]],  # faculty
        List[Dict[str, Any]],  # subjects
        List[Dict[str, Any]],  # groups
        List[Dict[str, Any]]   # enrollments
    ]:
        """Fetches all foundational records required for timetable scheduling."""
        pass

    @abstractmethod
    def save_scheduling_run(
        self,
        run_data: Dict[str, Any],
        allocations: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> str:
        """Persists a generated candidate schedule run, allocations, and conflicts."""
        pass

    @abstractmethod
    def list_scheduling_runs(self) -> List[Dict[str, Any]]:
        """Lists historical scheduling runs."""
        pass

    @abstractmethod
    def get_schedule_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata, full room-faculty allocations, and conflicts for a run."""
        pass

    @abstractmethod
    def publish_schedule(self, run_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Atomically publishes a candidate schedule and deactivates prior versions."""
        pass

    @abstractmethod
    def get_active_published_schedule(self) -> Optional[Dict[str, Any]]:
        """Retrieves the currently active published timetable."""
        pass

    @abstractmethod
    def get_student_timetable(self, roll_no: str) -> Optional[Dict[str, Any]]:
        """Returns personalized exam schedule for a specific student's roll number."""
        pass

    @abstractmethod
    def get_faculty_timetable(self, faculty_id: str) -> Optional[Dict[str, Any]]:
        """Returns assigned examination duties for a specific faculty member."""
        pass
