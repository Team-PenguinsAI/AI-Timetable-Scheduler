"""
csp_problem.py
--------------
Formulates the Timetable Scheduling task as a formal Constraint Satisfaction Problem (CSP).
Generates Variables, filtered Domains (unary constraints), and the Constraint Graph.
"""

from typing import List, Dict, Tuple, Set
from collections import defaultdict
from core.models import ProblemData, Session, TimeSlotRoom


class TimetableCSP:
    """
    Formal CSP representation of the timetable scheduling problem.

    Variables:
      - Each weekly hour of a subject for a class is one Session variable.
      - e.g. Session(id="CSE-A_CS101_1", class="CSE-A", subject="CS101", teacher="Dr. Sharma")

    Domains:
      - Set of legal (day, period, room) triples.
      - Unary constraints are pre-filtered during domain creation:
          * Room type matches session type (lab vs classroom)
          * Room capacity >= class strength
          * Period is not class lunch break
          * (day, period) is not in teacher's unavailable slots

    Constraint Graph:
      - Binary constraints connect variables that share the same class or teacher.
    """

    def __init__(self, data: ProblemData):
        self.data = data
        self.sessions: List[Session] = []
        self.domains: Dict[str, List[Tuple[int, int, str]]] = {}
        self.neighbors: Dict[str, Set[str]] = defaultdict(set)
        
        self._build_variables()
        self._build_domains()
        self._build_constraint_graph()

    def _build_variables(self):
        """Creates Session objects for all class-subject weekly hours."""
        teacher_loads = defaultdict(int)

        for cls_name, cls_obj in self.data.classes.items():
            for scode in cls_obj.subjects:
                if scode not in self.data.subjects:
                    continue
                subj = self.data.subjects[scode]
                is_lab = (subj.subject_type == "lab")

                # Find eligible teachers sorted by current assigned load (balanced assignment)
                eligible_teachers = [
                    t for t in self.data.teachers.values()
                    if scode in t.subjects and teacher_loads[t.name] + subj.weekly_hours <= t.max_weekly_load
                ]
                if not eligible_teachers:
                    # Fallback to any teacher capable of teaching the subject
                    eligible_teachers = [t for t in self.data.teachers.values() if scode in t.subjects]
                
                # Pick teacher with minimum current load
                if eligible_teachers:
                    eligible_teachers.sort(key=lambda t: teacher_loads[t.name])
                    assigned_teacher = eligible_teachers[0].name
                else:
                    assigned_teacher = "Unassigned"

                teacher_loads[assigned_teacher] += subj.weekly_hours

                # Create individual session variables
                for s_idx in range(1, subj.weekly_hours + 1):
                    session_id = f"{cls_name}_{scode}_s{s_idx}"
                    sess = Session(
                        session_id=session_id,
                        class_name=cls_name,
                        subject_code=scode,
                        subject_name=subj.name,
                        session_index=s_idx,
                        is_lab=is_lab,
                        teacher_name=assigned_teacher
                    )
                    self.sessions.append(sess)

    def _build_domains(self):
        """
        Builds the initial domain of (day, period, room) for each session,
        pruning values that violate unary constraints upfront.
        """
        num_days = self.data.time_structure.num_days
        num_periods = self.data.time_structure.periods_per_day

        for sess in self.sessions:
            cls_obj = self.data.classes[sess.class_name]
            t_obj = self.data.teachers.get(sess.teacher_name)
            domain_values = []

            for d in range(num_days):
                for p in range(num_periods):
                    # Unary Constraint 1: Class lunch break (H9)
                    if p == cls_obj.lunch_break_period:
                        continue

                    # Unary Constraint 2: Teacher unavailability (H6)
                    if t_obj and (d, p) in t_obj.unavailable_slots:
                        continue

                    for room_name, room_obj in self.data.rooms.items():
                        # Unary Constraint 3: Room type matching (H5)
                        if sess.is_lab and room_obj.room_type != "lab":
                            continue
                        if not sess.is_lab and room_obj.room_type != "classroom":
                            continue

                        # Unary Constraint 4: Room capacity >= class strength (H4)
                        if room_obj.capacity < cls_obj.strength:
                            continue

                        domain_values.append((d, p, room_name))

            self.domains[sess.session_id] = domain_values

    def _build_constraint_graph(self):
        """
        Builds adjacency list (neighbors) in the constraint graph:
        Two variables share a binary constraint if they share the same class or teacher.
        """
        for i in range(len(self.sessions)):
            for j in range(i + 1, len(self.sessions)):
                s1 = self.sessions[i]
                s2 = self.sessions[j]
                if s1.class_name == s2.class_name or s1.teacher_name == s2.teacher_name:
                    self.neighbors[s1.session_id].add(s2.session_id)
                    self.neighbors[s2.session_id].add(s1.session_id)

    def is_consistent(
        self,
        var_id: str,
        value: Tuple[int, int, str],
        current_assignment: Dict[str, Tuple[int, int, str]]
    ) -> bool:
        """
        Checks if assigning var_id = value is consistent with current_assignment.
        Must check:
          - Teacher not double-booked at (day, period)
          - Class not double-booked at (day, period)
          - Room not double-booked at (day, period)
        """
        day, period, room = value
        curr_session = next(s for s in self.sessions if s.session_id == var_id)

        for assigned_id, assigned_val in current_assignment.items():
            if assigned_val is None:
                continue
            a_day, a_period, a_room = assigned_val
            if a_day == day and a_period == period:
                # Same time slot!
                assigned_sess = next(s for s in self.sessions if s.session_id == assigned_id)
                # Teacher conflict
                if curr_session.teacher_name == assigned_sess.teacher_name:
                    return False
                # Class conflict
                if curr_session.class_name == assigned_sess.class_name:
                    return False
                # Room conflict
                if room == a_room:
                    return False

        return True
