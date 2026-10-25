"""
constraints.py
--------------
Defines and evaluates all Hard Constraints (H1-H9) and Soft Constraints (S1-S5).
Provides reusable violation checkers and cost functions for Backtracking,
Min-Conflicts, Simulated Annealing, and the live interactive UI.
"""

from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict
from core.models import ProblemData, Session, TimeSlotRoom


class ConstraintChecker:
    """
    Evaluates timetable assignments against all project specifications.
    
    Hard constraints (Must NEVER be violated):
      H1. Teacher cannot teach two sessions at the same time.
      H2. Class cannot have two sessions at the same time.
      H3. Room cannot be used for two sessions at the same time.
      H4. Room capacity must be at least the class strength.
      H5. Lab sessions must be in lab rooms; theory sessions in classrooms.
      H6. Teacher can only be scheduled in their available slots.
      H7. Every subject gets exactly its required weekly hours.
      H8. Teacher's load should not exceed their maximum weekly load.
      H9. Each class must have its lunch break in its assigned time slot.
      
    Soft constraints (Preferences / Quality optimization):
      S1. Minimize free periods (gaps) in a class's day. (Weight = 5)
      S2. Spread a subject's lectures across different days. (Weight = 10)
      S3. Lab sessions should occupy consecutive periods. (Weight = 15)
      S4. Respect teacher preferences (e.g., avoid 1st period). (Weight = 4)
      S5. Avoid more than 2 consecutive lectures for a teacher. (Weight = 8)
    """

    def __init__(self, data: ProblemData, all_sessions: List[Session]):
        self.data = data
        self.all_sessions = all_sessions
        self.session_map = {s.session_id: s for s in all_sessions}

    def evaluate(self, assignment: Dict[str, Tuple[int, int, str]]) -> Dict[str, Any]:
        """
        Complete timetable evaluation returning:
          - hard_violations: total count of hard violations
          - soft_penalty: total soft constraint penalty
          - total_cost: 1000 * hard_violations + soft_penalty
          - hard_details: human-readable descriptions of any hard violations
          - soft_details: human-readable descriptions of soft penalties
        """
        hard_details = self.get_hard_violations(assignment)
        soft_details, soft_score = self.get_soft_penalties(assignment)
        hard_count = len(hard_details)
        total_cost = (1000 * hard_count) + soft_score

        return {
            "hard_violations": hard_count,
            "soft_penalty": soft_score,
            "total_cost": total_cost,
            "hard_details": hard_details,
            "soft_details": soft_details,
            "is_valid": hard_count == 0
        }

    # -------------------------------------------------------------------------
    # HARD CONSTRAINTS (H1 to H9)
    # -------------------------------------------------------------------------
    def get_hard_violations(self, assignment: Dict[str, Tuple[int, int, str]]) -> List[str]:
        """Returns a list of human-readable violation descriptions."""
        violations = []
        days_names = self.data.time_structure.days

        # Track clashes per (day, period)
        teacher_slots = defaultdict(list)   # (teacher, day, period) -> [session_ids]
        class_slots = defaultdict(list)     # (class, day, period) -> [session_ids]
        room_slots = defaultdict(list)      # (room, day, period) -> [session_ids]
        teacher_load = defaultdict(int)     # teacher -> count of scheduled sessions
        scheduled_sessions_per_class_subj = defaultdict(int)

        for session_id, slot in assignment.items():
            if slot is None:
                continue
            day, period, room_name = slot
            session = self.session_map[session_id]
            day_name = days_names[day] if day < len(days_names) else f"Day {day}"

            # H1: Teacher clash tracking
            teacher_slots[(session.teacher_name, day, period)].append(session_id)
            teacher_load[session.teacher_name] += 1

            # H2: Class clash tracking
            class_slots[(session.class_name, day, period)].append(session_id)

            # H3: Room clash tracking
            room_slots[(room_name, day, period)].append(session_id)

            # Track subject hours for H7
            scheduled_sessions_per_class_subj[(session.class_name, session.subject_code)] += 1

            # H4: Room capacity >= class strength
            cls_obj = self.data.classes.get(session.class_name)
            room_obj = self.data.rooms.get(room_name)
            if cls_obj and room_obj:
                if room_obj.capacity < cls_obj.strength:
                    violations.append(
                        f"H4 (Room Capacity): {session.class_name} (strength {cls_obj.strength}) "
                        f"assigned to {room_name} (capacity {room_obj.capacity}) on {day_name} P{period + 1}."
                    )

            # H5: Lab sessions in lab rooms; theory in classrooms
            if room_obj:
                if session.is_lab and room_obj.room_type != "lab":
                    violations.append(
                        f"H5 (Room Type): Lab session {session.subject_code} ({session.class_name}) "
                        f"assigned to classroom {room_name} on {day_name} P{period + 1}."
                    )
                elif not session.is_lab and room_obj.room_type != "classroom":
                    violations.append(
                        f"H5 (Room Type): Theory session {session.subject_code} ({session.class_name}) "
                        f"assigned to lab {room_name} on {day_name} P{period + 1}."
                    )

            # H6: Teacher unavailable slots
            t_obj = self.data.teachers.get(session.teacher_name)
            if t_obj and (day, period) in t_obj.unavailable_slots:
                violations.append(
                    f"H6 (Teacher Unavailability): {session.teacher_name} is marked unavailable "
                    f"on {day_name} P{period + 1} (Session {session.subject_code} for {session.class_name})."
                )

            # H9: Class lunch break clash
            if cls_obj and period == cls_obj.lunch_break_period:
                violations.append(
                    f"H9 (Lunch Break Clash): {session.class_name} scheduled during its lunch break "
                    f"(P{period + 1}) on {day_name}."
                )

        # Check H1 (Teacher Clashes)
        for (teacher, day, period), s_ids in teacher_slots.items():
            if len(s_ids) > 1:
                day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                classes_str = ", ".join([self.session_map[sid].class_name for sid in s_ids])
                violations.append(
                    f"H1 (Teacher Clash): {teacher} has {len(s_ids)} sessions at the same time "
                    f"on {day_name} P{period + 1} (Classes: {classes_str})."
                )

        # Check H2 (Class Clashes)
        for (cls_name, day, period), s_ids in class_slots.items():
            if len(s_ids) > 1:
                day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                subjs_str = ", ".join([self.session_map[sid].subject_code for sid in s_ids])
                violations.append(
                    f"H2 (Class Clash): {cls_name} has {len(s_ids)} sessions at the same time "
                    f"on {day_name} P{period + 1} (Subjects: {subjs_str})."
                )

        # Check H3 (Room Clashes)
        for (rm, day, period), s_ids in room_slots.items():
            if len(s_ids) > 1:
                day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                violations.append(
                    f"H3 (Room Clash): {rm} is double-booked by {len(s_ids)} sessions "
                    f"on {day_name} P{period + 1}."
                )

        # Check H7: Required weekly hours
        for cls_name, cls_obj in self.data.classes.items():
            for scode in cls_obj.subjects:
                if scode in self.data.subjects:
                    expected = self.data.subjects[scode].weekly_hours
                    actual = scheduled_sessions_per_class_subj.get((cls_name, scode), 0)
                    if actual < expected:
                        violations.append(
                            f"H7 (Weekly Hours): {cls_name} - {scode} has only {actual}/{expected} hours scheduled."
                        )

        # Check H8: Teacher max weekly load
        for t_name, t_obj in self.data.teachers.items():
            load = teacher_load.get(t_name, 0)
            if load > t_obj.max_weekly_load:
                violations.append(
                    f"H8 (Teacher Load Exceeded): {t_name} is assigned {load} hours, "
                    f"exceeding max limit of {t_obj.max_weekly_load}."
                )

        return violations

    # -------------------------------------------------------------------------
    # SOFT CONSTRAINTS (S1 to S5)
    # -------------------------------------------------------------------------
    def get_soft_penalties(self, assignment: Dict[str, Tuple[int, int, str]]) -> Tuple[List[str], int]:
        """
        Evaluates soft constraints and returns:
          (list of penalty descriptions, total soft penalty score)
        """
        penalties = []
        total_score = 0
        days_names = self.data.time_structure.days
        num_days = self.data.time_structure.num_days
        periods_per_day = self.data.time_structure.periods_per_day

        # Organize schedule for fast query
        class_day_periods = defaultdict(lambda: defaultdict(list))  # class -> day -> [periods]
        teacher_day_periods = defaultdict(lambda: defaultdict(list)) # teacher -> day -> [periods]
        class_subj_day_counts = defaultdict(lambda: defaultdict(int)) # (class, subj) -> day -> count
        class_lab_sessions = defaultdict(lambda: defaultdict(list)) # (class, subj) -> day -> [periods]

        for session_id, slot in assignment.items():
            if slot is None:
                continue
            day, period, _ = slot
            session = self.session_map[session_id]

            class_day_periods[session.class_name][day].append(period)
            teacher_day_periods[session.teacher_name][day].append(period)
            class_subj_day_counts[(session.class_name, session.subject_code)][day] += 1

            if session.is_lab:
                class_lab_sessions[(session.class_name, session.subject_code)][day].append(period)

            # S4: Respect teacher preferences (e.g. avoid period 0 / first period)
            t_obj = self.data.teachers.get(session.teacher_name)
            if t_obj and period in t_obj.preferred_avoid_periods:
                cost = 4
                total_score += cost
                day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                penalties.append(
                    f"S4 (Teacher Preference): {session.teacher_name} prefers not to teach in period P{period + 1} "
                    f"on {day_name} (+{cost} pts)."
                )

        # S1: Minimize free periods (gaps) in a class's day (Weight = 5 per gap slot)
        for cls_name, day_dict in class_day_periods.items():
            lunch = self.data.classes[cls_name].lunch_break_period
            for day, periods in day_dict.items():
                if len(periods) > 1:
                    min_p = min(periods)
                    max_p = max(periods)
                    occupied = set(periods)
                    gaps = 0
                    for p in range(min_p, max_p + 1):
                        if p not in occupied and p != lunch:
                            gaps += 1
                    if gaps > 0:
                        cost = gaps * 5
                        total_score += cost
                        day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                        penalties.append(
                            f"S1 (Class Gaps): {cls_name} has {gaps} free period(s) on {day_name} (+{cost} pts)."
                        )

        # S2: Spread a subject's lectures across different days (Weight = 10 per extra lecture on same day)
        for (cls_name, scode), day_counts in class_subj_day_counts.items():
            subj = self.data.subjects.get(scode)
            if subj and subj.subject_type == "theory":
                for day, count in day_counts.items():
                    if count > 1:
                        excess = count - 1
                        cost = excess * 10
                        total_score += cost
                        day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                        penalties.append(
                            f"S2 (Subject Spread): {cls_name} has {count} lectures of {scode} on {day_name} (+{cost} pts)."
                        )

        # S3: Lab sessions should occupy consecutive periods (Weight = 15 if split)
        for (cls_name, scode), day_dict in class_lab_sessions.items():
            for day, periods in day_dict.items():
                if len(periods) > 1:
                    sorted_p = sorted(periods)
                    is_consecutive = all(sorted_p[i+1] == sorted_p[i] + 1 for i in range(len(sorted_p) - 1))
                    if not is_consecutive:
                        cost = 15
                        total_score += cost
                        day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                        penalties.append(
                            f"S3 (Consecutive Labs): Lab {scode} for {cls_name} is split into non-consecutive periods "
                            f"{[p+1 for p in sorted_p]} on {day_name} (+{cost} pts)."
                        )

        # S5: Avoid more than 2 consecutive lectures for a teacher (Weight = 8 per extra consecutive lecture)
        for t_name, day_dict in teacher_day_periods.items():
            for day, periods in day_dict.items():
                if len(periods) > 2:
                    sorted_p = sorted(periods)
                    current_streak = 1
                    for i in range(1, len(sorted_p)):
                        if sorted_p[i] == sorted_p[i - 1] + 1:
                            current_streak += 1
                            if current_streak > 2:
                                cost = 8
                                total_score += cost
                                day_name = days_names[day] if day < len(days_names) else f"Day {day}"
                                penalties.append(
                                    f"S5 (Teacher Fatigue): {t_name} has {current_streak} back-to-back lectures "
                                    f"on {day_name} (+{cost} pts)."
                                )
                        else:
                            current_streak = 1

        return penalties, total_score

    # -------------------------------------------------------------------------
    # LOCAL SEARCH FAST CONFLICT CHECKER
    # -------------------------------------------------------------------------
    def count_conflicts_for_variable(
        self,
        var_id: str,
        slot: Tuple[int, int, str],
        assignment: Dict[str, Tuple[int, int, str]]
    ) -> int:
        """
        Counts how many conflicts are caused if var_id is assigned to slot (day, period, room),
        assuming other variables remain at their current assignment.
        Used extensively by Min-Conflicts and Simulated Annealing.
        """
        day, period, room = slot
        session = self.session_map[var_id]
        conflicts = 0

        # Unary domain checks
        cls_obj = self.data.classes[session.class_name]
        rm_obj = self.data.rooms[room]
        t_obj = self.data.teachers[session.teacher_name]

        # Lunch clash
        if period == cls_obj.lunch_break_period:
            conflicts += 1

        # Capacity clash
        if rm_obj.capacity < cls_obj.strength:
            conflicts += 1

        # Room type mismatch
        if session.is_lab and rm_obj.room_type != "lab":
            conflicts += 1
        elif not session.is_lab and rm_obj.room_type != "classroom":
            conflicts += 1

        # Teacher unavailability
        if (day, period) in t_obj.unavailable_slots:
            conflicts += 1

        # Binary clashes against other assigned sessions
        for other_id, other_slot in assignment.items():
            if other_id == var_id or other_slot is None:
                continue
            o_day, o_period, o_room = other_slot
            if o_day == day and o_period == period:
                other_sess = self.session_map[other_id]
                # Teacher clash
                if other_sess.teacher_name == session.teacher_name:
                    conflicts += 1
                # Class clash
                if other_sess.class_name == session.class_name:
                    conflicts += 1
                # Room clash
                if o_room == room:
                    conflicts += 1

        return conflicts
