"""
ExamOpt — Deterministic Seed Generator (seed=42)
Problem Statement C10: Intelligent Examination Timetable Optimization System
GLA University Context: CSED Block AB-XI, BCA / BCA-DS / MCA Programs

Generates:
1. normal_gla_dataset/ (rooms.csv, timeslots.csv, faculty.csv, subjects.csv, student_groups.csv, student_enrollments.csv)
2. edge_case_lab_bottleneck.csv
3. edge_case_capacity_overflow.csv
4. invalid_corrupted_input.csv
5. SQLite Database: backend/examopt.db
"""

import os
import csv
import json
import random
import sqlite3
from pathlib import Path
from datetime import datetime, date

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "sample_datasets"
NORMAL_DIR = DATASET_DIR / "normal_gla_dataset"
SQLITE_DB_PATH = BASE_DIR / "examopt.db"
SCHEMA_SQL_PATH = BASE_DIR / "schema.sql"

# Ensure directories exist
NORMAL_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# 1. GENERATE ROOMS (15 Rooms in CSED Block AB-XI)
# ---------------------------------------------------------
ROOMS_DATA = [
    # 10 Theory Lecture Halls / Classrooms
    {"room_id": "AB11-101", "name": "CSED Block AB-XI Room 101", "building": "AB-XI CSED Block", "capacity": 80, "room_type": "THEORY", "unavailable_slots": ""},
    {"room_id": "AB11-102", "name": "CSED Block AB-XI Room 102", "building": "AB-XI CSED Block", "capacity": 80, "room_type": "THEORY", "unavailable_slots": "D2-M"},
    {"room_id": "AB11-103", "name": "CSED Block AB-XI Room 103", "building": "AB-XI CSED Block", "capacity": 60, "room_type": "THEORY", "unavailable_slots": ""},
    {"room_id": "AB11-201", "name": "CSED Block AB-XI Room 201", "building": "AB-XI CSED Block", "capacity": 100, "room_type": "THEORY", "unavailable_slots": ""},
    {"room_id": "AB11-202", "name": "CSED Block AB-XI Room 202", "building": "AB-XI CSED Block", "capacity": 100, "room_type": "THEORY", "unavailable_slots": "D4-E"},
    {"room_id": "AB11-203", "name": "CSED Block AB-XI Room 203", "building": "AB-XI CSED Block", "capacity": 80, "room_type": "THEORY", "unavailable_slots": ""},
    {"room_id": "AB11-301", "name": "CSED Block AB-XI Lecture Hall 301", "building": "AB-XI CSED Block", "capacity": 120, "room_type": "THEORY", "unavailable_slots": ""},
    {"room_id": "AB11-302", "name": "CSED Block AB-XI Lecture Hall 302", "building": "AB-XI CSED Block", "capacity": 120, "room_type": "THEORY", "unavailable_slots": "D1-M"},
    {"room_id": "AB11-AUD1", "name": "CSED Block AB-XI Mini Auditorium 1", "building": "AB-XI CSED Block", "capacity": 150, "room_type": "THEORY", "unavailable_slots": ""},
    {"room_id": "AB11-AUD2", "name": "CSED Block AB-XI Mini Auditorium 2", "building": "AB-XI CSED Block", "capacity": 150, "room_type": "THEORY", "unavailable_slots": ""},
    # 5 Specialized Computer & Data Science Laboratories
    {"room_id": "AB11-LAB1", "name": "CSED Block AB-XI Central Computing Lab", "building": "AB-XI CSED Block", "capacity": 100, "room_type": "LAB", "unavailable_slots": ""},
    {"room_id": "AB11-LAB2", "name": "CSED Block AB-XI Data Science Lab", "building": "AB-XI CSED Block", "capacity": 90, "room_type": "LAB", "unavailable_slots": "D3-E"},
    {"room_id": "AB11-LAB3", "name": "CSED Block AB-XI Advanced Computing Lab", "building": "AB-XI CSED Block", "capacity": 90, "room_type": "LAB", "unavailable_slots": ""},
    {"room_id": "AB11-LAB4", "name": "CSED Block AB-XI Database Systems Lab", "building": "AB-XI CSED Block", "capacity": 80, "room_type": "LAB", "unavailable_slots": ""},
    {"room_id": "AB11-LAB5", "name": "CSED Block AB-XI AI & Cloud Lab", "building": "AB-XI CSED Block", "capacity": 80, "room_type": "LAB", "unavailable_slots": "D5-E"},
]

