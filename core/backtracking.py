"""
backtracking.py
---------------
Implementation of:
  1. Plain Backtracking Search (Baseline)
  2. Heuristic Backtracking Search (MRV + Degree Heuristic + Forward Checking + LCV)

Tracks:
  - Time taken (seconds)
  - Nodes expanded (recursive calls / state evaluations)
  - Success status
"""

import time
import copy
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any, Set
from core.csp_problem import TimetableCSP


class BacktrackingSolver:
    """
    Backtracking solver for the Timetable CSP.
    Supports both baseline plain search and advanced heuristics.
    """

    def __init__(self, csp: TimetableCSP):
        self.csp = csp
        self.nodes_expanded = 0
        self.start_time = 0.0
        self.time_limit = 30.0  # seconds

    # -------------------------------------------------------------------------
    # 1. PLAIN BACKTRACKING (BASELINE)
    # -------------------------------------------------------------------------
    def solve_plain(self, time_limit: float = 30.0) -> Tuple[Optional[Dict[str, Tuple[int, int, str]]], Dict[str, Any]]:
        """
        Baseline Backtracking search without heuristics:
          - Static variable ordering (first unassigned variable in list)
          - Static domain value ordering (first value in list)
          - Standard consistency check
        """
        self.nodes_expanded = 0
        self.time_limit = time_limit
        self.start_time = time.time()

        var_list = [s.session_id for s in self.csp.sessions]
        assignment: Dict[str, Tuple[int, int, str]] = {}

        success = self._backtrack_plain(assignment, var_list)
        elapsed = time.time() - self.start_time

        stats = {
            "algorithm": "Backtracking (Baseline)",
            "time_taken": round(elapsed, 4),
            "nodes_expanded": self.nodes_expanded,
            "success": success,
            "timed_out": elapsed >= self.time_limit
        }
        return (assignment if success else None), stats

    def _backtrack_plain(
        self,
        assignment: Dict[str, Tuple[int, int, str]],
        var_list: List[str]
    ) -> bool:
        """Recursive helper for plain backtracking."""
        self.nodes_expanded += 1

        # Check timeout to avoid freezing indefinitely on large datasets
        if time.time() - self.start_time > self.time_limit:
            return False

        # Base case: All variables assigned
        if len(assignment) == len(var_list):
            return True

        # Pick first unassigned variable (static order)
        var = next(v for v in var_list if v not in assignment)

        for val in self.csp.domains[var]:
            if self.csp.is_consistent(var, val, assignment):
                assignment[var] = val
                if self._backtrack_plain(assignment, var_list):
                    return True
                # Undo assignment (backtrack)
                del assignment[var]

        return False

    # -------------------------------------------------------------------------
    # 2. HEURISTIC BACKTRACKING (MRV + DEGREE + FORWARD CHECKING + LCV)
    # -------------------------------------------------------------------------
    def solve_heuristic(
        self,
        use_mrv: bool = True,
        use_degree: bool = True,
        use_forward_checking: bool = True,
        use_lcv: bool = True,
        time_limit: float = 30.0
    ) -> Tuple[Optional[Dict[str, Tuple[int, int, str]]], Dict[str, Any]]:
        """
        Advanced Backtracking search with:
          - MRV (Minimum Remaining Values): Choose variable with fewest legal values
          - Degree Heuristic: Tie-breaker with most constraints on unassigned variables
          - Forward Checking: Prune incompatible values from neighboring domains
          - LCV: Order values by least constraining first
        """
        self.nodes_expanded = 0
        self.time_limit = time_limit
        self.start_time = time.time()

        assignment: Dict[str, Tuple[int, int, str]] = {}
        # Deep copy initial domains so forward checking can prune without side effects
        current_domains = {v: list(vals) for v, vals in self.csp.domains.items()}

        success = self._backtrack_heuristic(
            assignment,
            current_domains,
            use_mrv,
            use_degree,
            use_forward_checking,
            use_lcv
        )
        elapsed = time.time() - self.start_time

        stats = {
            "algorithm": "Backtracking (with Heuristics)",
            "time_taken": round(elapsed, 4),
            "nodes_expanded": self.nodes_expanded,
            "success": success,
            "timed_out": elapsed >= self.time_limit
        }
        return (assignment if success else None), stats

    def _select_unassigned_variable(
        self,
        assignment: Dict[str, Tuple[int, int, str]],
        domains: Dict[str, List[Tuple[int, int, str]]],
        use_mrv: bool,
        use_degree: bool
    ) -> str:
        """
        Selects next variable using MRV with Degree Heuristic tie-breaking.
        """
        unassigned = [s.session_id for s in self.csp.sessions if s.session_id not in assignment]

        if not use_mrv:
            return unassigned[0]

        # 1. MRV: Find variables with minimum domain size
        min_domain_size = min(len(domains[var]) for var in unassigned)
        mrv_candidates = [var for var in unassigned if len(domains[var]) == min_domain_size]

        if len(mrv_candidates) == 1 or not use_degree:
            return mrv_candidates[0]

        # 2. Degree Heuristic: Choose candidate with highest degree among unassigned neighbors
        def get_degree(var):
            return sum(1 for neighbor in self.csp.neighbors[var] if neighbor not in assignment)

        mrv_candidates.sort(key=get_degree, reverse=True)
        return mrv_candidates[0]

    def _order_domain_values(
        self,
        var: str,
        assignment: Dict[str, Tuple[int, int, str]],
        domains: Dict[str, List[Tuple[int, int, str]]],
        use_lcv: bool
    ) -> List[Tuple[int, int, str]]:
        """
        Orders domain values. With LCV, sorts by least number of values eliminated
        from neighboring unassigned variables.
        """
        values = domains[var]
        if not use_lcv or len(values) <= 1:
            return values

        curr_session = next(s for s in self.csp.sessions if s.session_id == var)

        def count_conflicts_ruled_out(val):
            d, p, r = val
            ruled_out = 0
            for neighbor_id in self.csp.neighbors[var]:
                if neighbor_id not in assignment:
                    n_sess = next(s for s in self.csp.sessions if s.session_id == neighbor_id)
                    for n_val in domains[neighbor_id]:
                        nd, np, nr = n_val
                        if nd == d and np == p:
                            if n_sess.class_name == curr_session.class_name or \
                               n_sess.teacher_name == curr_session.teacher_name or \
                               nr == r:
                                ruled_out += 1
            return ruled_out

        # Return values sorted ascending by how many neighbor values they rule out
        return sorted(values, key=count_conflicts_ruled_out)

    def _backtrack_heuristic(
        self,
        assignment: Dict[str, Tuple[int, int, str]],
        domains: Dict[str, List[Tuple[int, int, str]]],
        use_mrv: bool,
        use_degree: bool,
        use_forward_checking: bool,
        use_lcv: bool
    ) -> bool:
        """Recursive helper for Heuristic Backtracking."""
        self.nodes_expanded += 1

        # Timeout guard
        if time.time() - self.start_time > self.time_limit:
            return False

        # Base case
        if len(assignment) == len(self.csp.sessions):
            return True

        # Choose next variable using MRV and Degree heuristics
        var = self._select_unassigned_variable(assignment, domains, use_mrv, use_degree)

        # Order domain values
        ordered_values = self._order_domain_values(var, assignment, domains, use_lcv)

        curr_session = next(s for s in self.csp.sessions if s.session_id == var)

        for val in ordered_values:
            if not self.csp.is_consistent(var, val, assignment):
                continue

            assignment[var] = val

            if use_forward_checking:
                # Forward Checking: prune incompatible values from unassigned variables
                day, period, room = val
                pruned: Dict[str, List[Tuple[int, int, str]]] = defaultdict(list)
                domain_empty = False

                for unassigned_sess in self.csp.sessions:
                    u_id = unassigned_sess.session_id
                    if u_id in assignment:
                        continue

                    # Check if unassigned variable could clash at the same (day, period)
                    shares_teacher = (unassigned_sess.teacher_name == curr_session.teacher_name)
                    shares_class = (unassigned_sess.class_name == curr_session.class_name)

                    if shares_teacher or shares_class:
                        # Cannot use this (day, period) at all
                        kept = []
                        for u_val in domains[u_id]:
                            if u_val[0] == day and u_val[1] == period:
                                pruned[u_id].append(u_val)
                            else:
                                kept.append(u_val)
                        domains[u_id] = kept
                        if len(domains[u_id]) == 0:
                            domain_empty = True
                            break
                    else:
                        # Different class and teacher, but cannot use the SAME room at (day, period)
                        kept = []
                        for u_val in domains[u_id]:
                            if u_val[0] == day and u_val[1] == period and u_val[2] == room:
                                pruned[u_id].append(u_val)
                            else:
                                kept.append(u_val)
                        domains[u_id] = kept
                        if len(domains[u_id]) == 0:
                            domain_empty = True
                            break

                # If no domain wiped out, recurse
                if not domain_empty:
                    if self._backtrack_heuristic(assignment, domains, use_mrv, use_degree, use_forward_checking, use_lcv):
                        return True

                # Restore pruned values (backtrack domain changes)
                for u_id, removed_vals in pruned.items():
                    domains[u_id].extend(removed_vals)

            else:
                # Without forward checking, simple recursion
                if self._backtrack_heuristic(assignment, domains, use_mrv, use_degree, False, use_lcv):
                    return True

            # Undo assignment
            del assignment[var]

        return False
