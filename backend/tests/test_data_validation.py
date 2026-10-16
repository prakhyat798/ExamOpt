"""
ExamOpt — Data Validation Test Suite
Verifies data quality validation engine, foreign keys, constraints, and edge-case detection.
"""

import pytest
import sqlite3
from pathlib import Path
from validator import DataQualityValidator, validate_sqlite_database, validate_csv_file

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "examopt.db"
DATASETS_DIR = BASE_DIR / "sample_datasets"


def test_sqlite_normal_dataset_readiness():
    """Verify that normal GLA dataset passes with 100 Readiness Score and 0 errors."""
    assert DB_PATH.exists(), "examopt.db must exist before testing."
    report = validate_sqlite_database(str(DB_PATH))
    assert report["is_valid"] is True
    assert report["status"] == "READY_FOR_OPTIMIZATION"
    assert report["readiness_score"] == 100
    assert len(report["errors"]) == 0


def test_corrupted_input_rejection():
    """Verify detection of duplicate IDs, negative numbers, contradictory slots, and non-existent slots."""
    corrupt_csv = DATASETS_DIR / "invalid_corrupted_input.csv"
    assert corrupt_csv.exists()
    report = validate_csv_file(str(corrupt_csv), table_type="subjects")

    assert report["is_valid"] is False
    assert report["status"] == "VALIDATION_FAILED"

    error_codes = {e["code"] for e in report["errors"]}
    assert "DUPLICATE_SUBJECT_ID" in error_codes
    assert "NEGATIVE_ENROLLMENT" in error_codes
    assert "CONTRADICTORY_CONSTRAINTS" in error_codes
    assert "FOREIGN_KEY_NOT_FOUND" in error_codes


def test_lab_bottleneck_detection():
    """Verify detection of lab demand bottleneck when exams exceed specialized lab count."""
    lab_csv = DATASETS_DIR / "edge_case_lab_bottleneck.csv"
    assert lab_csv.exists()
    report = validate_csv_file(str(lab_csv), table_type="subjects")

    assert report["is_valid"] is False
    error_codes = {e["code"] for e in report["errors"]}
    assert "LAB_BOTTLENECK" in error_codes


def test_capacity_overflow_detection():
    """Verify detection of mega-course exceeding largest physical room capacity."""
    cap_csv = DATASETS_DIR / "edge_case_capacity_overflow.csv"
    assert cap_csv.exists()
    report = validate_csv_file(str(cap_csv), table_type="subjects")

    assert report["is_valid"] is False
    error_codes = {e["code"] for e in report["errors"]}
    assert "CAPACITY_OVERFLOW" in error_codes
