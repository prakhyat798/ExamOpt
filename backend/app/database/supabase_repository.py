"""
ExamOpt Supabase Cloud Repository Implementation
PostgREST HTTP REST adapter communicating with Supabase PostgreSQL cloud database.
Enforces authentic cloud communication without silent local fallbacks.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Tuple

import httpx

from app.database.base import DatabaseRepository
from app.database.config import DatabaseConfig
from app.database.exceptions import (
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    EntityNotFoundError,
    DatabaseIntegrityError
)


class SupabaseRepository(DatabaseRepository):
    """
    Cloud database repository communicating with Supabase PostgREST API.
    Preserves strict cloud boundary and surfaces errors transparently.
    """

    def __init__(self, config: DatabaseConfig, client: Optional[httpx.Client] = None):
        self.config = config
        self.config.validate()

        self.base_url = f"{self.config.supabase_url.rstrip('/')}/rest/v1"
        self.api_key = self.config.supabase_secret_key or self.config.supabase_publishable_key
        self._user_token: Optional[str] = None

        default_headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        self.client = client or httpx.Client(
            base_url=self.base_url,
            headers=default_headers,
            timeout=10.0
        )

    def _url(self, path: str) -> str:
        """Constructs an absolute URL for PostgREST endpoints."""
        clean_path = path.lstrip("/")
        return f"{self.base_url}/{clean_path}"

    def set_user_token(self, token: Optional[str]) -> None:
        """Sets an end-user JWT token to evaluate user-specific RLS policies."""
        self._user_token = token

    def _get_headers(self, prefer_count: bool = False, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self._user_token or self.api_key}",
            "Content-Type": "application/json"
        }
        if prefer_count:
            headers["Prefer"] = "count=exact"
        else:
            headers["Prefer"] = "return=representation"
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def _handle_response_error(self, response: httpx.Response, action_description: str) -> None:
        if response.status_code in (401, 403):
            raise DatabaseAuthenticationError(
                f"Authentication failed during {action_description}: HTTP {response.status_code} - {response.text}"
            )
        elif response.status_code == 404:
            raise EntityNotFoundError(
                f"Entity not found during {action_description}: HTTP 404 - {response.text}"
            )
        elif response.status_code in (409, 422):
            raise DatabaseIntegrityError(
                f"Integrity violation during {action_description}: HTTP {response.status_code} - {response.text}"
            )
        elif response.status_code >= 400:
            raise DatabaseConnectionError(
                f"Cloud database error during {action_description}: HTTP {response.status_code} - {response.text}"
            )

    def health_check(self) -> Dict[str, Any]:
        try:
            resp = self.client.get(self._url("/rooms?select=room_id&limit=1"), headers=self._get_headers())
            if resp.status_code == 200:
                return {
                    "backend": "supabase",
                    "is_cloud": True,
                    "connected": True,
                    "url": self.config.supabase_url,
                    "auth_configured": bool(self.api_key)
                }
            else:
                return {
                    "backend": "supabase",
                    "is_cloud": True,
                    "connected": False,
                    "error": f"HTTP {resp.status_code}: {resp.text}"
                }
        except httpx.RequestError as e:
            return {
                "backend": "supabase",
                "is_cloud": True,
                "connected": False,
                "error": f"Connection failed: {str(e)}"
            }

    def _get_table_count(self, table_name: str, query_filter: str = "") -> int:
        path = f"/{table_name}?select=*{'&' + query_filter if query_filter else ''}"
        headers = self._get_headers(prefer_count=True)
        headers["Range"] = "0-0"
        resp = self.client.get(self._url(path), headers=headers)
        self._handle_response_error(resp, f"counting rows in '{table_name}'")
        content_range = resp.headers.get("content-range", "")
        if "/" in content_range:
            try:
                return int(content_range.split("/")[1])
            except ValueError:
                pass
        try:
            return len(resp.json())
        except Exception:
            return 0

    def get_summary(self) -> Dict[str, Any]:
        try:
            rooms_resp = self.client.get(self._url("/rooms?select=room_type,capacity"), headers=self._get_headers())
            self._handle_response_error(rooms_resp, "fetching room capacities for summary")
            rooms = rooms_resp.json()

            total_theory = sum(r["capacity"] for r in rooms if r.get("room_type") == "THEORY")
            total_lab = sum(r["capacity"] for r in rooms if r.get("room_type") == "LAB")

            return {
                "counts": {
                    "rooms": len(rooms),
                    "timeslots": self._get_table_count("timeslots"),
                    "faculty": self._get_table_count("faculty"),
                    "subjects": self._get_table_count("subjects"),
                    "student_groups": self._get_table_count("student_groups"),
                    "student_enrollments": self._get_table_count("student_enrollments"),
                    "student_subject_enrollments": self._get_table_count("student_subject_enrollments"),
                    "backlog_students": self._get_table_count("student_enrollments", "has_backlog=eq.true")
                },
                "campus_capacity": {
                    "total_theory_seats": total_theory,
                    "total_lab_seats": total_lab,
                    "total_rooms": len(rooms)
                }
            }
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to communicate with Supabase: {e}") from e

    def get_table_data(self, table_name: str, limit: int = 500) -> Dict[str, Any]:
        allowed_tables = {
            "rooms", "timeslots", "faculty", "subjects",
            "student_groups", "student_enrollments", "student_subject_enrollments",
            "scheduling_runs", "scheduled_exams", "published_schedules", "schedule_conflicts"
        }
        if table_name not in allowed_tables:
            raise EntityNotFoundError(f"Table '{table_name}' is not allowed or not found.")

        try:
            resp = self.client.get(self._url(f"/{table_name}?select=*&limit={limit}"), headers=self._get_headers())
            self._handle_response_error(resp, f"fetching table '{table_name}'")
            rows = resp.json()
            return {"table": table_name, "count": len(rows), "rows": rows}
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to fetch table data from Supabase: {e}") from e

    def get_active_dataset_records(self) -> Tuple[
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]]
    ]:
        try:
            rooms = self.client.get(self._url("/rooms?select=*&limit=1000"), headers=self._get_headers()).json()
            timeslots = self.client.get(self._url("/timeslots?select=*&limit=1000"), headers=self._get_headers()).json()
            faculty = self.client.get(self._url("/faculty?select=*&limit=1000"), headers=self._get_headers()).json()
            subjects = self.client.get(self._url("/subjects?select=*&limit=1000"), headers=self._get_headers()).json()
            groups = self.client.get(self._url("/student_groups?select=*&limit=1000"), headers=self._get_headers()).json()
            enrollments = self.client.get(self._url("/student_enrollments?select=*&limit=5000"), headers=self._get_headers()).json()

            for s in subjects:
                s["requires_lab"] = 1 if s.get("requires_lab") in (True, 1, "true", "TRUE") else 0
            for e in enrollments:
                e["has_backlog"] = 1 if e.get("has_backlog") in (True, 1, "true", "TRUE") else 0

            return rooms, timeslots, faculty, subjects, groups, enrollments
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to fetch dataset from Supabase: {e}") from e

    def save_scheduling_run(
        self,
        run_data: Dict[str, Any],
        allocations: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> str:
        run_id = run_data["run_id"]
        try:
            run_payload = {
                "run_id": run_id,
                "algorithm": run_data["algorithm"],
                "status": run_data["status"],
                "total_exams": run_data["total_exams"],
                "scheduled_exams": run_data["scheduled_exams"],
                "unscheduled_exams": run_data["unscheduled_exams"],
                "hard_conflicts": run_data["hard_conflicts"],
                "soft_score": run_data["soft_score"],
                "execution_time_ms": run_data["execution_time_ms"],
                "metadata_json": run_data.get("metadata", {})
            }
            resp = self.client.post(self._url("/scheduling_runs"), json=run_payload, headers=self._get_headers())
            self._handle_response_error(resp, f"inserting scheduling run '{run_id}'")

            if allocations:
                alloc_payloads = []
                for alloc in allocations:
                    alloc_payloads.append({
                        "id": alloc.get("id") or f"ALLOC-{uuid.uuid4().hex[:8]}",
                        "run_id": run_id,
                        "subject_id": alloc["subject_id"],
                        "slot_id": alloc["slot_id"],
                        "room_id": alloc["room_id"],
                        "assigned_faculty_id": alloc.get("assigned_faculty_id"),
                        "assigned_students": alloc["assigned_students"]
                    })
                resp = self.client.post(self._url("/scheduled_exams"), json=alloc_payloads, headers=self._get_headers())
                self._handle_response_error(resp, f"inserting scheduled exams for run '{run_id}'")

            if conflicts:
                conf_payloads = []
                for conf in conflicts:
                    conf_payloads.append({
                        "run_id": run_id,
                        "conflict_type": conf["conflict_type"],
                        "subject_id_1": conf["subject_id_1"],
                        "description": conf["description"]
                    })
                resp = self.client.post(self._url("/schedule_conflicts"), json=conf_payloads, headers=self._get_headers())
                self._handle_response_error(resp, f"inserting conflicts for run '{run_id}'")

            return run_id
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to persist scheduling run to Supabase: {e}") from e

    def list_scheduling_runs(self) -> List[Dict[str, Any]]:
        try:
            resp = self.client.get(self._url("/scheduling_runs?select=*&order=created_at.desc"), headers=self._get_headers())
            self._handle_response_error(resp, "listing scheduling runs")
            return resp.json()
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to list scheduling runs from Supabase: {e}") from e

    def get_schedule_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        try:
            run_resp = self.client.get(self._url(f"/scheduling_runs?run_id=eq.{run_id}"), headers=self._get_headers())
            self._handle_response_error(run_resp, f"fetching run '{run_id}'")
            runs = run_resp.json()
            if not runs:
                return None
            run = runs[0]

            alloc_resp = self.client.get(self._url(f"/scheduled_exams?run_id=eq.{run_id}&order=slot_id.asc"), headers=self._get_headers())
            self._handle_response_error(alloc_resp, f"fetching allocations for run '{run_id}'")
            raw_allocs = alloc_resp.json()

            allocations = []
            if raw_allocs:
                subj_map = {s["subject_id"]: s for s in self.client.get(self._url("/subjects?select=*"), headers=self._get_headers()).json()}
                slot_map = {t["slot_id"]: t for t in self.client.get(self._url("/timeslots?select=*"), headers=self._get_headers()).json()}
                room_map = {r["room_id"]: r for r in self.client.get(self._url("/rooms?select=*"), headers=self._get_headers()).json()}
                fac_map = {f["faculty_id"]: f for f in self.client.get(self._url("/faculty?select=*"), headers=self._get_headers()).json()}

                for a in raw_allocs:
                    s = subj_map.get(a["subject_id"], {})
                    t = slot_map.get(a["slot_id"], {})
                    r = room_map.get(a["room_id"], {})
                    f = fac_map.get(a.get("assigned_faculty_id"), {})
                    allocations.append({
                        "id": a["id"],
                        "run_id": a["run_id"],
                        "subject_id": a["subject_id"],
                        "subject_name": s.get("name", a["subject_id"]),
                        "program": s.get("program", ""),
                        "semester": s.get("semester", 1),
                        "duration_hours": s.get("duration_hours", 3),
                        "requires_lab": s.get("requires_lab", False),
                        "slot_id": a["slot_id"],
                        "exam_date": t.get("exam_date", ""),
                        "session": t.get("session", ""),
                        "time_range": t.get("time_range", ""),
                        "room_id": a["room_id"],
                        "room_name": r.get("name", a["room_id"]),
                        "room_capacity": r.get("capacity", 0),
                        "assigned_faculty_id": a.get("assigned_faculty_id"),
                        "assigned_faculty_name": f.get("name") if f else None,
                        "assigned_students": a.get("assigned_students", 0)
                    })

            conf_resp = self.client.get(self._url(f"/schedule_conflicts?run_id=eq.{run_id}"), headers=self._get_headers())
            self._handle_response_error(conf_resp, f"fetching conflicts for run '{run_id}'")
            conflicts = conf_resp.json()

            return {
                "run": run,
                "allocations": allocations,
                "conflicts": conflicts
            }
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to fetch run details from Supabase: {e}") from e

    def publish_schedule(self, run_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        try:
            run_resp = self.client.get(self._url(f"/scheduling_runs?run_id=eq.{run_id}"), headers=self._get_headers())
            self._handle_response_error(run_resp, f"checking run '{run_id}' for publication")
            runs = run_resp.json()
            if not runs:
                raise EntityNotFoundError(f"Run '{run_id}' not found.")
            run = runs[0]

            if run.get("hard_conflicts", 0) > 0 or run.get("status") != "FEASIBLE":
                raise DatabaseIntegrityError(
                    f"Cannot publish schedule '{run_id}' with status '{run.get('status')}' and {run.get('hard_conflicts')} hard conflicts!"
                )

            patch_resp = self.client.patch(
                self._url("/published_schedules?is_active=eq.true"),
                json={"is_active": False},
                headers=self._get_headers()
            )
            self._handle_response_error(patch_resp, "deactivating prior published schedules")

            ver_resp = self.client.get(self._url("/published_schedules?select=version&order=version.desc&limit=1"), headers=self._get_headers())
            self._handle_response_error(ver_resp, "querying latest publication version")
            vers = ver_resp.json()
            new_version = (vers[0]["version"] + 1) if vers else 1

            pub_id = f"PUB-V{new_version}-{uuid.uuid4().hex[:6]}"
            pub_title = title or f"GLA University Autumn 2026 Examination Timetable (Version {new_version})"

            pub_payload = {
                "published_id": pub_id,
                "version": new_version,
                "run_id": run_id,
                "title": pub_title,
                "is_active": True
            }
            create_resp = self.client.post(self._url("/published_schedules"), json=pub_payload, headers=self._get_headers())
            self._handle_response_error(create_resp, "creating published schedule record")

            return {
                "message": f"Schedule '{run_id}' successfully published as Version {new_version}.",
                "published_id": pub_id,
                "version": new_version,
                "run_id": run_id,
                "title": pub_title,
                "is_active": True
            }
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to publish schedule on Supabase: {e}") from e

    def get_active_published_schedule(self) -> Optional[Dict[str, Any]]:
        try:
            pub_resp = self.client.get(self._url("/published_schedules?is_active=eq.true&order=version.desc&limit=1"), headers=self._get_headers())
            self._handle_response_error(pub_resp, "fetching active published schedule")
            pubs = pub_resp.json()
            if not pubs:
                return None
            pub = pubs[0]
            run_id = pub["run_id"]
            details = self.get_schedule_run_details(run_id)
            if details:
                details["publication"] = pub
            return details
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to fetch active schedule from Supabase: {e}") from e

    def get_student_timetable(self, roll_no: str) -> Optional[Dict[str, Any]]:
        try:
            st_resp = self.client.get(self._url(f"/student_enrollments?roll_no=eq.{roll_no}"), headers=self._get_headers())
            self._handle_response_error(st_resp, f"fetching student '{roll_no}'")
            students = st_resp.json()
            if not students:
                return None
            student_dict = students[0]
            enrolled_subj_ids = set(s.strip() for s in student_dict.get("enrolled_subject_ids", "").split(",") if s.strip())

            active_pub = self.get_active_published_schedule()
            allocations = active_pub.get("allocations", []) if active_pub else []

            student_exams = [a for a in allocations if a["subject_id"] in enrolled_subj_ids]
            student_exams.sort(key=lambda x: (x["exam_date"], x["slot_id"]))

            return {
                "student": student_dict,
                "total_enrolled_exams": len(enrolled_subj_ids),
                "scheduled_exams_count": len(student_exams),
                "schedule": student_exams
            }
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to fetch student timetable from Supabase: {e}") from e

    def get_faculty_timetable(self, faculty_id: str) -> Optional[Dict[str, Any]]:
        try:
            fac_resp = self.client.get(self._url(f"/faculty?faculty_id=eq.{faculty_id}"), headers=self._get_headers())
            self._handle_response_error(fac_resp, f"fetching faculty '{faculty_id}'")
            faculties = fac_resp.json()
            if not faculties:
                return None
            faculty_dict = faculties[0]

            active_pub = self.get_active_published_schedule()
            allocations = active_pub.get("allocations", []) if active_pub else []

            assigned_duties = [a for a in allocations if a.get("assigned_faculty_id") == faculty_id]
            assigned_duties.sort(key=lambda x: (x["exam_date"], x["slot_id"]))

            return {
                "faculty": faculty_dict,
                "assigned_duties_count": len(assigned_duties),
                "max_duties": faculty_dict.get("max_duties", 4),
                "duties": assigned_duties
            }
        except httpx.RequestError as e:
            raise DatabaseConnectionError(f"Failed to fetch faculty timetable from Supabase: {e}") from e