# ---------------------------------------------------------
# 2. GENERATE TIME SLOTS (10 Slots across 5 Exam Days)
# ---------------------------------------------------------
EXAM_DATES = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
TIMESLOTS_DATA = []
for day_idx, exam_date in enumerate(EXAM_DATES, start=1):
    TIMESLOTS_DATA.append({
        "slot_id": f"D{day_idx}-M",
        "day_number": day_idx,
        "exam_date": exam_date,
        "session": "MORNING",
        "time_range": "09:30 AM - 12:30 PM"
    })
    TIMESLOTS_DATA.append({
        "slot_id": f"D{day_idx}-E",
        "day_number": day_idx,
        "exam_date": exam_date,
        "session": "EVENING",
        "time_range": "02:00 PM - 05:00 PM"
    })

# ---------------------------------------------------------
# 3. GENERATE FACULTY / INVIGILATORS (20 Faculty members)
# ---------------------------------------------------------
FACULTY_NAMES = [
    ("Dr. Ashish Sharma", "CSED", "D1-M|D4-E", 5),
    ("Prof. Manoj Kumar", "CSED", "D2-E", 4),
    ("Dr. Neha Agrawal", "BCA", "", 5),
    ("Dr. Sachin Upadhyay", "CSED", "D3-M", 4),
    ("Prof. Pooja Pathak", "BCA", "", 4),
    ("Dr. Rajesh Singh", "MCA", "D5-E", 5),
    ("Prof. Deepa Gupta", "BCA", "D1-E", 4),
    ("Dr. Arvind Sharma", "CSED", "", 6),
    ("Prof. Vikram Chaudhary", "MCA", "D2-M", 4),
    ("Dr. Ritu Bhargava", "BCA", "", 5),
    ("Prof. Amit Garg", "CSED", "D3-E", 4),
    ("Dr. Sneha Verma", "MCA", "", 5),
    ("Prof. Kamal Kant", "CSED", "D4-M", 4),
    ("Dr. Preeti Tyagi", "BCA", "", 4),
    ("Prof. Gaurav Bansal", "CSED", "D1-M", 5),
    ("Dr. Anjali Mathur", "MCA", "", 4),
    ("Prof. Saurabh Dixit", "BCA", "D5-M", 4),
    ("Dr. Pradeep Rawat", "CSED", "", 5),
    ("Prof. Sunita Kumari", "MCA", "D2-E", 4),
    ("Dr. Pankaj Goswami", "CSED", "", 6),
]
FACULTY_DATA = [
    {
        "faculty_id": f"FAC-{101 + i}",
        "name": name,
        "department": dept,
        "unavailable_slots": unav,
        "max_duties": duties
    }
    for i, (name, dept, unav, duties) in enumerate(FACULTY_NAMES)
]

