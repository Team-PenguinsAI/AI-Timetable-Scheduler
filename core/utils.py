"""
utils.py
--------
Utility functions for:
  - Constructing 2D Timetable Grids (by Class, Teacher, Room)
  - Exporting schedules to CSV and multi-sheet Excel files
  - Pretty-printing schedules for console or logs
"""

from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import pandas as pd
import io
from core.models import ProblemData, Session


def build_class_grid(
    class_name: str,
    assignment: Dict[str, Tuple[int, int, str]],
    all_sessions: List[Session],
    data: ProblemData
) -> pd.DataFrame:
    """
    Builds a DataFrame representing the weekly schedule for a specific class.
    Rows: Days (Monday-Friday)
    Columns: Periods (P1, P2, P3...)
    Cells: "Subject (Teacher) [Room]" or "LUNCH BREAK" or "FREE"
    """
    session_map = {s.session_id: s for s in all_sessions}
    days = data.time_structure.days
    num_periods = data.time_structure.periods_per_day
    lunch_period = data.classes[class_name].lunch_break_period

    # Initialize empty grid
    grid = [["FREE" for _ in range(num_periods)] for _ in range(len(days))]

    # Mark lunch break
    for d in range(len(days)):
        if 0 <= lunch_period < num_periods:
            grid[d][lunch_period] = "🍽️ LUNCH BREAK"

    # Fill assigned sessions
    for sid, slot in assignment.items():
        if slot is None:
            continue
        sess = session_map[sid]
        if sess.class_name == class_name:
            day, period, room = slot
            lab_badge = "🧪 " if sess.is_lab else "📖 "
            cell_text = f"{lab_badge}{sess.subject_code}\n{sess.teacher_name}\n[{room}]"
            # In case of clash, append
            if grid[day][period] in ["FREE", "🍽️ LUNCH BREAK"]:
                grid[day][period] = cell_text
            else:
                grid[day][period] += f"\n⚠️ CLASH:\n{cell_text}"

    col_names = [f"Period {p + 1}" for p in range(num_periods)]
    return pd.DataFrame(grid, index=days, columns=col_names)


def build_teacher_grid(
    teacher_name: str,
    assignment: Dict[str, Tuple[int, int, str]],
    all_sessions: List[Session],
    data: ProblemData
) -> pd.DataFrame:
    """
    Builds a weekly schedule grid for a specific teacher.
    """
    session_map = {s.session_id: s for s in all_sessions}
    days = data.time_structure.days
    num_periods = data.time_structure.periods_per_day
    t_obj = data.teachers[teacher_name]

    grid = [["FREE" for _ in range(num_periods)] for _ in range(len(days))]

    # Mark unavailable slots
    for (d, p) in t_obj.unavailable_slots:
        if d < len(days) and p < num_periods:
            grid[d][p] = "🚫 UNAVAILABLE"

    # Fill assigned sessions
    for sid, slot in assignment.items():
        if slot is None:
            continue
        sess = session_map[sid]
        if sess.teacher_name == teacher_name:
            day, period, room = slot
            lab_badge = "🧪 " if sess.is_lab else "📖 "
            cell_text = f"{lab_badge}{sess.class_name}\n{sess.subject_code}\n[{room}]"
            if grid[day][period] in ["FREE", "🚫 UNAVAILABLE"]:
                grid[day][period] = cell_text
            else:
                grid[day][period] += f"\n⚠️ CLASH:\n{cell_text}"

    col_names = [f"Period {p + 1}" for p in range(num_periods)]
    return pd.DataFrame(grid, index=days, columns=col_names)


def build_room_grid(
    room_name: str,
    assignment: Dict[str, Tuple[int, int, str]],
    all_sessions: List[Session],
    data: ProblemData
) -> pd.DataFrame:
    """
    Builds a weekly schedule grid for a specific room.
    """
    session_map = {s.session_id: s for s in all_sessions}
    days = data.time_structure.days
    num_periods = data.time_structure.periods_per_day

    grid = [["EMPTY" for _ in range(num_periods)] for _ in range(len(days))]

    for sid, slot in assignment.items():
        if slot is None:
            continue
        day, period, room = slot
        if room == room_name:
            sess = session_map[sid]
            lab_badge = "🧪 " if sess.is_lab else "📖 "
            cell_text = f"{lab_badge}{sess.class_name}\n{sess.subject_code}\n({sess.teacher_name})"
            if grid[day][period] == "EMPTY":
                grid[day][period] = cell_text
            else:
                grid[day][period] += f"\n⚠️ CLASH:\n{cell_text}"

    col_names = [f"Period {p + 1}" for p in range(num_periods)]
    return pd.DataFrame(grid, index=days, columns=col_names)


def export_all_to_csv(
    assignment: Dict[str, Tuple[int, int, str]],
    all_sessions: List[Session],
    data: ProblemData
) -> str:
    """
    Exports complete timetable to flat CSV string.
    """
    session_map = {s.session_id: s for s in all_sessions}
    rows = []
    days = data.time_structure.days

    for sid, slot in assignment.items():
        if slot is None:
            continue
        day, period, room = slot
        sess = session_map[sid]
        rows.append({
            "Day": days[day] if day < len(days) else f"Day {day}",
            "Period": period + 1,
            "Class": sess.class_name,
            "Subject Code": sess.subject_code,
            "Subject Name": sess.subject_name,
            "Teacher": sess.teacher_name,
            "Room": room,
            "Type": "Lab" if sess.is_lab else "Theory"
        })

    df = pd.DataFrame(rows)
    # Sort logically
    if not df.empty:
        df = df.sort_values(by=["Class", "Day", "Period"])
    return df.to_csv(index=False)


def export_all_to_excel_bytes(
    assignment: Dict[str, Tuple[int, int, str]],
    all_sessions: List[Session],
    data: ProblemData
) -> bytes:
    """
    Exports complete timetable to multi-sheet Excel workbook in memory.
    Sheets:
      - All Sessions (Flat list)
      - Each Class Grid (CSE-A, CSE-B, etc.)
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Master List
        session_map = {s.session_id: s for s in all_sessions}
        rows = []
        days = data.time_structure.days

        for sid, slot in assignment.items():
            if slot is None:
                continue
            day, period, room = slot
            sess = session_map[sid]
            rows.append({
                "Day": days[day] if day < len(days) else f"Day {day}",
                "Period": period + 1,
                "Class": sess.class_name,
                "Subject Code": sess.subject_code,
                "Subject Name": sess.subject_name,
                "Teacher": sess.teacher_name,
                "Room": room,
                "Type": "Lab" if sess.is_lab else "Theory"
            })
        master_df = pd.DataFrame(rows)
        if not master_df.empty:
            master_df = master_df.sort_values(by=["Class", "Day", "Period"])
        master_df.to_excel(writer, sheet_name="Master Schedule", index=False)

        # Class Grids
        for cname in data.classes.keys():
            cdf = build_class_grid(cname, assignment, all_sessions, data)
            sheet_title = f"Class_{cname}"[:31]  # Excel 31 char limit
            cdf.to_excel(writer, sheet_name=sheet_title)

    return output.getvalue()
