/**
 * ExamOpt API Client Service
 * Connects React Frontend to FastAPI Backend
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface DataSummary {
  active_preset: string;
  counts: {
    rooms: number;
    timeslots: number;
    faculty: number;
    subjects: number;
    student_groups: number;
    student_enrollments: number;
    student_subject_enrollments: number;
    backlog_students: number;
  };
  campus_capacity: {
    total_theory_seats: number;
    total_lab_seats: number;
    total_rooms: number;
  };
}

export interface ValidationErrorItem {
  code: string;
  table: string;
  row_id: string;
  field: string;
  message: string;
  severity: 'ERROR' | 'WARNING';
}

export interface ValidationReport {
  is_valid: boolean;
  readiness_score: number;
  status: string;
  summary: {
    total_errors: number;
    total_warnings: number;
    table_counts: Record<string, number>;
  };
  errors: ValidationErrorItem[];
  warnings: ValidationErrorItem[];
  diagnostics: string[];
}

export interface ScheduledAllocation {
  subject_id: string;
  subject_name: string;
  program: string;
  semester: number;
  slot_id: string;
  exam_date: string;
  session: string;
  time_range: string;
  room_id: string;
  room_name: string;
  room_capacity: number;
  assigned_faculty_id?: string;
  assigned_faculty_name?: string;
  assigned_students: number;
  duration_hours: number;
  requires_lab: boolean;
}

export interface ScheduleRunResult {
  run_id: string;
  algorithm: string;
  status: string;
  is_feasible: boolean;
  total_exams: number;
  scheduled_exams: number;
  unscheduled_exams: number;
  hard_conflicts: number;
  slots_used: number;
  room_utilization_pct: number;
  unused_capacity_seats: number;
  execution_time_ms: number;
  soft_score: number;
  allocations: ScheduledAllocation[];
  unscheduled_details: any[];
  conflicts_log: any[];
}

export interface AlgorithmComparisonMetric {
  algorithm: string;
  status: string;
  is_feasible: boolean;
  scheduled_exams: number;
  unscheduled_exams: number;
  hard_conflicts: number;
  slots_used: number;
  room_utilization_pct: number;
  unused_capacity_seats: number;
  execution_time_ms: number;
  soft_score: number;
}

export interface BenchmarkComparisonResponse {
  summary: {
    total_exams_to_schedule: number;
    total_available_slots: number;
    total_available_rooms: number;
    best_performing_algorithm: string;
    best_soft_score: number;
  };
  comparison: AlgorithmComparisonMetric[];
  detailed_results: Record<string, ScheduleRunResult>;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  return res.json();
}

export async function fetchDataSummary(): Promise<DataSummary> {
  const res = await fetch(`${API_BASE_URL}/api/data/summary`);
  if (!res.ok) throw new Error("Failed to load data summary");
  return res.json();
}

export async function fetchTableData(tableName: string, limit: number = 500) {
  const res = await fetch(`${API_BASE_URL}/api/data/tables/${tableName}?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to load ${tableName}`);
  return res.json();
}

export async function runValidation(presetName?: string): Promise<ValidationReport> {
  const res = await fetch(`${API_BASE_URL}/api/data/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preset_name: presetName })
  });
  if (!res.ok) throw new Error("Validation request failed");
  return res.json();
}

export async function loadPreset(presetName: string) {
  const res = await fetch(`${API_BASE_URL}/api/data/load-preset/${presetName}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Failed to activate preset ${presetName}`);
  return res.json();
}

export async function generateSchedule(algorithm: string = 'BACKTRACKING'): Promise<ScheduleRunResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/schedules/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ algorithm })
  });
  if (!res.ok) throw new Error("Failed to generate schedule");
  return res.json();
}

export async function compareAlgorithms(): Promise<BenchmarkComparisonResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/schedules/compare`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error("Comparison benchmark failed");
  return res.json();
}

export async function publishSchedule(runId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/schedules/${runId}/publish`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Publication rejected" }));
    throw new Error(err.detail || "Publication rejected");
  }
  return res.json();
}

export async function fetchActivePublishedSchedule() {
  const res = await fetch(`${API_BASE_URL}/api/v1/schedules/active-published`);
  if (!res.ok) throw new Error("No published timetable available");
  return res.json();
}

export async function fetchStudentTimetable(rollNo?: string) {
  const url = rollNo 
    ? `${API_BASE_URL}/api/v1/timetable/student?roll_no=${encodeURIComponent(rollNo)}`
    : `${API_BASE_URL}/api/v1/timetable/student`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Student timetable lookup failed");
  return res.json();
}

export async function fetchFacultyTimetable(facultyId?: string) {
  const url = facultyId 
    ? `${API_BASE_URL}/api/v1/timetable/faculty?faculty_id=${encodeURIComponent(facultyId)}`
    : `${API_BASE_URL}/api/v1/timetable/faculty`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Faculty timetable lookup failed");
  return res.json();
}

export function getExportTimetableCsvUrl(runId?: string) {
  return runId ? `${API_BASE_URL}/api/v1/timetable/export/csv?run_id=${runId}` : `${API_BASE_URL}/api/v1/timetable/export/csv`;
}
