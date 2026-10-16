"""
ExamOpt — Database Adapters Test Suite
Verifies backend selection (SQLite vs Supabase), error propagation, non-leakage of secrets,
and mocked Supabase PostgREST cloud operations.
"""

import os
import pytest
import httpx
from pathlib import Path

from app.database import (
    DatabaseBackend,
    DatabaseConfig,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    EntityNotFoundError,
    DatabaseIntegrityError,
    SQLiteRepository,
    SupabaseRepository,
    get_repository,
    reset_repository
)


@pytest.fixture(autouse=True)
def clean_repo_state():
    reset_repository()
    # Save original env
    orig_backend = os.environ.get("DATABASE_BACKEND")
    orig_url = os.environ.get("SUPABASE_URL")
    orig_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    orig_secret = os.environ.get("SUPABASE_SECRET_KEY")

    yield

    # Restore original env
    reset_repository()
    for var, val in [
        ("DATABASE_BACKEND", orig_backend),
        ("SUPABASE_URL", orig_url),
        ("SUPABASE_PUBLISHABLE_KEY", orig_key),
        ("SUPABASE_SECRET_KEY", orig_secret)
    ]:
        if val is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = val


def test_adapter_selection_sqlite():
    """Verify SQLite backend is chosen by default and reports safe status without secrets."""
    os.environ["DATABASE_BACKEND"] = "sqlite"
    cfg = DatabaseConfig()
    assert cfg.backend == DatabaseBackend.SQLITE

    repo = get_repository(cfg, force_refresh=True)
    assert isinstance(repo, SQLiteRepository)

    status = cfg.get_safe_status()
    assert status["configured_backend"] == "sqlite"
    assert status["is_cloud"] is False
    assert "password" not in status
    assert "secret" not in status


def test_adapter_selection_supabase_valid():
    """Verify Supabase cloud adapter is selected when configured, with safe status."""
    cfg = DatabaseConfig(
        backend="supabase",
        supabase_url="https://mock-proj.supabase.co",
        supabase_publishable_key="mock-anon-key"
    )
    assert cfg.backend == DatabaseBackend.SUPABASE

    repo = get_repository(cfg, force_refresh=True)
    assert isinstance(repo, SupabaseRepository)
    assert repo.base_url == "https://mock-proj.supabase.co/rest/v1"

    status = cfg.get_safe_status()
    assert status["configured_backend"] == "supabase"
    assert status["is_cloud"] is True
    assert status["supabase"]["configured"] is True
    # Ensure raw secret is NOT leaked in status
    assert "mock-anon-key" not in str(status)


