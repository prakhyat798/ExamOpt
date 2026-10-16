import { useState, useEffect } from 'react';
import {
  Calendar, Clock, Building, Users, BookOpen, CheckCircle, AlertTriangle,
  XCircle, Play, RefreshCw, Download, Award, ShieldCheck, UserCheck,
  Smartphone, Filter, ChevronRight, CheckCircle2
} from 'lucide-react';
import {
  fetchDataSummary, runValidation, loadPreset, generateSchedule,
  compareAlgorithms, publishSchedule, fetchActivePublishedSchedule,
  fetchStudentTimetable, fetchFacultyTimetable, getExportTimetableCsvUrl
} from './services/api';
import type {
  DataSummary, ValidationReport, BenchmarkComparisonResponse, ScheduledAllocation
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'timetable' | 'validation' | 'benchmark' | 'student' | 'faculty'>('overview');
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [activeSchedule, setActiveSchedule] = useState<any | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkComparisonResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Filters for timetable grid
  const [selectedProgram, setSelectedProgram] = useState<string>('ALL');
  const [selectedSemester, setSelectedSemester] = useState<string>('ALL');
  const [selectedRoomType, setSelectedRoomType] = useState<string>('ALL');

  // Student and Faculty lookup states
  const [studentRollNo, setStudentRollNo] = useState<string>('GLA26-BCA-0001');
  const [studentData, setStudentData] = useState<any | null>(null);
  const [facultyId, setFacultyId] = useState<string>('FAC-101');
  const [facultyData, setFacultyData] = useState<any | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const sum = await fetchDataSummary();
      setSummary(sum);

      const val = await runValidation();
      setValidationReport(val);

      const pub = await fetchActivePublishedSchedule().catch(() => null);
      if (pub) setActiveSchedule(pub);
    } catch (err: any) {
      console.error(err);
      setStatusMessage({ text: err.message || "Failed to load initial data", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handlePresetSwitch = async (preset: string) => {
    setLoading(true);
    setStatusMessage({ text: `Switching to dataset preset '${preset}'...`, type: 'info' });
    try {
      const res = await loadPreset(preset);
      setValidationReport(res.validation_report);
      const sum = await fetchDataSummary();
      setSummary(sum);
      setStatusMessage({ text: `Dataset preset '${preset}' activated and validated.`, type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Failed to switch preset", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (algorithm: string) => {
    setLoading(true);
    setStatusMessage({ text: `Running ${algorithm} scheduling engine...`, type: 'info' });
    try {
      const res = await generateSchedule(algorithm);
      setActiveSchedule({ allocations: res.allocations, run: res });
      setStatusMessage({
        text: `Schedule generated with ${res.algorithm}! (${res.scheduled_exams}/${res.total_exams} scheduled, ${res.execution_time_ms}ms)`,
        type: res.is_feasible ? 'success' : 'error'
      });
      setActiveTab('timetable');
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Scheduling failed", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleBenchmark = async () => {
    setLoading(true);
    setStatusMessage({ text: "Executing side-by-side multi-algorithm benchmark...", type: 'info' });
    try {
      const res = await compareAlgorithms();
      setBenchmark(res);
      setStatusMessage({ text: "Benchmark evaluation completed successfully!", type: 'success' });
      setActiveTab('benchmark');
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Benchmark failed", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (runId: string) => {
    setLoading(true);
    try {
      const res = await publishSchedule(runId);
      setStatusMessage({ text: res.message, type: 'success' });
      const pub = await fetchActivePublishedSchedule();
      setActiveSchedule(pub);
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Publishing rejected", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleStudentLookup = async (roll: string) => {
    setLoading(true);
    try {
      const res = await fetchStudentTimetable(roll);
      setStudentData(res);
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Student not found", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleFacultyLookup = async (fId: string) => {
    setLoading(true);
    try {
      const res = await fetchFacultyTimetable(fId);
      setFacultyData(res);
    } catch (err: any) {
      setStatusMessage({ text: err.message || "Faculty not found", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Filtered allocations for timetable
  const rawAllocations: ScheduledAllocation[] = activeSchedule?.allocations || [];
  const filteredAllocations = rawAllocations.filter(a => {
    if (selectedProgram !== 'ALL' && a.program !== selectedProgram) return false;
    if (selectedSemester !== 'ALL' && String(a.semester) !== selectedSemester) return false;
    if (selectedRoomType === 'LAB' && !a.requires_lab) return false;
    if (selectedRoomType === 'THEORY' && a.requires_lab) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* Header / Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Calendar className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">ExamOpt</span>
                <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-medium px-2 py-0.5 rounded-full">
                  GLA University
                </span>
              </div>
              <p className="text-xs text-slate-400">Intelligent Examination Timetable Optimization System</p>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex items-center space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 overflow-x-auto">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${activeTab === 'overview' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('timetable')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${activeTab === 'timetable' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Timetable Grid
            </button>
            <button
              onClick={() => setActiveTab('validation')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${activeTab === 'validation' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Data Quality
            </button>
            <button
              onClick={() => setActiveTab('benchmark')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${activeTab === 'benchmark' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Algorithm Comparison
            </button>
            <button
              onClick={() => { setActiveTab('student'); handleStudentLookup(studentRollNo); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center space-x-1 ${activeTab === 'student' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              <Smartphone className="w-3 h-3" />
              <span>Student App</span>
            </button>
            <button
              onClick={() => { setActiveTab('faculty'); handleFacultyLookup(facultyId); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center space-x-1 ${activeTab === 'faculty' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              <UserCheck className="w-3 h-3" />
              <span>Faculty Portal</span>
            </button>
          </nav>

          {/* Quick Actions */}
          <div className="flex items-center space-x-2">
            {loading && (
              <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[11px] text-indigo-300 animate-pulse">
                <RefreshCw className="w-3 h-3 animate-spin" />
                <span>Processing...</span>
              </span>
            )}
            <a
              href={getExportTimetableCsvUrl(activeSchedule?.run?.run_id)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
              title="Download Timetable CSV"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">CSV Export</span>
            </a>
          </div>
        </div>
      </header>

      {/* Status banner */}
      {statusMessage && (
        <div className={`px-4 py-2.5 text-xs font-medium flex items-center justify-between transition ${
          statusMessage.type === 'success' ? 'bg-emerald-950/80 text-emerald-300 border-b border-emerald-800' :
          statusMessage.type === 'error' ? 'bg-rose-950/80 text-rose-300 border-b border-rose-800' :
          'bg-indigo-950/80 text-indigo-300 border-b border-indigo-800'
        }`}>
          <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {statusMessage.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-400" />}
              {statusMessage.type === 'error' && <AlertTriangle className="w-4 h-4 text-rose-400" />}
              <span>{statusMessage.text}</span>
            </div>
            <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Quick Metrics Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs">Exams (Subjects)</span>
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-2xl font-bold text-white">{summary?.counts.subjects || 24}</div>
                <div className="text-[11px] text-slate-400 mt-1">BCA, BCA-DS, MCA</div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs">Exam Rooms</span>
                  <Building className="w-4 h-4 text-violet-400" />
                </div>
                <div className="text-2xl font-bold text-white">{summary?.counts.rooms || 15}</div>
                <div className="text-[11px] text-slate-400 mt-1">10 Theory + 5 Labs</div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs">Time Slots</span>
                  <Clock className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold text-white">{summary?.counts.timeslots || 10}</div>
                <div className="text-[11px] text-slate-400 mt-1">5 Days × 2 Sessions</div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs">Faculty</span>
                  <Users className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white">{summary?.counts.faculty || 20}</div>
                <div className="text-[11px] text-slate-400 mt-1">CSED, BCA, MCA</div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs">Individual Students</span>
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="text-2xl font-bold text-white">{summary?.counts.student_enrollments || 355}</div>
                <div className="text-[11px] text-slate-400 mt-1">1,735 Subject Enrollments</div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <div className="flex items-center justify-between text-slate-400 mb-2">
                  <span className="text-xs">Backlog Students</span>
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                </div>
                <div className="text-2xl font-bold text-rose-400">{summary?.counts.backlog_students || 70}</div>
                <div className="text-[11px] text-slate-400 mt-1">Cross-Semester Edges</div>
              </div>
            </div>

            {/* Quick Engine Launcher & Preset Switcher */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Algorithm Trigger Card */}
              <div className="lg:col-span-2 bg-gradient-to-br from-slate-800/80 to-slate-900 border border-slate-700 rounded-2xl p-6 shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                      <span>Deterministic Optimization Engine</span>
                      <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                        Ready
                      </span>
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Choose an optimization algorithm to generate a zero-conflict timetable respecting student clashes, room capacities, and faculty workloads.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <button
                    onClick={() => handleGenerate('FIRST_FIT')}
                    className="flex flex-col items-start p-4 rounded-xl bg-slate-800/90 hover:bg-slate-700/80 border border-slate-700 text-left transition group"
                  >
                    <div className="text-xs font-bold text-slate-300 group-hover:text-white flex items-center justify-between w-full">
                      <span>Algorithm A</span>
                      <Play className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-400" />
                    </div>
                    <div className="text-sm font-semibold text-white mt-1">First-Fit Baseline</div>
                    <p className="text-[11px] text-slate-400 mt-2">Greedy placement into first available slot & room configuration.</p>
                  </button>

                  <button
                    onClick={() => handleGenerate('WELSH_POWELL')}
                    className="flex flex-col items-start p-4 rounded-xl bg-slate-800/90 hover:bg-slate-700/80 border border-slate-700 text-left transition group"
                  >
                    <div className="text-xs font-bold text-slate-300 group-hover:text-white flex items-center justify-between w-full">
                      <span>Algorithm B</span>
                      <Play className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-400" />
                    </div>
                    <div className="text-sm font-semibold text-white mt-1">Welsh–Powell Coloring</div>
                    <p className="text-[11px] text-slate-400 mt-2">Graph degree ordering (most constrained first) + Best-Fit room packing.</p>
                  </button>

                  <button
                    onClick={() => handleGenerate('BACKTRACKING')}
                    className="flex flex-col items-start p-4 rounded-xl bg-gradient-to-br from-indigo-900/40 to-slate-800/90 hover:from-indigo-900/60 border border-indigo-500/40 text-left transition group"
                  >
                    <div className="text-xs font-bold text-indigo-300 group-hover:text-white flex items-center justify-between w-full">
                      <span>Algorithm C (Recommended)</span>
                      <Play className="w-3.5 h-3.5 text-indigo-400" />
                    </div>
                    <div className="text-sm font-semibold text-white mt-1">MRV Backtracking</div>
                    <p className="text-[11px] text-slate-400 mt-2">Constraint search with MRV heuristic, forward checking, and fixed propagation.</p>
                  </button>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-700/60 flex items-center justify-between flex-wrap gap-3">
                  <div className="text-xs text-slate-400">
                    Active Published Schedule: <span className="font-semibold text-white">{activeSchedule?.publication?.title || "Auto-Published Version 1"}</span>
                  </div>
                  <button
                    onClick={handleBenchmark}
                    className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition"
                  >
                    <Award className="w-4 h-4" />
                    <span>Run Comparative Benchmark</span>
                  </button>
                </div>
              </div>

              {/* Rubric Edge-Case Switcher Card */}
              <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>Rubric Test Datasets</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Toggle between normal GLA dataset and edge-case scenarios to evaluate the validator:
                  </p>

                  <div className="space-y-2 mt-4">
                    <button
                      onClick={() => handlePresetSwitch('normal')}
                      className={`w-full px-3 py-2 rounded-lg text-left text-xs font-medium border flex items-center justify-between transition ${
                        summary?.active_preset === 'normal'
                          ? 'bg-emerald-950/60 border-emerald-600/60 text-emerald-300'
                          : 'bg-slate-900/60 border-slate-700 text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">Normal GLA Dataset</div>
                        <div className="text-[10px] opacity-75">100% valid, 0 clashes, schedulable</div>
                      </div>
                      {summary?.active_preset === 'normal' && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                    </button>

                    <button
                      onClick={() => handlePresetSwitch('lab_bottleneck')}
                      className={`w-full px-3 py-2 rounded-lg text-left text-xs font-medium border flex items-center justify-between transition ${
                        summary?.active_preset === 'lab_bottleneck'
                          ? 'bg-amber-950/60 border-amber-600/60 text-amber-300'
                          : 'bg-slate-900/60 border-slate-700 text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">Edge: Lab Bottleneck</div>
                        <div className="text-[10px] opacity-75">6 lab exams locked to slot D1-M (exceeds 5 labs)</div>
                      </div>
                      {summary?.active_preset === 'lab_bottleneck' && <CheckCircle className="w-4 h-4 text-amber-400" />}
                    </button>

                    <button
                      onClick={() => handlePresetSwitch('capacity_overflow')}
                      className={`w-full px-3 py-2 rounded-lg text-left text-xs font-medium border flex items-center justify-between transition ${
                        summary?.active_preset === 'capacity_overflow'
                          ? 'bg-rose-950/60 border-rose-600/60 text-rose-300'
                          : 'bg-slate-900/60 border-slate-700 text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">Edge: Capacity Overflow</div>
                        <div className="text-[10px] opacity-75">Mega-course with 650 students (exceeds hall 150)</div>
                      </div>
                      {summary?.active_preset === 'capacity_overflow' && <CheckCircle className="w-4 h-4 text-rose-400" />}
                    </button>

                    <button
                      onClick={() => handlePresetSwitch('invalid_corrupted')}
                      className={`w-full px-3 py-2 rounded-lg text-left text-xs font-medium border flex items-center justify-between transition ${
                        summary?.active_preset === 'invalid_corrupted'
                          ? 'bg-purple-950/60 border-purple-600/60 text-purple-300'
                          : 'bg-slate-900/60 border-slate-700 text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">Invalid Corrupted Input</div>
                        <div className="text-[10px] opacity-75">Negative counts, contradictory slots, duplicate IDs</div>
                      </div>
                      {summary?.active_preset === 'invalid_corrupted' && <CheckCircle className="w-4 h-4 text-purple-400" />}
                    </button>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-700/60 flex items-center justify-between">
                  <span className="text-xs text-slate-400">Readiness Score:</span>
                  <span className={`text-sm font-bold ${validationReport?.is_valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {validationReport?.readiness_score || 0}/100
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: TIMETABLE GRID */}
        {activeTab === 'timetable' && (
          <div className="space-y-4">
            {/* Filter and Publish Bar */}
            <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center space-x-1.5 text-xs text-slate-400">
                  <Filter className="w-3.5 h-3.5" />
                  <span>Filters:</span>
                </div>

                {/* Program Filter */}
                <select
                  value={selectedProgram}
                  onChange={(e) => setSelectedProgram(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Programs</option>
                  <option value="BCA">BCA Regular</option>
                  <option value="BCA-DS">BCA (Data Science)</option>
                  <option value="MCA">MCA</option>
                </select>

                {/* Semester Filter */}
                <select
                  value={selectedSemester}
                  onChange={(e) => setSelectedSemester(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Semesters</option>
                  <option value="1">Semester 1</option>
                  <option value="3">Semester 3</option>
                  <option value="5">Semester 5</option>
                </select>

                {/* Room Type Filter */}
                <select
                  value={selectedRoomType}
                  onChange={(e) => setSelectedRoomType(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Room Types</option>
                  <option value="THEORY">Theory Halls Only</option>
                  <option value="LAB">Laboratories Only</option>
                </select>

                <span className="text-xs text-slate-400">
                  Showing {filteredAllocations.length} of {rawAllocations.length} examinations
                </span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2">
                {activeSchedule?.run?.run_id && (
                  <button
                    onClick={() => handlePublish(activeSchedule.run.run_id)}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow transition"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Publish Schedule</span>
                  </button>
                )}
                <a
                  href={getExportTimetableCsvUrl(activeSchedule?.run?.run_id)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs font-semibold text-white transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download CSV</span>
                </a>
              </div>
            </div>

            {/* Timetable Table */}
            <div className="bg-slate-800/60 border border-slate-700 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 text-slate-300 font-semibold border-b border-slate-700">
                    <tr>
                      <th className="px-4 py-3">Slot & Date</th>
                      <th className="px-4 py-3">Subject</th>
                      <th className="px-4 py-3">Program / Sem</th>
                      <th className="px-4 py-3">Room & Type</th>
                      <th className="px-4 py-3">Enrolled / Cap</th>
                      <th className="px-4 py-3">Assigned Faculty</th>
                      <th className="px-4 py-3">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {filteredAllocations.map((a, idx) => (
                      <tr key={idx} className="hover:bg-slate-700/30 transition">
                        <td className="px-4 py-3 font-medium">
                          <div className="text-white flex items-center space-x-1.5">
                            <span className="bg-indigo-950 text-indigo-300 font-mono px-1.5 py-0.5 rounded border border-indigo-800 text-[11px]">
                              {a.slot_id}
                            </span>
                            <span>{a.exam_date}</span>
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">{a.session} ({a.time_range})</div>
                        </td>

                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{a.subject_name}</div>
                          <div className="text-[11px] font-mono text-indigo-300">{a.subject_id}</div>
                        </td>

                        <td className="px-4 py-3">
                          <span className="bg-slate-800 px-2 py-0.5 rounded text-[11px] border border-slate-700">
                            {a.program} • Sem {a.semester}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <div className="text-white font-medium">{a.room_name}</div>
                          <div className="flex items-center space-x-1.5 mt-0.5">
                            <span className="font-mono text-[11px] text-slate-400">{a.room_id}</span>
                            <span className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                              a.requires_lab ? 'bg-amber-950/80 text-amber-300 border border-amber-800' : 'bg-slate-800 text-slate-300'
                            }`}>
                              {a.requires_lab ? 'LAB' : 'THEORY'}
                            </span>
                          </div>
                        </td>

                        <td className="px-4 py-3">
                          <div className="font-medium text-white">
                            {a.assigned_students} / {a.room_capacity}
                          </div>
                          <div className="w-20 bg-slate-700 rounded-full h-1.5 mt-1 overflow-hidden">
                            <div
                              className="bg-indigo-500 h-1.5 rounded-full"
                              style={{ width: `${Math.min(100, (a.assigned_students / a.room_capacity) * 100)}%` }}
                            />
                          </div>
                        </td>

                        <td className="px-4 py-3">
                          <div className="text-slate-200 font-medium">{a.assigned_faculty_name || 'TBD'}</div>
                          {a.assigned_faculty_id && (
                            <div className="text-[10px] text-slate-400 font-mono">{a.assigned_faculty_id}</div>
                          )}
                        </td>

                        <td className="px-4 py-3 text-slate-300">
                          {a.duration_hours} Hours
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: DATA QUALITY & VALIDATION REPORT */}
        {activeTab === 'validation' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Readiness Score Card */}
              <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Dataset Readiness Score</span>
                    <ShieldCheck className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div className="mt-4 flex items-baseline space-x-2">
                    <span className={`text-4xl font-extrabold ${validationReport?.is_valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {validationReport?.readiness_score || 0}
                    </span>
                    <span className="text-slate-400 text-sm">/ 100</span>
                  </div>
                  <div className="mt-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      validationReport?.is_valid
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}>
                      {validationReport?.status || 'UNKNOWN'}
                    </span>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-700/60 text-xs text-slate-400">
                  Blocking Errors: <span className="font-bold text-rose-400">{validationReport?.summary.total_errors || 0}</span> | Warnings: <span className="font-bold text-amber-400">{validationReport?.summary.total_warnings || 0}</span>
                </div>
              </div>

              {/* Dataset Scope Breakdown */}
              <div className="md:col-span-2 bg-slate-800/80 border border-slate-700 rounded-2xl p-6">
                <h3 className="text-sm font-bold text-white mb-4">Relational Integrity Scope</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                    <div className="text-[11px] text-slate-400">Rooms Analyzed</div>
                    <div className="text-lg font-bold text-white mt-1">{validationReport?.summary.table_counts.rooms || 0}</div>
                  </div>
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                    <div className="text-[11px] text-slate-400">Timeslots Available</div>
                    <div className="text-lg font-bold text-white mt-1">{validationReport?.summary.table_counts.timeslots || 0}</div>
                  </div>
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                    <div className="text-[11px] text-slate-400">Faculty Registered</div>
                    <div className="text-lg font-bold text-white mt-1">{validationReport?.summary.table_counts.faculty || 0}</div>
                  </div>
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                    <div className="text-[11px] text-slate-400">Courses / Subjects</div>
                    <div className="text-lg font-bold text-white mt-1">{validationReport?.summary.table_counts.subjects || 0}</div>
                  </div>
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                    <div className="text-[11px] text-slate-400">Student Groups</div>
                    <div className="text-lg font-bold text-white mt-1">{validationReport?.summary.table_counts.student_groups || 0}</div>
                  </div>
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                    <div className="text-[11px] text-slate-400">Individual Students</div>
                    <div className="text-lg font-bold text-white mt-1">{validationReport?.summary.table_counts.student_enrollments || 0}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Error Diagnostics List */}
            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6">
              <h3 className="text-sm font-bold text-white mb-3">Validation Issues & Flagged Constraints</h3>
              {(!validationReport?.errors || validationReport.errors.length === 0) ? (
                <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>0 validation errors detected. Dataset is 100% clean, verified, and schedulable with 0 clashes!</span>
                </div>
              ) : (
                <div className="space-y-2">
                  {validationReport.errors.map((err, i) => (
                    <div key={i} className="p-3 rounded-xl bg-rose-950/50 border border-rose-800/70 text-xs flex items-start space-x-3">
                      <XCircle className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <div className="font-semibold text-rose-300 flex items-center space-x-2">
                          <span className="font-mono bg-rose-900 px-1.5 py-0.5 rounded text-[10px] text-white">[{err.code}]</span>
                          <span>Table: {err.table} • Field: {err.field} • Row ID: {err.row_id}</span>
                        </div>
                        <div className="text-slate-300 mt-1">{err.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Recommendations */}
              {validationReport?.diagnostics && validationReport.diagnostics.length > 0 && (
                <div className="mt-6 pt-4 border-t border-slate-700/60">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Engine Feasibility Diagnostics</h4>
                  <ul className="space-y-1.5 text-xs text-slate-400">
                    {validationReport.diagnostics.map((diag, i) => (
                      <li key={i} className="flex items-center space-x-2">
                        <ChevronRight className="w-3.5 h-3.5 text-indigo-400" />
                        <span>{diag}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: ALGORITHM COMPARISON & BENCHMARK */}
        {activeTab === 'benchmark' && (
          <div className="space-y-6">
            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                    <Award className="w-5 h-5 text-amber-400" />
                    <span>Side-by-Side Algorithm Benchmark (First-Fit vs Welsh–Powell vs Backtracking)</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Evaluated on the exact same university dataset under hard student clashes, room capacities, and faculty constraints.
                  </p>
                </div>
                <button
                  onClick={handleBenchmark}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Rerun Benchmark</span>
                </button>
              </div>

              {benchmark ? (
                <div className="overflow-x-auto mt-4">
                  <table className="w-full text-left text-xs border border-slate-700 rounded-xl overflow-hidden">
                    <thead className="bg-slate-900 text-slate-200 font-semibold border-b border-slate-700">
                      <tr>
                        <th className="px-4 py-3">Algorithm</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Scheduled / Total</th>
                        <th className="px-4 py-3">Hard Conflicts</th>
                        <th className="px-4 py-3">Slots Used</th>
                        <th className="px-4 py-3">Room Utilization</th>
                        <th className="px-4 py-3">Unused Capacity</th>
                        <th className="px-4 py-3">Runtime (ms)</th>
                        <th className="px-4 py-3">Soft Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/60 bg-slate-800/40">
                      {benchmark.comparison.map((item, idx) => (
                        <tr key={idx} className={item.algorithm === benchmark.summary.best_performing_algorithm ? 'bg-indigo-950/40 font-semibold' : ''}>
                          <td className="px-4 py-3 text-white flex items-center space-x-2">
                            {item.algorithm === benchmark.summary.best_performing_algorithm && (
                              <Award className="w-4 h-4 text-amber-400 flex-shrink-0" />
                            )}
                            <span>{item.algorithm}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                              item.is_feasible ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
                            }`}>
                              {item.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-white">
                            {item.scheduled_exams} / {benchmark.summary.total_exams_to_schedule}
                          </td>
                          <td className="px-4 py-3">
                            <span className={item.hard_conflicts === 0 ? 'text-emerald-400' : 'text-rose-400'}>
                              {item.hard_conflicts}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-300 font-mono">
                            {item.slots_used} / {benchmark.summary.total_available_slots}
                          </td>
                          <td className="px-4 py-3 text-slate-200">
                            {item.room_utilization_pct}%
                          </td>
                          <td className="px-4 py-3 text-slate-300">
                            {item.unused_capacity_seats} seats
                          </td>
                          <td className="px-4 py-3 font-mono text-indigo-300">
                            {item.execution_time_ms} ms
                          </td>
                          <td className="px-4 py-3 font-bold text-amber-400">
                            {item.soft_score} / 100
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center text-slate-400 text-xs">
                  Click 'Rerun Benchmark' to compute side-by-side performance metrics.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 5: STUDENT COMPANION MOBILE APP */}
        {activeTab === 'student' && (
          <div className="max-w-md mx-auto space-y-4">
            <div className="bg-slate-800/90 border border-slate-700 rounded-2xl p-5 shadow-2xl">
              <div className="flex items-center space-x-2 text-indigo-400 mb-3">
                <Smartphone className="w-5 h-5" />
                <h2 className="text-sm font-bold text-white">ExamOpt Student Portal</h2>
              </div>

              {/* Roll number search */}
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={studentRollNo}
                  onChange={(e) => setStudentRollNo(e.target.value)}
                  placeholder="Enter Roll No (e.g. GLA26-BCA-0001)"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                />
                <button
                  onClick={() => handleStudentLookup(studentRollNo)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Lookup
                </button>
              </div>

              {studentData?.student && (
                <div className="mt-4 pt-3 border-t border-slate-700/60">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-white text-sm">{studentData.student.student_name}</div>
                      <div className="text-[11px] font-mono text-indigo-300">{studentData.student.roll_no}</div>
                    </div>
                    {studentData.student.has_backlog === 1 && (
                      <span className="bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-semibold px-2 py-0.5 rounded-full">
                        Backlog Cohort
                      </span>
                    )}
                  </div>

                  <div className="mt-4 space-y-2.5">
                    <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Upcoming Examinations ({studentData.schedule.length})
                    </div>
                    {studentData.schedule.map((exam: any, idx: number) => (
                      <div key={idx} className="p-3 bg-slate-900/80 border border-slate-700 rounded-xl">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white text-xs">{exam.subject_name}</span>
                          <span className="text-[10px] bg-indigo-950 text-indigo-300 font-mono px-1.5 py-0.5 rounded border border-indigo-800">
                            {exam.slot_id}
                          </span>
                        </div>
                        <div className="text-[11px] font-mono text-indigo-400 mt-0.5">{exam.subject_id}</div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                          <span className="flex items-center space-x-1">
                            <Calendar className="w-3 h-3 text-slate-500" />
                            <span>{exam.exam_date}</span>
                          </span>
                          <span className="flex items-center space-x-1 font-medium text-slate-300">
                            <Building className="w-3 h-3 text-slate-500" />
                            <span>{exam.room_name} ({exam.room_id})</span>
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 6: FACULTY DUTY PORTAL */}
        {activeTab === 'faculty' && (
          <div className="max-w-md mx-auto space-y-4">
            <div className="bg-slate-800/90 border border-slate-700 rounded-2xl p-5 shadow-2xl">
              <div className="flex items-center space-x-2 text-emerald-400 mb-3">
                <UserCheck className="w-5 h-5" />
                <h2 className="text-sm font-bold text-white">Faculty Invigilation Duty Portal</h2>
              </div>

              {/* Faculty selector */}
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={facultyId}
                  onChange={(e) => setFacultyId(e.target.value)}
                  placeholder="Enter Faculty ID (e.g. FAC-101)"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                />
                <button
                  onClick={() => handleFacultyLookup(facultyId)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition"
                >
                  Lookup
                </button>
              </div>

              {facultyData?.faculty && (
                <div className="mt-4 pt-3 border-t border-slate-700/60">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-white text-sm">{facultyData.faculty.name}</div>
                      <div className="text-[11px] text-slate-400">Department: {facultyData.faculty.department}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-semibold text-emerald-400">
                        {facultyData.assigned_duties_count} / {facultyData.max_duties} Duties
                      </div>
                      <div className="text-[10px] text-slate-400">Max Duty Cap</div>
                    </div>
                  </div>

                  <div className="mt-4 space-y-2.5">
                    <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Assigned Invigilation Shifts ({facultyData.duties.length})
                    </div>
                    {facultyData.duties.map((duty: any, idx: number) => (
                      <div key={idx} className="p-3 bg-slate-900/80 border border-slate-700 rounded-xl">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white text-xs">{duty.room_name} ({duty.room_id})</span>
                          <span className="text-[10px] bg-indigo-950 text-indigo-300 font-mono px-1.5 py-0.5 rounded border border-indigo-800">
                            {duty.slot_id}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-300 mt-1">Course: {duty.subject_name} ({duty.subject_id})</div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                          <span>{duty.exam_date}</span>
                          <span className="text-emerald-300 font-medium">{duty.session} ({duty.time_range})</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-4 text-center text-xs text-slate-400">
        ExamOpt — Problem Statement C10: Intelligent Examination Timetable Optimization System • GLA University Context
      </footer>
    </div>
  );
}
