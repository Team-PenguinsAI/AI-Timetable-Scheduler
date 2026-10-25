"""
models.py
---------
Data models and helper classes for the AI-Based Timetable Scheduler.
Designed to be clean, intuitive, and beginner-friendly with type annotations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import json


@dataclass
class Subject:
    """Represents an academic course/subject."""
    code: str                  # e.g., "CS101"
    name: str                  # e.g., "Data Structures"
    weekly_hours: int          # e.g., 3 hours per week
    subject_type: str = "theory"  # "theory" or "lab"


@dataclass
class Teacher:
    """Represents a faculty instructor."""
    name: str                           # e.g., "Dr. Sharma"
    subjects: List[str]                 # list of subject codes they can teach
    unavailable_slots: List[Tuple[int, int]] = field(default_factory=list)  # [(day, period), ...]
    max_weekly_load: int = 18           # maximum periods per week
    preferred_avoid_periods: List[int] = field(default_factory=list)  # e.g., [0] for avoid 1st period


@dataclass
class ClassBatch:
    """Represents a student cohort/class batch."""
    name: str                           # e.g., "CSE-A"
    strength: int                       # e.g., 40 students
    subjects: List[str]                 # list of subject codes enrolled
    lunch_break_period: int = 3         # index of lunch break period (0-indexed)


@dataclass
class Room:
    """Represents a lecture hall or laboratory."""
    name: str                           # e.g., "Room-101"
    capacity: int                       # e.g., 45 seats
    room_type: str = "classroom"        # "classroom" or "lab"


@dataclass
class TimeStructure:
    """Defines working days and daily period slots."""
    days: List[str] = field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    periods_per_day: int = 6            # e.g., 6 periods per day
    break_periods: List[int] = field(default_factory=lambda: [3])  # periods reserved for lunch/break

    @property
    def num_days(self) -> int:
        return len(self.days)


@dataclass
class Session:
    """
    The fundamental CSP Variable: Represents one single period session
    that must be scheduled on the timetable.
    """
    session_id: str             # Unique ID: e.g. "CSE-A_CS101_1"
    class_name: str             # e.g., "CSE-A"
    subject_code: str           # e.g., "CS101"
    subject_name: str           # e.g., "Data Structures"
    session_index: int          # 1, 2, 3 (which weekly lecture of this subject)
    is_lab: bool                # True if lab, False if theory
    teacher_name: str           # Pre-assigned eligible instructor

    def __hash__(self):
        return hash(self.session_id)

    def __eq__(self, other):
        if isinstance(other, Session):
            return self.session_id == other.session_id
        return False


@dataclass
class TimeSlotRoom:
    """
    The fundamental CSP Domain Value: A combination of (day, period, room).
    """
    day: int                    # 0 to num_days - 1
    period: int                 # 0 to periods_per_day - 1
    room_name: str              # e.g. "Room-101"

    def to_tuple(self) -> Tuple[int, int, str]:
        return (self.day, self.period, self.room_name)


class ProblemData:
    """
    Container for all problem input data, with JSON / dictionary loading
    and sanity-checking validation.
    """
    def __init__(
        self,
        subjects: List[Subject],
        teachers: List[Teacher],
        classes: List[ClassBatch],
        rooms: List[Room],
        time_structure: TimeStructure
    ):
        self.subjects = {s.code: s for s in subjects}
        self.teachers = {t.name: t for t in teachers}
        self.classes = {c.name: c for c in classes}
        self.rooms = {r.name: r for r in rooms}
        self.time_structure = time_structure

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProblemData":
        """Builds ProblemData from a dictionary (e.g. loaded from JSON)."""
        subjects = [
            Subject(
                code=s["code"],
                name=s["name"],
                weekly_hours=int(s["weekly_hours"]),
                subject_type=s.get("type", s.get("subject_type", "theory")).lower()
            )
            for s in data["subjects"]
        ]

        teachers = []
        for t in data["teachers"]:
            unavailable = []
            for u in t.get("unavailable_slots", []):
                # Accepts [day, period] or "day,period"
                if isinstance(u, (list, tuple)):
                    unavailable.append((int(u[0]), int(u[1])))
                elif isinstance(u, str):
                    parts = u.split(",")
                    unavailable.append((int(parts[0]), int(parts[1])))
            
            avoid = t.get("preferred_avoid_periods", [])
            teachers.append(
                Teacher(
                    name=t["name"],
                    subjects=t["subjects"],
                    unavailable_slots=unavailable,
                    max_weekly_load=int(t.get("max_weekly_load", 20)),
                    preferred_avoid_periods=[int(p) for p in avoid]
                )
            )

        classes = [
            ClassBatch(
                name=c["name"],
                strength=int(c["strength"]),
                subjects=c["subjects"],
                lunch_break_period=int(c.get("lunch_break_period", 3))
            )
            for c in data["classes"]
        ]

        rooms = [
            Room(
                name=r["name"],
                capacity=int(r["capacity"]),
                room_type=r.get("type", r.get("room_type", "classroom")).lower()
            )
            for r in data["rooms"]
        ]

        ts_data = data.get("time_structure", {})
        time_structure = TimeStructure(
            days=ts_data.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
            periods_per_day=int(ts_data.get("periods_per_day", 6)),
            break_periods=ts_data.get("break_periods", [3])
        )

        return cls(subjects, teachers, classes, rooms, time_structure)

    @classmethod
    def from_json_file(cls, filepath: str) -> "ProblemData":
        """Loads ProblemData directly from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes problem data to a JSON-compatible dictionary."""
        return {
            "time_structure": {
                "days": self.time_structure.days,
                "periods_per_day": self.time_structure.periods_per_day,
                "break_periods": self.time_structure.break_periods
            },
            "subjects": [
                {
                    "code": s.code,
                    "name": s.name,
                    "weekly_hours": s.weekly_hours,
                    "type": s.subject_type
                }
                for s in self.subjects.values()
            ],
            "teachers": [
                {
                    "name": t.name,
                    "subjects": t.subjects,
                    "unavailable_slots": [list(u) for u in t.unavailable_slots],
                    "max_weekly_load": t.max_weekly_load,
                    "preferred_avoid_periods": t.preferred_avoid_periods
                }
                for t in self.teachers.values()
            ],
            "classes": [
                {
                    "name": c.name,
                    "strength": c.strength,
                    "subjects": c.subjects,
                    "lunch_break_period": c.lunch_break_period
                }
                for c in self.classes.values()
            ],
            "rooms": [
                {
                    "name": r.name,
                    "capacity": r.capacity,
                    "type": r.room_type
                }
                for r in self.rooms.values()
            ]
        }

    def validate(self) -> List[str]:
        """
        Validates problem input data to ensure it's logically sound
        and mathematically solvable. Returns a list of error/warning strings.
        """
        errors = []
        total_slots_per_room = self.time_structure.num_days * self.time_structure.periods_per_day

        # Check subject references
        for c in self.classes.values():
            for code in c.subjects:
                if code not in self.subjects:
                    errors.append(f"Class '{c.name}' references unknown subject '{code}'.")

        # Check teacher availability for each subject
        for s in self.subjects.values():
            capable = [t for t in self.teachers.values() if s.code in t.subjects]
            if not capable:
                errors.append(f"No teacher found who can teach subject '{s.name}' ({s.code}).")

        # Check total capacity vs required hours
        total_theory_hours = 0
        total_lab_hours = 0
        for c in self.classes.values():
            for code in c.subjects:
                if code in self.subjects:
                    subj = self.subjects[code]
                    if subj.subject_type == "lab":
                        total_lab_hours += subj.weekly_hours
                    else:
                        total_theory_hours += subj.weekly_hours

        classroom_count = sum(1 for r in self.rooms.values() if r.room_type == "classroom")
        lab_count = sum(1 for r in self.rooms.values() if r.room_type == "lab")

        max_available_classroom_slots = classroom_count * total_slots_per_room
        max_available_lab_slots = lab_count * total_slots_per_room

        if total_theory_hours > max_available_classroom_slots:
            errors.append(
                f"Total theory hours ({total_theory_hours}) exceeds available classroom slots ({max_available_classroom_slots})."
            )
        if total_lab_hours > max_available_lab_slots:
            errors.append(
                f"Total lab hours ({total_lab_hours}) exceeds available lab slots ({max_available_lab_slots})."
            )

        return errors