def test_unsupported_backend_raises_configuration_error():
    """Verify choosing an invalid backend raises a clear ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc_info:
        DatabaseConfig(backend="invalid_engine")
    assert "Unsupported DATABASE_BACKEND" in str(exc_info.value)


def test_missing_supabase_config_raises_configuration_error():
    """Verify Supabase mode fails explicitly without falling back to SQLite when credentials are missing."""
    os.environ["DATABASE_BACKEND"] = "supabase"
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
    os.environ.pop("SUPABASE_SECRET_KEY", None)

    with pytest.raises(ConfigurationError) as exc_info:
        get_repository(force_refresh=True)
    assert "Supabase configuration missing" in str(exc_info.value)


def test_supabase_cloud_connection_failure_reported():
    """Verify cloud connection failure is reported and does not silently substitute SQLite data."""
    cfg = DatabaseConfig(
        backend="supabase",
        supabase_url="https://unreachable-domain-12345.supabase.co",
        supabase_publishable_key="mock-key"
    )
    repo = SupabaseRepository(cfg)
    health = repo.health_check()
    assert health["backend"] == "supabase"
    assert health["is_cloud"] is True
    assert health["connected"] is False
    assert "error" in health

    # Trying to fetch data through an unreachable endpoint raises DatabaseConnectionError
    with pytest.raises(DatabaseConnectionError):
        repo.get_summary()


def test_supabase_repository_mocked_rest_operations():
    """
    Unit test: Verify SupabaseRepository CRUD operations using a mocked PostgREST HTTP transport.
    [Clearly Labeled: Mocked Network Transport]
    """
    mock_rooms = [{"room_id": "R101", "name": "Room 101", "room_type": "THEORY", "capacity": 60, "unavailable_slots": ""}]
    mock_slots = [{"slot_id": "D1-M", "day_number": 1, "exam_date": "2026-10-19", "session": "MORNING", "time_range": "09:30 AM - 12:30 PM"}]
    mock_faculty = [{"faculty_id": "F01", "name": "Prof A", "department": "CSED", "unavailable_slots": "", "max_duties": 4}]
    mock_subjects = [{"subject_id": "BCA-101", "name": "C Programming", "program": "BCA", "semester": 1, "duration_hours": 3, "requires_lab": False}]
    mock_groups = [{"group_id": "GRP-1", "name": "BCA Sem 1", "program": "BCA", "semester": 1, "is_backlog_group": False, "student_count": 45}]
    mock_enrollments = [{"roll_no": "GLA-001", "student_name": "Student A", "group_id": "GRP-1", "enrolled_subject_ids": "BCA-101", "has_backlog": False}]

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method

        if "/rooms" in url and method == "GET":
            return httpx.Response(200, json=mock_rooms, headers={"content-range": "0-0/1"})
        elif "/timeslots" in url and method == "GET":
            return httpx.Response(200, json=mock_slots, headers={"content-range": "0-0/1"})
        elif "/faculty" in url and method == "GET":
            return httpx.Response(200, json=mock_faculty, headers={"content-range": "0-0/1"})
        elif "/subjects" in url and method == "GET":
            return httpx.Response(200, json=mock_subjects, headers={"content-range": "0-0/1"})
        elif "/student_groups" in url and method == "GET":
            return httpx.Response(200, json=mock_groups, headers={"content-range": "0-0/1"})
        elif "/student_enrollments" in url and method == "GET":
            return httpx.Response(200, json=mock_enrollments, headers={"content-range": "0-0/1"})
        elif "/student_subject_enrollments" in url and method == "GET":
            return httpx.Response(200, json=[], headers={"content-range": "0-0/1"})
        elif "/scheduling_runs" in url and method == "POST":
            return httpx.Response(201, json=[{"run_id": "RUN-TEST-001"}])
        elif "/scheduled_exams" in url and method == "POST":
            return httpx.Response(201, json=[])
        elif "/schedule_conflicts" in url and method == "POST":
            return httpx.Response(201, json=[])
        elif "/schedule_conflicts" in url and method == "GET":
            return httpx.Response(200, json=[])
        elif "/published_schedules" in url and method == "PATCH":
            return httpx.Response(200, json=[])
        elif "/published_schedules" in url and method == "GET":
            return httpx.Response(200, json=[{"published_id": "PUB-V1-123456", "version": 1, "run_id": "RUN-TEST-001", "is_active": True}])
        elif "/published_schedules" in url and method == "POST":
            return httpx.Response(201, json=[{"published_id": "PUB-V2-654321", "version": 2, "is_active": True}])
        elif "/scheduling_runs" in url and method == "GET":
            return httpx.Response(200, json=[{"run_id": "RUN-TEST-001", "status": "FEASIBLE", "hard_conflicts": 0}])
        elif "/scheduled_exams" in url and method == "GET":
            return httpx.Response(200, json=[{
                "id": "ALLOC-1", "run_id": "RUN-TEST-001", "subject_id": "BCA-101",
                "slot_id": "D1-M", "room_id": "R101", "assigned_faculty_id": "F01", "assigned_students": 45
            }])
        return httpx.Response(404, json={"message": "Not Found"})

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    cfg = DatabaseConfig(
        backend="supabase",
        supabase_url="https://mock-proj.supabase.co",
        supabase_publishable_key="mock-key"
    )
    repo = SupabaseRepository(cfg, client=client)

    # 1. Test health check
    health = repo.health_check()
    assert health["connected"] is True
    assert health["backend"] == "supabase"

    # 2. Test get_active_dataset_records
    rooms, slots, fac, subjs, grps, enrs = repo.get_active_dataset_records()
    assert len(rooms) == 1
    assert len(subjs) == 1
    assert subjs[0]["requires_lab"] == 0  # Normalized to int for algorithms

    # 3. Test save_scheduling_run
    run_id = repo.save_scheduling_run(
        {
            "run_id": "RUN-TEST-001", "algorithm": "FIRST_FIT", "status": "FEASIBLE",
            "total_exams": 1, "scheduled_exams": 1, "unscheduled_exams": 0,
            "hard_conflicts": 0, "soft_score": 80.0, "execution_time_ms": 12.5
        },
        allocations=[{"subject_id": "BCA-101", "slot_id": "D1-M", "room_id": "R101", "assigned_students": 45}],
        conflicts=[]
    )
    assert run_id == "RUN-TEST-001"

    # 4. Test publish_schedule
    pub = repo.publish_schedule("RUN-TEST-001")
    assert pub["is_active"] is True
    assert pub["version"] == 2

    # 5. Test student personalized schedule
    st_sched = repo.get_student_timetable("GLA-001")
    assert st_sched is not None
    assert st_sched["student"]["roll_no"] == "GLA-001"
    assert len(st_sched["schedule"]) == 1

    # 6. Test faculty personalized schedule
    fac_sched = repo.get_faculty_timetable("F01")
    assert fac_sched is not None
    assert fac_sched["faculty"]["faculty_id"] == "F01"
    assert len(fac_sched["duties"]) == 1


def test_supabase_error_handling_mappings():
    """Verify HTTP status codes from Supabase are mapped to typed Database exceptions."""
    cfg = DatabaseConfig(
        backend="supabase",
        supabase_url="https://mock-proj.supabase.co",
        supabase_publishable_key="mock-key"
    )

    # 1. Test 401 Authentication Error
    client_401 = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(401, json={"message": "Invalid API key"})))
    repo_401 = SupabaseRepository(cfg, client=client_401)
    with pytest.raises(DatabaseAuthenticationError):
        repo_401.get_table_data("rooms")

    # 2. Test 404 Entity Not Found
    client_404 = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(404, json={"message": "Row not found"})))
    repo_404 = SupabaseRepository(cfg, client=client_404)
    with pytest.raises(EntityNotFoundError):
        repo_404.get_table_data("rooms")

    # 3. Test 409 Integrity Error
    client_409 = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(409, json={"message": "Duplicate key violation"})))
    repo_409 = SupabaseRepository(cfg, client=client_409)
    with pytest.raises(DatabaseIntegrityError):
        repo_409.get_table_data("rooms")

    # 4. Direct handler unit testing for 403 and 422
    resp_403 = httpx.Response(403, text="Forbidden")
    with pytest.raises(DatabaseAuthenticationError):
        repo_401._handle_response_error(resp_403, "testing 403")

    resp_422 = httpx.Response(422, text="Unprocessable Entity")
    with pytest.raises(DatabaseIntegrityError):
        repo_401._handle_response_error(resp_422, "testing 422")