# ---------------------------------------------------------
# 4. DEFINE 24 REALISTIC SUBJECTS (BCA, BCA-DS, MCA)
# ---------------------------------------------------------
# 24 Subjects across Sem 1, 3, 5
SUBJECTS_CATALOG = [
    # BCA Semester 1 (Regular)
    {"subject_id": "BCA-101", "name": "Mathematical Foundation of Computer Science", "program": "BCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCA-102", "name": "Problem Solving with C Programming", "program": "BCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": "D3-M"},
    {"subject_id": "BCA-103", "name": "Digital Logic and Computer Organization", "program": "BCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCA-104P", "name": "C Programming Laboratory", "program": "BCA", "semester": 1, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": "D1-M"},

    # BCA-DS Semester 3 (Data Science Regular)
    {"subject_id": "BCADS-301", "name": "Data Structures using Python", "program": "BCA-DS", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D1-M", "unavailable_slots": ""},
    {"subject_id": "BCADS-302", "name": "Statistical Foundations for Data Science", "program": "BCA-DS", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCADS-303", "name": "Database Management Systems", "program": "BCA-DS", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": "D4-M"},
    {"subject_id": "BCADS-304P", "name": "Data Structures & Python Lab", "program": "BCA-DS", "semester": 3, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCADS-305P", "name": "R Programming & Statistics Lab", "program": "BCA-DS", "semester": 3, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},

    # BCA General Semester 3 (Regular)
    {"subject_id": "BCA-301", "name": "Object-Oriented Programming with Java", "program": "BCA", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCA-302", "name": "Operating Systems & Shell Scripting", "program": "BCA", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": "D2-E"},
    {"subject_id": "BCA-303", "name": "Web Technologies & UI Design", "program": "BCA", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCA-304P", "name": "Java Programming Laboratory", "program": "BCA", "semester": 3, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},

    # BCA-DS Semester 5 (Data Science Regular)
    {"subject_id": "BCADS-501", "name": "Machine Learning & Pattern Recognition", "program": "BCA-DS", "semester": 5, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCADS-502", "name": "Big Data Analytics with Apache Spark", "program": "BCA-DS", "semester": 5, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D2-M", "unavailable_slots": ""},
    {"subject_id": "BCADS-503", "name": "Data Visualization & Business Intelligence", "program": "BCA-DS", "semester": 5, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": "D3-E"},
    {"subject_id": "BCADS-504P", "name": "Machine Learning Hands-on Lab", "program": "BCA-DS", "semester": 5, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "BCADS-505P", "name": "Big Data & Hadoop Lab", "program": "BCA-DS", "semester": 5, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},

    # MCA Semester 1 (Regular)
    {"subject_id": "MCA-101", "name": "Advanced Data Structures & Algorithms", "program": "MCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "MCA-102", "name": "Advanced Operating Systems & Virtualization", "program": "MCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "MCA-103", "name": "Relational & NoSQL Database Architecture", "program": "MCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D3-M", "unavailable_slots": ""},
    {"subject_id": "MCA-104", "name": "Discrete Mathematics & Graph Theory", "program": "MCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": None, "unavailable_slots": "D5-M"},
    {"subject_id": "MCA-105P", "name": "Advanced DSA Laboratory", "program": "MCA", "semester": 1, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},
    {"subject_id": "MCA-106P", "name": "Enterprise DBMS Laboratory", "program": "MCA", "semester": 1, "duration_hours": 2, "requires_lab": 1, "fixed_slot": None, "unavailable_slots": ""},
]

# ---------------------------------------------------------
# 5. DEFINE 8 STUDENT GROUPS (5 Regular + 3 Backlog)
# ---------------------------------------------------------
GROUPS_CONFIG = [
    # 5 Regular Batches
    {"group_id": "GRP-BCA-S1", "name": "BCA Semester 1 Regular", "program": "BCA", "semester": 1, "is_backlog_group": 0, "count": 60,
     "subjects": ["BCA-101", "BCA-102", "BCA-103", "BCA-104P"]},
    {"group_id": "GRP-BCADS-S3", "name": "BCA (Data Science) Sem 3 Regular", "program": "BCA-DS", "semester": 3, "is_backlog_group": 0, "count": 55,
     "subjects": ["BCADS-301", "BCADS-302", "BCADS-303", "BCADS-304P", "BCADS-305P"]},
    {"group_id": "GRP-BCA-S3", "name": "BCA General Sem 3 Regular", "program": "BCA", "semester": 3, "is_backlog_group": 0, "count": 50,
     "subjects": ["BCA-301", "BCA-302", "BCA-303", "BCA-304P"]},
    {"group_id": "GRP-BCADS-S5", "name": "BCA (Data Science) Sem 5 Regular", "program": "BCA-DS", "semester": 5, "is_backlog_group": 0, "count": 55,
     "subjects": ["BCADS-501", "BCADS-502", "BCADS-503", "BCADS-504P", "BCADS-505P"]},
    {"group_id": "GRP-MCA-S1", "name": "MCA Semester 1 Regular", "program": "MCA", "semester": 1, "is_backlog_group": 0, "count": 65,
     "subjects": ["MCA-101", "MCA-102", "MCA-103", "MCA-104", "MCA-105P", "MCA-106P"]},

    # 3 Cross-Semester Backlog Cohorts (Real-world cross-semester conflict edges!)
    {"group_id": "GRP-BL-S5-S3", "name": "BCA-DS Sem 5 Cohort with Sem 3 Backlog", "program": "BCA-DS", "semester": 5, "is_backlog_group": 1, "count": 25,
     "subjects": ["BCADS-501", "BCADS-502", "BCADS-503", "BCADS-504P", "BCADS-301", "BCADS-303"]}, # Backlog in BCADS-301, 303!
    {"group_id": "GRP-BL-S3-S1", "name": "BCA Sem 3 Cohort with Sem 1 Backlog", "program": "BCA", "semester": 3, "is_backlog_group": 1, "count": 25,
     "subjects": ["BCA-301", "BCA-302", "BCA-303", "BCA-102", "BCA-104P"]}, # Backlog in BCA-102, 104P!
    {"group_id": "GRP-BL-MCA-BCA", "name": "MCA Sem 1 Cohort with BCA Bridge Backlog", "program": "MCA", "semester": 1, "is_backlog_group": 1, "count": 20,
     "subjects": ["MCA-101", "MCA-102", "MCA-103", "BCA-101"]}, # Backlog in BCA-101!
]

# Names pool for realistic student generation
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Shaurya", "Atharv", "Ananya", "Diya", "Gauri", "Anushka", "Navya", "Angel", "Pari", "Saanvi",
    "Rohan", "Priya", "Rahul", "Pooja", "Vikram", "Neha", "Amit", "Kavya", "Deepak", "Swati",
    "Kunal", "Meera", "Harsh", "Sneha", "Tanmay", "Riya", "Manish", "Simran", "Naveen", "Bhavna",
    "Akash", "Tanya", "Gaurav", "Nisha", "Dev", "Isha", "Abhishek", "Shreya", "Prashant", "Kriti"
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Yadav", "Mishra", "Pandey", "Saxena", "Agrawal", "Trivedi",
    "Chaudhary", "Joshi", "Bhardwaj", "Tiwari", "Shukla", "Dubey", "Rawat", "Bansal", "Goel", "Gautam",
    "Srivastava", "Upadhyay", "Tripathi", "Pathak", "Chauhan", "Dixit", "Kapoor", "Bhatnagar", "Mehta", "Tyagi"
]


def generate_synthetic_students():
    """Generates 350 individual students and their enrollments."""
    students = []
    junction_rows = []
    roll_counter = 1

    for grp in GROUPS_CONFIG:
        group_id = grp["group_id"]
        count = grp["count"]
        program = grp["program"]
        subjects = grp["subjects"]
        has_backlog = grp["is_backlog_group"]

        prog_code = "DS" if program == "BCA-DS" else ("MCA" if program == "MCA" else "BCA")

        for _ in range(count):
            roll_no = f"GLA26-{prog_code}-{roll_counter:04d}"
            roll_counter += 1
            f_name = random.choice(FIRST_NAMES)
            l_name = random.choice(LAST_NAMES)
            student_name = f"{f_name} {l_name}"

            # Every student in the group is enrolled in all group's subjects
            enrolled_str = ",".join(subjects)

            students.append({
                "roll_no": roll_no,
                "student_name": student_name,
                "group_id": group_id,
                "enrolled_subject_ids": enrolled_str,
                "has_backlog": has_backlog
            })

            for s_id in subjects:
                junction_rows.append({
                    "roll_no": roll_no,
                    "subject_id": s_id
                })

    return students, junction_rows


def calculate_subject_enrollments(junction_rows):
    """Calculates exact enrollment count per subject from junction rows."""
    counts = {}
    for row in junction_rows:
        s_id = row["subject_id"]
        counts[s_id] = counts.get(s_id, 0) + 1
    return counts


def write_csv(filepath, rows, fieldnames):
    """Writes list of dicts to CSV."""
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_and_seed_sqlite(subjects_data, students_data, junction_data):
    """Executes schema.sql and seeds all data into backend/examopt.db."""
    if SQLITE_DB_PATH.exists():
        SQLITE_DB_PATH.unlink()

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Apply schema
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)

    # Insert Rooms
    cursor.executemany(
        """INSERT INTO rooms (room_id, name, building, capacity, room_type, unavailable_slots)
           VALUES (:room_id, :name, :building, :capacity, :room_type, :unavailable_slots)""",
        ROOMS_DATA
    )

    # Insert Timeslots
    cursor.executemany(
        """INSERT INTO timeslots (slot_id, day_number, exam_date, session, time_range)
           VALUES (:slot_id, :day_number, :exam_date, :session, :time_range)""",
        TIMESLOTS_DATA
    )

    # Insert Faculty
    cursor.executemany(
        """INSERT INTO faculty (faculty_id, name, department, unavailable_slots, max_duties)
           VALUES (:faculty_id, :name, :department, :unavailable_slots, :max_duties)""",
        FACULTY_DATA
    )

    # Insert Subjects
    cursor.executemany(
        """INSERT INTO subjects (subject_id, name, program, semester, duration_hours, requires_lab, fixed_slot, unavailable_slots, enrolled_students)
           VALUES (:subject_id, :name, :program, :semester, :duration_hours, :requires_lab, :fixed_slot, :unavailable_slots, :enrolled_students)""",
        subjects_data
    )

    # Insert Student Groups
    cursor.executemany(
        """INSERT INTO student_groups (group_id, name, program, semester, is_backlog_group, student_count)
           VALUES (:group_id, :name, :program, :semester, :is_backlog_group, :count)""",
        GROUPS_CONFIG
    )

    # Insert Student Enrollments
    cursor.executemany(
        """INSERT INTO student_enrollments (roll_no, student_name, group_id, enrolled_subject_ids, has_backlog)
           VALUES (:roll_no, :student_name, :group_id, :enrolled_subject_ids, :has_backlog)""",
        students_data
    )

    # Insert Junction Rows
    cursor.executemany(
        """INSERT INTO student_subject_enrollments (roll_no, subject_id)
           VALUES (:roll_no, :subject_id)""",
        junction_data
    )

    conn.commit()
    conn.close()


def generate_edge_cases(normal_subjects):
    """Generates the three mandatory edge-case datasets."""
    # 1. edge_case_lab_bottleneck.csv
    # 6 lab exams are forced into the same fixed_slot ('D1-M'), but campus only has 5 lab rooms in total!
    # And total lab demand in D1-M (460 students) exceeds total campus lab seats (440 seats)!
    lab_bottleneck = []
    lab_target_ids = ["BCADS-304P", "BCADS-305P", "BCA-104P", "BCADS-504P", "BCADS-505P", "MCA-105P"]
    for s in normal_subjects:
        item = dict(s)
        if item["subject_id"] in lab_target_ids:
            item["fixed_slot"] = "D1-M"
            item["requires_lab"] = 1
            item["unavailable_slots"] = ""  # Clear unavailable to isolate bottleneck
        lab_bottleneck.append(item)

    lab_bottleneck_path = DATASET_DIR / "edge_case_lab_bottleneck.csv"
    write_csv(
        lab_bottleneck_path,
        lab_bottleneck,
        ["subject_id", "name", "program", "semester", "duration_hours", "requires_lab", "fixed_slot", "unavailable_slots", "enrolled_students"]
    )

    # 2. edge_case_capacity_overflow.csv
    # A mega-course has enrolled_students = 650, exceeding any single theory hall (max 150)
    capacity_overflow = []
    for s in normal_subjects:
        item = dict(s)
        if item["subject_id"] == "BCA-101":
            item["name"] = "Mega University Core: Mathematical Foundations"
            item["enrolled_students"] = 650
        capacity_overflow.append(item)

    capacity_overflow_path = DATASET_DIR / "edge_case_capacity_overflow.csv"
    write_csv(
        capacity_overflow_path,
        capacity_overflow,
        ["subject_id", "name", "program", "semester", "duration_hours", "requires_lab", "fixed_slot", "unavailable_slots", "enrolled_students"]
    )

    # 3. invalid_corrupted_input.csv
    # Contains:
    # - Duplicate subject_id rows
    # - Negative student counts (enrolled_students = -40)
    # - Contradictory constraints (fixed_slot = D2-M AND unavailable_slots = D2-M)
    # - Missing required fields and non-existent fixed_slot references (D99-M)
    corrupted_data = [
        {"subject_id": "BCA-101", "name": "Math Foundation", "program": "BCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D1-M", "unavailable_slots": "", "enrolled_students": 60},
        # Duplicate subject_id
        {"subject_id": "BCA-101", "name": "Duplicate Math Entry", "program": "BCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D1-E", "unavailable_slots": "", "enrolled_students": 50},
        # Negative student count
        {"subject_id": "ERR-NEG-01", "name": "Corrupted Quantum Computing", "program": "MCA", "semester": 1, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "", "unavailable_slots": "", "enrolled_students": -40},
        # Contradictory constraints: fixed_slot = D2-M and unavailable_slots = D2-M
        {"subject_id": "ERR-CONTRA-02", "name": "Contradictory Logic Systems", "program": "BCA", "semester": 3, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D2-M", "unavailable_slots": "D2-M|D3-E", "enrolled_students": 45},
        # Non-existent slot reference D99-M
        {"subject_id": "ERR-SLOT-03", "name": "Invalid Slot Reference Subject", "program": "BCA-DS", "semester": 5, "duration_hours": 3, "requires_lab": 0, "fixed_slot": "D99-M", "unavailable_slots": "D88-E", "enrolled_students": 55},
        # Missing required name and invalid duration
        {"subject_id": "ERR-MISSING-04", "name": "", "program": "INVALID_PROG", "semester": 12, "duration_hours": 10, "requires_lab": 5, "fixed_slot": "", "unavailable_slots": "", "enrolled_students": 30},
    ]

    invalid_path = DATASET_DIR / "invalid_corrupted_input.csv"
    write_csv(
        invalid_path,
        corrupted_data,
        ["subject_id", "name", "program", "semester", "duration_hours", "requires_lab", "fixed_slot", "unavailable_slots", "enrolled_students"]
    )


def main():
    print("=" * 60)
    print(" ExamOpt Deterministic Seed Generator (seed=42) ")
    print("=" * 60)

    # 1. Generate Students & Junction records
    students, junction_rows = generate_synthetic_students()
    total_students = len(students)
    total_enrollment_records = len(junction_rows)
    print(f"[+] Generated {total_students} synthetic individual students across 8 groups.")
    print(f"[+] Generated {total_enrollment_records} relational student-to-subject enrollments.")

    # 2. Derive exact enrolled_students per subject
    subject_counts = calculate_subject_enrollments(junction_rows)

    # 3. Build complete subjects list with 100% mathematically consistent enrolled_students
    subjects_final = []
    for s in SUBJECTS_CATALOG:
        s_copy = dict(s)
        s_copy["enrolled_students"] = subject_counts.get(s_copy["subject_id"], 0)
        subjects_final.append(s_copy)

    # 4. Write Normal GLA Dataset CSV files
    write_csv(
        NORMAL_DIR / "rooms.csv",
        ROOMS_DATA,
        ["room_id", "name", "building", "capacity", "room_type", "unavailable_slots"]
    )
    write_csv(
        NORMAL_DIR / "timeslots.csv",
        TIMESLOTS_DATA,
        ["slot_id", "day_number", "exam_date", "session", "time_range"]
    )
    write_csv(
        NORMAL_DIR / "faculty.csv",
        FACULTY_DATA,
        ["faculty_id", "name", "department", "unavailable_slots", "max_duties"]
    )
    write_csv(
        NORMAL_DIR / "subjects.csv",
        subjects_final,
        ["subject_id", "name", "program", "semester", "duration_hours", "requires_lab", "fixed_slot", "unavailable_slots", "enrolled_students"]
    )

    # Student groups CSV
    groups_csv_rows = [
        {"group_id": g["group_id"], "name": g["name"], "program": g["program"], "semester": g["semester"], "is_backlog_group": g["is_backlog_group"], "student_count": g["count"]}
        for g in GROUPS_CONFIG
    ]
    write_csv(
        NORMAL_DIR / "student_groups.csv",
        groups_csv_rows,
        ["group_id", "name", "program", "semester", "is_backlog_group", "student_count"]
    )

    # Student enrollments CSV
    write_csv(
        NORMAL_DIR / "student_enrollments.csv",
        students,
        ["roll_no", "student_name", "group_id", "enrolled_subject_ids", "has_backlog"]
    )
    print(f"[+] Successfully wrote all normal CSV files to {NORMAL_DIR}")

    # 5. Generate Edge-Case & Corrupted Datasets
    generate_edge_cases(subjects_final)
    print(f"[+] Successfully generated edge-case CSV files in {DATASET_DIR}")

    # 6. Seed SQLite Database
    print(f"[+] Seeding SQLite database at {SQLITE_DB_PATH}...")
    build_and_seed_sqlite(subjects_final, students, junction_rows)

    # Verify counts in SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    summary = {
        "rooms": cur.execute("SELECT COUNT(*) FROM rooms;").fetchone()[0],
        "timeslots": cur.execute("SELECT COUNT(*) FROM timeslots;").fetchone()[0],
        "faculty": cur.execute("SELECT COUNT(*) FROM faculty;").fetchone()[0],
        "subjects": cur.execute("SELECT COUNT(*) FROM subjects;").fetchone()[0],
        "student_groups": cur.execute("SELECT COUNT(*) FROM student_groups;").fetchone()[0],
        "student_enrollments": cur.execute("SELECT COUNT(*) FROM student_enrollments;").fetchone()[0],
        "student_subject_enrollments": cur.execute("SELECT COUNT(*) FROM student_subject_enrollments;").fetchone()[0],
        "backlog_students": cur.execute("SELECT COUNT(*) FROM student_enrollments WHERE has_backlog = 1;").fetchone()[0]
    }
    conn.close()

    print("[+] Database Verification Summary:")
    for k, v in summary.items():
        print(f"    - {k}: {v}")
    print("[SUCCESS] Deterministic seed generation & database population completed.")


if __name__ == "__main__":
    main()
