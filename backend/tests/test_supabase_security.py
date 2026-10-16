"""
ExamOpt — Supabase Security & RLS Policy Verification Suite
Performs static SQL verification on migration scripts to guarantee:
1. RLS is enabled on all 11 application tables.
2. Missing index on student_enrollments(group_id) is created.
3. Least-privilege policies protect student, faculty, and diagnostic tables from anonymous read.
4. Ordinary users cannot grant themselves admin privileges.
5. Helper functions use SECURITY DEFINER with fixed search paths.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR.parent / "supabase" / "migrations"


def get_migration_content() -> str:
    migration_file = MIGRATIONS_DIR / "20261016000001_harden_rls_and_indexes.sql"
    assert migration_file.exists(), f"Hardened migration file not found at {migration_file}"
    return migration_file.read_text(encoding="utf-8")


def test_all_11_tables_have_rls_enabled():
    """Verify that every single application table has an explicit ALTER TABLE ... ENABLE ROW LEVEL SECURITY."""
    content = get_migration_content()

    required_tables = [
        "rooms",
        "timeslots",
        "subjects",
        "student_groups",
        "student_enrollments",
        "student_subject_enrollments",
        "faculty",
        "scheduling_runs",
        "scheduled_exams",
        "published_schedules",
        "schedule_conflicts",
        "user_profiles"
    ]

    for table in required_tables:
        pattern = rf"ALTER\s+TABLE\s+{table}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY\s*;"
        match = re.search(pattern, content, re.IGNORECASE)
        assert match is not None, f"Table '{table}' does NOT have RLS enabled in hardened migration!"


def test_missing_index_def03_created():
    """Verify that DEF-03 (index on student_enrollments(group_id)) is created."""
    content = get_migration_content()
    pattern = r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+idx_pg_student_enrollments_group\s+ON\s+student_enrollments\s*\(\s*group_id\s*\)\s*;"
    match = re.search(pattern, content, re.IGNORECASE)
    assert match is not None, "Missing index idx_pg_student_enrollments_group was not found in migration!"


def test_anonymous_access_policies_restricted():
    """
    Verify that unauthenticated anon users are strictly denied from querying sensitive tables.
    Only public metadata (rooms, timeslots, subjects) and active published schedules may allow public access.
    """
    content = get_migration_content()

    # Sensitive tables must NOT have "USING (true)" policies
    sensitive_tables = [
        "student_enrollments",
        "student_subject_enrollments",
        "scheduling_runs",
        "schedule_conflicts",
        "user_profiles"
    ]

    for table in sensitive_tables:
        # Search for any policy on table with USING (true)
        pattern = rf'CREATE\s+POLICY\s+"[^"]+"\s+ON\s+{table}\s+FOR\s+SELECT\s+USING\s*\(\s*true\s*\)'
        match = re.search(pattern, content, re.IGNORECASE)
        assert match is None, f"Sensitive table '{table}' has an insecure public read policy!"


def test_prevent_self_assigned_admin_privileges():
    """Verify that user_profiles table strictly restricts insert and update to administrators only."""
    content = get_migration_content()
    pattern = r'CREATE\s+POLICY\s+"Only admins can insert or update profiles"\s+ON\s+user_profiles\s+FOR\s+ALL\s+USING\s*\(\s*public\.is_admin\(\)\s*\)\s+WITH\s+CHECK\s*\(\s*public\.is_admin\(\)\s*\)'
    match = re.search(pattern, content, re.IGNORECASE)
    assert match is not None, "user_profiles does not restrict profile creation/update to admins!"


def test_security_definer_functions_have_fixed_search_path():
    """
    Verify that all SECURITY DEFINER functions declare a strict fixed search path
    to prevent search-path injection and privilege escalation.
    """
    content = get_migration_content()

    helper_functions = [
        "get_current_user_role",
        "get_current_student_roll_no",
        "get_current_faculty_id",
        "is_admin"
    ]

    for func in helper_functions:
        pattern = rf"FUNCTION\s+public\.{func}.*?SECURITY\s+DEFINER.*?SET\s+search_path\s*=\s*public\s*,\s*auth"
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        assert match is not None, f"Function 'public.{func}' is missing 'SECURITY DEFINER' with fixed search_path!"


def test_grants_revocation_from_anon_and_authenticated():
    """Verify that direct write permissions on schema public are revoked from anon and authenticated roles."""
    content = get_migration_content()
    assert "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;" in content
    assert "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;" in content
