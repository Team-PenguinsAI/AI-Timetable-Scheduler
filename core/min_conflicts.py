"""
min_conflicts.py
----------------
Implementation of Min-Conflicts Local Search algorithm for Timetable CSP.
Includes:
  - Greedy / Smart initial assignment
  - Random selection among conflicted variables
  - Random tie-breaking among minimum conflict values
  - Plateau escaping (Random walk with p=0.05 and Random restart)
  - Cost tracking per iteration for convergence graphing
"""

import time
import random
from typing import Dict, List, Tuple, Optional, Any
from core.csp_problem import TimetableCSP
from core.constraints import ConstraintChecker


class MinConflictsSolver:
    """
    Min-Conflicts Local Search solver.
    Operates on a complete state, iteratively moving a conflicted variable
    to a domain value that minimizes conflicts.
    """

    def __init__(self, csp: TimetableCSP, checker: ConstraintChecker):
        self.csp = csp
        self.checker = checker

    def solve(
        self,
        max_iterations: int = 2000,
        random_walk_prob: float = 0.05,
        max_restarts: int = 3,
        time_limit: float = 30.0,
        seed: Optional[int] = None
    ) -> Tuple[Dict[str, Tuple[int, int, str]], Dict[str, Any]]:
        """
        Executes Min-Conflicts local search with plateau escaping.
        Returns:
          (best_assignment, stats_dictionary)
        """
        if seed is not None:
            random.seed(seed)

        start_time = time.time()
        best_assignment: Dict[str, Tuple[int, int, str]] = {}
        best_eval = {"hard_violations": float("inf"), "total_cost": float("inf")}
        cost_history: List[Tuple[int, int]] = []  # [(iteration, total_cost)]
        total_iterations = 0

        for restart in range(max_restarts):
            if time.time() - start_time > time_limit:
                break

            # 1. Generate Complete Initial Assignment
            # Justification: We use a greedy initial assignment where each variable
            # picks the domain value that causes the fewest conflicts with already placed variables.
            assignment = self._generate_initial_assignment()
            curr_eval = self.checker.evaluate(assignment)

            if curr_eval["total_cost"] < best_eval["total_cost"]:
                best_eval = curr_eval
                best_assignment = assignment.copy()

            if curr_eval["hard_violations"] == 0:
                # Immediately found valid schedule
                elapsed = time.time() - start_time
                return best_assignment, {
                    "algorithm": "Min-Conflicts Local Search",
                    "time_taken": round(elapsed, 4),
                    "iterations": total_iterations,
                    "restarts": restart,
                    "hard_violations": 0,
                    "soft_penalty": curr_eval["soft_penalty"],
                    "total_cost": curr_eval["total_cost"],
                    "cost_history": cost_history,
                    "success": True
                }

            # Local search loop
            for it in range(max_iterations):
                total_iterations += 1
                if time.time() - start_time > time_limit:
                    break

                # Record cost history for convergence graph
                cost_history.append((total_iterations, curr_eval["total_cost"]))

                # Check if current assignment is clash-free
                if curr_eval["hard_violations"] == 0:
                    best_assignment = assignment.copy()
                    best_eval = curr_eval
                    break

                # 2. Identify all conflicted variables
                conflicted_vars = []
                for sess in self.csp.sessions:
                    var_id = sess.session_id
                    conflicts = self.checker.count_conflicts_for_variable(
                        var_id, assignment[var_id], assignment
                    )
                    if conflicts > 0:
                        conflicted_vars.append(var_id)

                if not conflicted_vars:
                    # No conflicted variables left!
                    break

                # 3. Pick a conflicted variable uniformly at random
                # Justification: Random choice prevents cycling through the same variables
                var_to_move = random.choice(conflicted_vars)
                var_domain = self.csp.domains[var_to_move]

                # 4. Plateau Escaping: Random Walk with probability p
                # Justification: Occasional random moves prevent algorithm from getting stuck in local minima
                if random.random() < random_walk_prob:
                    chosen_val = random.choice(var_domain)
                else:
                    # 5. Greedy Min-Conflict value selection with Random Tie-Breaking
                    val_conflicts = []
                    for val in var_domain:
                        c = self.checker.count_conflicts_for_variable(var_to_move, val, assignment)
                        val_conflicts.append((c, val))

                    min_c = min(c for c, _ in val_conflicts)
                    best_values = [val for c, val in val_conflicts if c == min_c]
                    # Tie-breaking: choose uniformly at random among tied minimums
                    chosen_val = random.choice(best_values)

                # Move variable to chosen value
                assignment[var_to_move] = chosen_val
                curr_eval = self.checker.evaluate(assignment)

                if curr_eval["total_cost"] < best_eval["total_cost"]:
                    best_eval = curr_eval
                    best_assignment = assignment.copy()

            if best_eval["hard_violations"] == 0:
                break

        elapsed = time.time() - start_time
        success = (best_eval["hard_violations"] == 0)

        stats = {
            "algorithm": "Min-Conflicts Local Search",
            "time_taken": round(elapsed, 4),
            "iterations": total_iterations,
            "restarts": restart,
            "hard_violations": best_eval["hard_violations"],
            "soft_penalty": best_eval["soft_penalty"],
            "total_cost": best_eval["total_cost"],
            "cost_history": cost_history,
            "success": success
        }
        return best_assignment, stats

    def _generate_initial_assignment(self) -> Dict[str, Tuple[int, int, str]]:
        """
        Generates a greedy initial assignment to start the local search.
        For each variable, evaluates a random subset of domain values and picks the one
        with the fewest current conflicts.
        """
        assignment: Dict[str, Tuple[int, int, str]] = {}
        for sess in self.csp.sessions:
            var_id = sess.session_id
            domain = self.csp.domains[var_id]
            # Sample up to 10 random values to keep initialization super fast
            sample_size = min(len(domain), 10)
            candidate_vals = random.sample(domain, sample_size) if sample_size > 0 else domain

            best_val = candidate_vals[0]
            best_conflicts = float("inf")

            for val in candidate_vals:
                c = self.checker.count_conflicts_for_variable(var_id, val, assignment)
                if c < best_conflicts:
                    best_conflicts = c
                    best_val = val
                    if c == 0:
                        break

            assignment[var_id] = best_val

        return assignment
