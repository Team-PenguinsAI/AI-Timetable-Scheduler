"""
simulated_annealing.py
----------------------
Implementation of:
  1. Simulated Annealing (Standalone Local Search) [+6 Bonus Marks]
  2. Hybrid CSP + Simulated Annealing [+6 Bonus Marks]
     (Backtracking finds a feasible schedule; SA refines soft constraint quality)

Neighborhood moves:
  - Single Move: Move a random session to a new valid (day, period, room) slot.
  - Swap Move: Swap the time slots of two sessions.
Cooling Schedule:
  - Geometric cooling: T = T * alpha
Acceptance Criterion:
  - Metropolis: exp(-delta_E / T)
"""

import time
import math
import random
from typing import Dict, List, Tuple, Optional, Any
from core.csp_problem import TimetableCSP
from core.constraints import ConstraintChecker
from core.backtracking import BacktrackingSolver


class SimulatedAnnealingSolver:
    """
    Simulated Annealing and Hybrid Solver for Timetable CSP.
    """

    def __init__(self, csp: TimetableCSP, checker: ConstraintChecker):
        self.csp = csp
        self.checker = checker

    def solve(
        self,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.992,
        min_temp: float = 0.1,
        max_iterations_per_temp: int = 10,
        time_limit: float = 30.0,
        initial_assignment: Optional[Dict[str, Tuple[int, int, str]]] = None,
        only_preserve_feasible: bool = False,
        seed: Optional[int] = None
    ) -> Tuple[Dict[str, Tuple[int, int, str]], Dict[str, Any]]:
        """
        Runs Simulated Annealing optimization.
        If initial_assignment is provided, starts from there (used in Hybrid mode).
        If only_preserve_feasible is True, rejects moves that create hard constraint clashes.
        """
        if seed is not None:
            random.seed(seed)

        start_time = time.time()

        # 1. Starting Assignment
        if initial_assignment is not None:
            current_assignment = initial_assignment.copy()
        else:
            current_assignment = self._generate_random_assignment()

        curr_eval = self.checker.evaluate(current_assignment)
        best_assignment = current_assignment.copy()
        best_eval = curr_eval

        T = initial_temp
        total_iterations = 0
        accepted_moves = 0
        cost_history: List[Tuple[int, int]] = []

        all_var_ids = [s.session_id for s in self.csp.sessions]

        while T > min_temp and (time.time() - start_time) < time_limit:
            for _ in range(max_iterations_per_temp):
                total_iterations += 1
                cost_history.append((total_iterations, curr_eval["total_cost"]))

                # 2. Neighborhood Move Selection
                # 70% chance of Move, 30% chance of Swap
                neighbor_assignment = current_assignment.copy()

                if random.random() < 0.7 or len(all_var_ids) < 2:
                    # Move operator: pick a variable and assign a new value from its domain
                    var_id = random.choice(all_var_ids)
                    domain = self.csp.domains[var_id]
                    if domain:
                        new_val = random.choice(domain)
                        neighbor_assignment[var_id] = new_val
                else:
                    # Swap operator: pick two variables and swap their (day, period, room)
                    var1, var2 = random.sample(all_var_ids, 2)
                    val1 = neighbor_assignment[var1]
                    val2 = neighbor_assignment[var2]
                    # Verify each value is valid in the other variable's unary domain
                    if val2 in self.csp.domains[var1] and val1 in self.csp.domains[var2]:
                        neighbor_assignment[var1] = val2
                        neighbor_assignment[var2] = val1

                neighbor_eval = self.checker.evaluate(neighbor_assignment)

                # In Hybrid mode, never accept a move that breaks a hard constraint!
                if only_preserve_feasible and neighbor_eval["hard_violations"] > 0:
                    continue

                # 3. Energy difference delta_E
                delta_cost = neighbor_eval["total_cost"] - curr_eval["total_cost"]

                # 4. Metropolis Acceptance Criterion
                accept = False
                if delta_cost <= 0:
                    accept = True
                else:
                    acceptance_prob = math.exp(-delta_cost / max(T, 1e-6))
                    if random.random() < acceptance_prob:
                        accept = True

                if accept:
                    current_assignment = neighbor_assignment
                    curr_eval = neighbor_eval
                    accepted_moves += 1

                    if curr_eval["total_cost"] < best_eval["total_cost"]:
                        best_assignment = current_assignment.copy()
                        best_eval = curr_eval

            # 5. Cooling Schedule
            T *= cooling_rate

        elapsed = time.time() - start_time
        success = (best_eval["hard_violations"] == 0)

        stats = {
            "algorithm": "Simulated Annealing",
            "time_taken": round(elapsed, 4),
            "iterations": total_iterations,
            "accepted_moves": accepted_moves,
            "final_temperature": round(T, 4),
            "hard_violations": best_eval["hard_violations"],
            "soft_penalty": best_eval["soft_penalty"],
            "total_cost": best_eval["total_cost"],
            "cost_history": cost_history,
            "success": success
        }
        return best_assignment, stats

    def solve_hybrid(
        self,
        time_limit: float = 30.0,
        seed: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, Tuple[int, int, str]]], Dict[str, Any]]:
        """
        Hybrid Approach:
          Phase 1: Run Heuristic Backtracking CSP to obtain a guaranteed feasible timetable.
          Phase 2: Run Simulated Annealing to optimize soft-constraint quality without violating hard constraints.
        """
        start_time = time.time()

        # Phase 1: Backtracking CSP for feasibility
        bt_solver = BacktrackingSolver(self.csp)
        feasible_assignment, bt_stats = bt_solver.solve_heuristic(
            use_mrv=True, use_degree=True, use_forward_checking=True, time_limit=time_limit / 2
        )

        if feasible_assignment is None:
            # If backtracking didn't find a solution within time limit
            return None, {
                "algorithm": "Hybrid (CSP + Simulated Annealing)",
                "time_taken": round(time.time() - start_time, 4),
                "phase1_success": False,
                "success": False,
                "message": "Phase 1 Backtracking failed to find a feasible timetable within time limit."
            }

        initial_eval = self.checker.evaluate(feasible_assignment)
        remaining_time = max(5.0, time_limit - (time.time() - start_time))

        # Phase 2: Simulated Annealing for soft constraint optimization
        optimized_assignment, sa_stats = self.solve(
            initial_temp=50.0,
            cooling_rate=0.99,
            min_temp=0.5,
            max_iterations_per_temp=8,
            time_limit=remaining_time,
            initial_assignment=feasible_assignment,
            only_preserve_feasible=True,
            seed=seed
        )

        final_eval = self.checker.evaluate(optimized_assignment)
        total_elapsed = time.time() - start_time

        stats = {
            "algorithm": "Hybrid (CSP + Simulated Annealing)",
            "time_taken": round(total_elapsed, 4),
            "phase1_time": bt_stats["time_taken"],
            "phase2_time": sa_stats["time_taken"],
            "iterations": sa_stats["iterations"],
            "nodes_expanded": bt_stats["nodes_expanded"],
            "initial_soft_penalty": initial_eval["soft_penalty"],
            "final_soft_penalty": final_eval["soft_penalty"],
            "soft_penalty_improvement": initial_eval["soft_penalty"] - final_eval["soft_penalty"],
            "hard_violations": final_eval["hard_violations"],
            "soft_penalty": final_eval["soft_penalty"],
            "total_cost": final_eval["total_cost"],
            "cost_history": sa_stats["cost_history"],
            "success": final_eval["hard_violations"] == 0
        }
        return optimized_assignment, stats

    def _generate_random_assignment(self) -> Dict[str, Tuple[int, int, str]]:
        """Generates a random assignment using valid unary domains."""
        assignment = {}
        for sess in self.csp.sessions:
            domain = self.csp.domains[sess.session_id]
            assignment[sess.session_id] = random.choice(domain) if domain else (0, 0, "Room-101")
        return assignment
