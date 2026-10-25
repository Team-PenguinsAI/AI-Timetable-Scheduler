"""
app.py
------
Interactive Streamlit Web Application for the AI-Based Timetable Scheduler.

Features:
  1. Data Input: Preloaded Small/Large datasets or Upload Custom JSON/CSV files with live validation.
  2. Algorithm Selector:
     - Plain Backtracking (Baseline)
     - Heuristic Backtracking (MRV + Degree + Forward Checking)
     - Min-Conflicts Local Search (with random walk/restart)
     - Simulated Annealing (+6 Bonus)
     - Hybrid CSP + SA (+6 Bonus)
  3. Real-time Metrics: Time taken, nodes/iterations, hard violations, soft penalties, cost score.
  4. 2D Timetable Views: By Class, By Teacher, By Room.
  5. Interactive Manual Editor with Instant Conflict Detection (Flags any H1-H9 violation immediately).
  6. Direct Export to CSV and multi-sheet Excel (.xlsx).
  7. Experimental Benchmark & Convergence Analysis visualization.
"""

import streamlit as st
import pandas as pd
import json
import time
import os
import io

from core.models import ProblemData, Session
from core.csp_problem import TimetableCSP
from core.constraints import ConstraintChecker
from core.backtracking import BacktrackingSolver
from core.min_conflicts import MinConflictsSolver
from core.simulated_annealing import SimulatedAnnealingSolver
from core.utils import (
    build_class_grid,
    build_teacher_grid,
    build_room_grid,
    export_all_to_csv,
    export_all_to_excel_bytes
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Timetable Scheduler",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished, beginner-friendly UI
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .clash-card {
        background-color: #fef2f2;
        border-left: 5px solid #ef4444;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 8px;
    }
    .success-card {
        background-color: #f0fdf4;
        border-left: 5px solid #22c55e;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "problem_data" not in st.session_state:
    st.session_state.problem_data = None
if "current_dataset_name" not in st.session_state:
    st.session_state.current_dataset_name = "Small Dataset"
if "assignment" not in st.session_state:
    st.session_state.assignment = None
if "csp" not in st.session_state:
    st.session_state.csp = None
if "checker" not in st.session_state:
    st.session_state.checker = None
if "last_stats" not in st.session_state:
    st.session_state.last_stats = None


# -----------------------------------------------------------------------------
# SIDEBAR: DATA INPUT & CONFIGURATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/calendar--v1.png", width=64)
    st.title("Scheduler Setup")

    st.subheader("1. Select Dataset")
    dataset_option = st.selectbox(
        "Choose problem input:",
        [
            "Small Dataset (3 Classes, 6 Teachers, 4 Rooms)",
            "Large Dataset (8 Classes, 16 Teachers, 10 Rooms)",
            "Upload Custom JSON File",
            "Upload CSV Files"
        ]
    )

    loaded_data = None

    if "Small Dataset" in dataset_option:
        loaded_data = ProblemData.from_json_file("data/small_dataset.json")
        st.session_state.current_dataset_name = "Small Dataset (5 days x 6 periods)"
    elif "Large Dataset" in dataset_option:
        loaded_data = ProblemData.from_json_file("data/large_dataset.json")
        st.session_state.current_dataset_name = "Large Dataset (5 days x 7 periods)"
    elif "Upload Custom JSON" in dataset_option:
        uploaded_json = st.file_uploader("Upload JSON configuration:", type=["json"])
        if uploaded_json:
            try:
                dict_data = json.load(uploaded_json)
                loaded_data = ProblemData.from_dict(dict_data)
                st.session_state.current_dataset_name = uploaded_json.name
            except Exception as e:
                st.error(f"Error parsing JSON: {e}")
    elif "Upload CSV Files" in dataset_option:
        st.markdown("**Upload entity CSV files:**")
        f_subjs = st.file_uploader("Subjects CSV", type=["csv"], key="csv_subj")
        f_teach = st.file_uploader("Teachers CSV", type=["csv"], key="csv_teach")
        f_class = st.file_uploader("Classes CSV", type=["csv"], key="csv_class")
        f_rooms = st.file_uploader("Rooms CSV", type=["csv"], key="csv_rooms")

        if f_subjs and f_teach and f_class and f_rooms:
            try:
                # Load CSVs to DataFrames
                df_subjs = pd.read_csv(f_subjs)
                df_teach = pd.read_csv(f_teach)
                df_class = pd.read_csv(f_class)
                df_rooms = pd.read_csv(f_rooms)

                # Reconstruct dict format
                subj_list = df_subjs.to_dict(orient="records")
                teach_list = []
                for _, r in df_teach.iterrows():
                    unav = []
                    if pd.notna(r.get("unavailable_slots")):
                        for slot in str(r["unavailable_slots"]).split(";"):
                            if "," in slot:
                                parts = slot.split(",")
                                unav.append([int(parts[0]), int(parts[1])])
                    avoid = []
                    if pd.notna(r.get("preferred_avoid_periods")):
                        avoid = [int(p) for p in str(r["preferred_avoid_periods"]).split(";") if p.strip()]
                    teach_list.append({
                        "name": r["name"],
                        "subjects": str(r["subjects"]).split(";"),
                        "unavailable_slots": unav,
                        "max_weekly_load": int(r.get("max_weekly_load", 18)),
                        "preferred_avoid_periods": avoid
                    })

                class_list = []
                for _, r in df_class.iterrows():
                    class_list.append({
                        "name": r["name"],
                        "strength": int(r["strength"]),
                        "subjects": str(r["subjects"]).split(";"),
                        "lunch_break_period": int(r.get("lunch_break_period", 3))
                    })

                room_list = df_rooms.to_dict(orient="records")

                combined_dict = {
                    "time_structure": {
                        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                        "periods_per_day": 6,
                        "break_periods": [3]
                    },
                    "subjects": subj_list,
                    "teachers": teach_list,
                    "classes": class_list,
                    "rooms": room_list
                }
                loaded_data = ProblemData.from_dict(combined_dict)
                st.session_state.current_dataset_name = "Uploaded CSV Dataset"
            except Exception as e:
                st.error(f"Error reading CSV files: {e}")

    # Set and validate data
    if loaded_data:
        st.session_state.problem_data = loaded_data
        st.session_state.csp = TimetableCSP(loaded_data)
        st.session_state.checker = ConstraintChecker(loaded_data, st.session_state.csp.sessions)

        errors = loaded_data.validate()
        if not errors:
            st.success("✅ Dataset Solvable & Validated")
        else:
            for err in errors:
                st.warning(f"⚠️ {err}")

        # Quick summary stats in sidebar
        st.markdown(f"""
        **Dataset Summary:**
        - **Classes:** {len(loaded_data.classes)}
        - **Teachers:** {len(loaded_data.teachers)}
        - **Rooms:** {len(loaded_data.rooms)}
        - **Total Sessions to Place:** {len(st.session_state.csp.sessions)}
        """)

    st.divider()

    st.subheader("2. AI Search Algorithm")
    algorithm_choice = st.selectbox(
        "Choose generation algorithm:",
        [
            "Backtracking (with Heuristics: MRV + FC + Degree)",
            "Backtracking (Baseline Plain)",
            "Min-Conflicts Local Search",
            "Simulated Annealing (+6 Bonus)",
            "Hybrid CSP + Simulated Annealing (+6 Bonus)"
        ]
    )

    time_limit = st.slider("Time limit (seconds):", 1.0, 30.0, 10.0, 0.5)

    generate_btn = st.button("🚀 Generate Timetable", type="primary", use_container_width=True)


# -----------------------------------------------------------------------------
# MAIN APP HEADER
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">📅 AI-Based College Timetable Scheduler</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">Active Dataset: <b>{st.session_state.current_dataset_name}</b> | '
    'Constraint Satisfaction Problem & Local Search Solver</div>',
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# ALGORITHM EXECUTION
# -----------------------------------------------------------------------------
if generate_btn and st.session_state.problem_data:
    csp = st.session_state.csp
    checker = st.session_state.checker

    with st.spinner(f"Running {algorithm_choice}..."):
        start_ts = time.time()

        if "Baseline" in algorithm_choice:
            solver = BacktrackingSolver(csp)
            assignment, stats = solver.solve_plain(time_limit=time_limit)

        elif "Heuristics" in algorithm_choice:
            solver = BacktrackingSolver(csp)
            assignment, stats = solver.solve_heuristic(
                use_mrv=True, use_degree=True, use_forward_checking=True, time_limit=time_limit
            )

        elif "Min-Conflicts" in algorithm_choice:
            solver = MinConflictsSolver(csp, checker)
            assignment, stats = solver.solve(max_iterations=2000, time_limit=time_limit, seed=42)

        elif "Hybrid" in algorithm_choice:
            solver = SimulatedAnnealingSolver(csp, checker)
            assignment, stats = solver.solve_hybrid(time_limit=time_limit, seed=42)

        else:  # Simulated Annealing
            solver = SimulatedAnnealingSolver(csp, checker)
            assignment, stats = solver.solve(initial_temp=80.0, cooling_rate=0.99, time_limit=time_limit, seed=42)

        st.session_state.assignment = assignment
        st.session_state.last_stats = stats

# If no assignment yet generated, auto-run heuristic backtracking once on small dataset
if st.session_state.assignment is None and st.session_state.problem_data:
    bt = BacktrackingSolver(st.session_state.csp)
    assign, stats = bt.solve_heuristic(time_limit=10.0)
    st.session_state.assignment = assign
    st.session_state.last_stats = stats


# -----------------------------------------------------------------------------
# RESULTS BANNER & METRICS
# -----------------------------------------------------------------------------
if st.session_state.assignment is not None and st.session_state.last_stats is not None:
    eval_res = st.session_state.checker.evaluate(st.session_state.assignment)
    stats = st.session_state.last_stats

    # Status Notification
    if eval_res["hard_violations"] == 0:
        st.markdown(
            f'<div class="success-card"><b>✅ VALID TIMETABLE FOUND!</b> '
            f'Generated via <i>{stats.get("algorithm", "AI Search")}</i> with <b>0 Hard Constraint Clashes</b>.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="clash-card"><b>⚠️ HARD CONSTRAINTS VIOLATED:</b> '
            f'{eval_res["hard_violations"]} conflicts detected. Review details in the Constraints tab.</div>',
            unsafe_allow_html=True
        )

    # Metric Columns
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("⏱️ Time Taken", f"{stats.get('time_taken', 0):.3f} s")
    c2.metric("❌ Hard Violations", f"{eval_res['hard_violations']}")
    c3.metric("🎯 Soft Penalty", f"{eval_res['soft_penalty']} pts")
    
    nodes_val = stats.get("nodes_expanded", stats.get("iterations", "N/A"))
    c4.metric("🔄 Nodes / Iterations", f"{nodes_val}")
    c5.metric("💲 Total Cost", f"{eval_res['total_cost']}")


# -----------------------------------------------------------------------------
# MAIN DASHBOARD TABS
# -----------------------------------------------------------------------------
tab_grids, tab_editor, tab_analysis, tab_benchmarks, tab_export = st.tabs([
    "📊 Timetable Views",
    "✏️ Manual Schedule Editor",
    "⚖️ Constraint Breakdown",
    "📈 Experiments & Benchmarks",
    "💾 Export (CSV / Excel)"
])

# -----------------------------------------------------------------------------
# TAB 1: TIMETABLE VIEWS
# -----------------------------------------------------------------------------
with tab_grids:
    st.subheader("Timetable Grids")
    if st.session_state.assignment is not None:
        view_type = st.radio("Select Grid Perspective:", ["By Class", "By Teacher", "By Room"], horizontal=True)
        data = st.session_state.problem_data
        sessions = st.session_state.csp.sessions
        assignment = st.session_state.assignment

        if view_type == "By Class":
            selected_class = st.selectbox("Select Class:", list(data.classes.keys()))
            grid_df = build_class_grid(selected_class, assignment, sessions, data)
            st.dataframe(grid_df, use_container_width=True, height=260)

        elif view_type == "By Teacher":
            selected_teacher = st.selectbox("Select Teacher:", list(data.teachers.keys()))
            grid_df = build_teacher_grid(selected_teacher, assignment, sessions, data)
            st.dataframe(grid_df, use_container_width=True, height=260)

        else:
            selected_room = st.selectbox("Select Room:", list(data.rooms.keys()))
            grid_df = build_room_grid(selected_room, assignment, sessions, data)
            st.dataframe(grid_df, use_container_width=True, height=260)
    else:
        st.info("Click 'Generate Timetable' to view schedule grids.")

# -----------------------------------------------------------------------------
# TAB 2: MANUAL SCHEDULE EDITOR (WITH INSTANT CONFLICT DETECTION)
# -----------------------------------------------------------------------------
with tab_editor:
    st.subheader("Manual Schedule Editor & Instant Clash Checker")
    st.caption("Move any scheduled session to another time slot or room. The system immediately checks all Hard Constraints (H1-H9) and warns you of any conflict!")

    if st.session_state.assignment is not None:
        sessions = st.session_state.csp.sessions
        data = st.session_state.problem_data
        assignment = st.session_state.assignment

        # Create session dropdown labels
        session_options = {
            f"{s.class_name} | {s.subject_code} ({s.subject_name}) | {s.teacher_name} [Session {s.session_index}]": s.session_id
            for s in sessions
        }

        col_sel, col_dest = st.columns([1, 1])

        with col_sel:
            st.markdown("##### 1. Choose Session to Move")
            chosen_label = st.selectbox("Select Session:", list(session_options.keys()))
            chosen_id = session_options[chosen_label]
            curr_slot = assignment.get(chosen_id)

            if curr_slot:
                d_idx, p_idx, r_name = curr_slot
                d_name = data.time_structure.days[d_idx]
                st.info(f"**Current Placement:** {d_name}, Period {p_idx + 1} in {r_name}")

        with col_dest:
            st.markdown("##### 2. Choose New Destination")
            new_day = st.selectbox("Destination Day:", data.time_structure.days, index=curr_slot[0] if curr_slot else 0)
            new_day_idx = data.time_structure.days.index(new_day)

            new_period = st.selectbox(
                "Destination Period:",
                [f"Period {p + 1}" for p in range(data.time_structure.periods_per_day)],
                index=curr_slot[1] if curr_slot else 0
            )
            new_period_idx = int(new_period.split()[1]) - 1

            new_room = st.selectbox("Destination Room:", list(data.rooms.keys()))

        # Live conflict test without modifying original state until confirmed
        proposed_slot = (new_day_idx, new_period_idx, new_room)
        test_assignment = assignment.copy()
        test_assignment[chosen_id] = proposed_slot

        test_eval = st.session_state.checker.evaluate(test_assignment)

        st.divider()
        st.markdown("##### 3. Real-Time Conflict Analysis")

        if test_eval["hard_violations"] == 0:
            st.markdown(
                '<div class="success-card"><b>✅ VALID MOVE!</b> '
                'This placement causes <b>0 hard-constraint clashes</b>.</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="clash-card"><b>⚠️ {test_eval["hard_violations"]} HARD CONFLICT(S) DETECTED:</b><br>',
                unsafe_allow_html=True
            )
            for clash in test_eval["hard_details"]:
                st.markdown(f"- 🔴 **{clash}**")
            st.markdown('</div>', unsafe_allow_html=True)

        # Apply Move Button
        if st.button("💾 Apply Manual Move to Timetable", type="secondary"):
            st.session_state.assignment[chosen_id] = proposed_slot
            st.success("Session position updated in timetable!")
            st.rerun()

# -----------------------------------------------------------------------------
# TAB 3: CONSTRAINT BREAKDOWN & COST ANALYSIS
# -----------------------------------------------------------------------------
with tab_analysis:
    st.subheader("Constraints & Cost Function Breakdown")
    st.latex(r"\text{Cost} = 1000 \times (\text{Hard Violations}) + \text{Soft Penalties}")

    if st.session_state.assignment is not None:
        eval_res = st.session_state.checker.evaluate(st.session_state.assignment)

        c_hard, c_soft = st.columns(2)

        with c_hard:
            st.markdown("#### Hard Constraints (H1 - H9)")
            st.markdown("Must strictly equal 0 for feasibility:")
            hard_rules = [
                ("H1. Teacher Clash", "No teacher teaches two sessions at same time"),
                ("H2. Class Clash", "No class has two sessions at same time"),
                ("H3. Room Clash", "No room used for two sessions at same time"),
                ("H4. Room Capacity", "Room capacity >= class strength"),
                ("H5. Room Type", "Lab sessions in labs; theory in classrooms"),
                ("H6. Teacher Availability", "Teacher only scheduled in available slots"),
                ("H7. Weekly Hours", "Subject gets exactly its required hours"),
                ("H8. Teacher Max Load", "Teacher hours do not exceed max limit"),
                ("H9. Lunch Break", "No sessions during class lunch break")
            ]
            for h_code, desc in hard_rules:
                has_violation = any(h_code[:2] in v for v in eval_res["hard_details"])
                icon = "❌" if has_violation else "✅"
                st.markdown(f"**{icon} {h_code}**: {desc}")

            if eval_res["hard_details"]:
                st.error("Active Violations:")
                for d in eval_res["hard_details"]:
                    st.write(f"- {d}")

        with c_soft:
            st.markdown("#### Soft Constraints (S1 - S5)")
            st.markdown(f"Total Soft Penalty Score: **{eval_res['soft_penalty']} points**")
            soft_rules = [
                ("S1. Class Gaps (Weight: 5)", "Minimize free gap periods in class day"),
                ("S2. Subject Spread (Weight: 10)", "Spread theory lectures across days"),
                ("S3. Consecutive Labs (Weight: 15)", "2-period labs scheduled back-to-back"),
                ("S4. Teacher Preference (Weight: 4)", "Respect avoided periods (e.g. 1st period)"),
                ("S5. Teacher Fatigue (Weight: 8)", "Avoid >2 consecutive periods for a teacher")
            ]
            for s_code, desc in soft_rules:
                st.markdown(f"**{s_code}**: {desc}")

            if eval_res["soft_details"]:
                st.warning("Soft Penalties Incurred:")
                for d in eval_res["soft_details"][:8]:
                    st.write(f"- {d}")
                if len(eval_res["soft_details"]) > 8:
                    st.caption(f"...and {len(eval_res['soft_details']) - 8} more minor penalties.")

# -----------------------------------------------------------------------------
# TAB 4: EXPERIMENTS & BENCHMARKS
# -----------------------------------------------------------------------------
with tab_benchmarks:
    st.subheader("Algorithm Comparison & Convergence Graphs")
    st.markdown("Official benchmark comparing Backtracking Baseline, Backtracking Heuristic, Min-Conflicts, Simulated Annealing, and Hybrid CSP+SA.")

    # Show generated graphs if available
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if os.path.exists("min_conflicts_convergence.png"):
            st.image("min_conflicts_convergence.png", caption="Min-Conflicts Cost vs. Iterations")
        else:
            st.info("Run `python run_experiments.py` to generate Min-Conflicts graph.")

    with col_g2:
        if os.path.exists("algorithm_comparison_chart.png"):
            st.image("algorithm_comparison_chart.png", caption="Runtime Comparison Across Datasets")
        elif os.path.exists("sa_convergence.png"):
            st.image("sa_convergence.png", caption="Simulated Annealing Convergence")
        else:
            st.info("Run `python run_experiments.py` to generate comparison charts.")

    # Benchmark Results Tables
    if os.path.exists("benchmark_results.json"):
        with open("benchmark_results.json", "r") as f:
            b_data = json.load(f)

        st.markdown("#### Small Dataset Benchmark Table (Average over 10 runs)")
        small_df = pd.DataFrame(b_data["small_dataset"]).T
        small_df = small_df[["time_taken", "nodes_expanded", "hard_violations", "soft_penalty", "success_rate"]]
        small_df.columns = ["Time (s)", "Nodes/Iters", "Hard Violations", "Soft Penalty", "Success Rate"]
        st.dataframe(small_df, use_container_width=True)

        st.markdown("#### Large Dataset Benchmark Table (Average over 10 runs)")
        large_df = pd.DataFrame(b_data["large_dataset"]).T
        large_df = large_df[["time_taken", "nodes_expanded", "hard_violations", "soft_penalty", "success_rate"]]
        large_df.columns = ["Time (s)", "Nodes/Iters", "Hard Violations", "Soft Penalty", "Success Rate"]
        st.dataframe(large_df, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: EXPORT (CSV / EXCEL)
# -----------------------------------------------------------------------------
with tab_export:
    st.subheader("Export Generated Timetable")
    st.markdown("Download the complete generated timetable as CSV or Excel (.xlsx) file.")

    if st.session_state.assignment is not None:
        assignment = st.session_state.assignment
        sessions = st.session_state.csp.sessions
        data = st.session_state.problem_data

        csv_str = export_all_to_csv(assignment, sessions, data)
        excel_bytes = export_all_to_excel_bytes(assignment, sessions, data)

        col_csv, col_excel = st.columns(2)

        with col_csv:
            st.download_button(
                label="📥 Download Timetable as CSV",
                data=csv_str,
                file_name="college_timetable.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col_excel:
            st.download_button(
                label="📥 Download Multi-Sheet Excel Workbook (.xlsx)",
                data=excel_bytes,
                file_name="college_timetable.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.divider()
        st.markdown("#### Master Timetable Preview")
        preview_df = pd.read_csv(io.StringIO(csv_str))
        st.dataframe(preview_df, use_container_width=True, height=350)
    else:
        st.info("No timetable generated yet. Please generate a timetable first.")
