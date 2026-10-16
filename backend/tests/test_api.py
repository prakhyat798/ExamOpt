"""
ExamOpt — FastAPI Endpoints Test Suite
Verifies Phase 1 Data Endpoints, schedule generation, publishing, and personalized mobile endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"]["sqlite_connected"] is True


def test_data_summary():
    response = client.get("/api/data/summary")
    assert response.status_code == 200
    data = response.json()
    counts = data["counts"]
    assert counts["rooms"] == 15
    assert counts["timeslots"] == 10
    assert counts["subjects"] == 24
    assert counts["student_groups"] == 8
    assert counts["student_enrollments"] == 355
    assert counts["backlog_students"] == 70


def test_table_data_endpoint():
    response = client.get("/api/data/tables/rooms")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 15
    assert len(data["rows"]) == 15


def test_validation_endpoint():
    response = client.post("/api/data/validate")
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["readiness_score"] == 100


def test_schedule_generation_and_publishing():
    # 1. Generate schedule
    gen_resp = client.post("/api/v1/schedules/generate", json={"algorithm": "WELSH_POWELL"})
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["is_feasible"] is True
    assert gen_data["scheduled_exams"] == 24
    run_id = gen_data["run_id"]

    # 2. Publish schedule
    pub_resp = client.post(f"/api/v1/schedules/{run_id}/publish")
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert pub_data["is_active"] is True
    assert pub_data["version"] >= 1

    # 3. Active published timetable
    active_resp = client.get("/api/v1/schedules/active-published")
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert len(active_data["allocations"]) == 24


def test_student_and_faculty_mobile_views():
    # Student view
    st_resp = client.get("/api/v1/timetable/student?roll_no=GLA26-BCA-0001")
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert st_data["student"]["roll_no"] == "GLA26-BCA-0001"
    assert len(st_data["schedule"]) > 0

    # Faculty view
    fac_resp = client.get("/api/v1/timetable/faculty?faculty_id=FAC-101")
    assert fac_resp.status_code == 200
    fac_data = fac_resp.json()
    assert fac_data["faculty"]["faculty_id"] == "FAC-101"
