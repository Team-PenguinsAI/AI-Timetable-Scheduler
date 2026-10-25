"""
run_experiments.py
------------------
Automated experiment runner for the AI-Based Timetable Scheduler.
Fulfills all requirements of Section 6 (Experiments and Comparison):
  - Benchmarks Backtracking (Baseline), Backtracking (Heuristic), Min-Conflicts,
    Simulated Annealing, and Hybrid CSP+SA.
  - Runs randomized methods 10 times to report average metrics and success rate.
  - Tests on both Small and Large datasets.
  - Plots 'Cost vs. Iterations' for Min-Conflicts and Simulated Annealing.
  - Produces formatted comparison tables and analytical answers.
"""

import time
import json
import statistics
import matplotlib.pyplot as plt
from typing import Dict, List, Any

from core.models import ProblemData
from core.csp_problem import TimetableCSP
from core.constraints import ConstraintChecker
from core.backtracking import BacktrackingSolver
from core.min_conflicts import MinConflictsSolver
from core.simulated_annealing import SimulatedAnnealingSolver


def run_benchmark_for_dataset(dataset_path: str, dataset_name: str) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f"  RUNNING BENCHMARK ON {dataset_name.upper()} DATASET")
    print(f"=======================================================")

    problem_data = ProblemData.from_json_file(dataset_path)
    csp = TimetableCSP(problem_data)
    checker = ConstraintChecker(problem_data, csp.sessions)

    results: Dict[str, Any] = {}

    # 1. Backtracking (Baseline) - Deterministic (1 run)
    print("\n[1/5] Running Backtracking (Baseline)...")
    bt_solver = BacktrackingSolver(csp)
    assign_plain, stats_plain = bt_solver.solve_plain(time_limit=30.0)
    eval_plain = checker.evaluate(assign_plain) if assign_plain else {"hard_violations": -1, "soft_penalty": -1}
    
    results["Backtracking (Baseline)"] = {
        "time_taken": stats_plain["time_taken"],
        "nodes_expanded": stats_plain["nodes_expanded"],
        "hard_violations": eval_plain["hard_violations"],
        "soft_penalty": eval_plain["soft_penalty"],
        "success_rate": "1/1 (100%)" if stats_plain["success"] else "0/1 (0%)"
    }

    # 2. Backtracking (With Heuristics) - Deterministic (1 run)
    print("[2/5] Running Backtracking (with Heuristics: MRV + FC + Degree)...")
    assign_heur, stats_heur = bt_solver.solve_heuristic(time_limit=30.0)
    eval_heur = checker.evaluate(assign_heur) if assign_heur else {"hard_violations": -1, "soft_penalty": -1}

    results["Backtracking (with Heuristics)"] = {
        "time_taken": stats_heur["time_taken"],
        "nodes_expanded": stats_heur["nodes_expanded"],
        "hard_violations": eval_heur["hard_violations"],
        "soft_penalty": eval_heur["soft_penalty"],
        "success_rate": "1/1 (100%)" if stats_heur["success"] else "0/1 (0%)"
    }

    # 3. Min-Conflicts Local Search - Randomized (10 runs)
    print("[3/5] Running Min-Conflicts Local Search (10 runs)...")
    mc_times = []
    mc_iters = []
    mc_hards = []
    mc_softs = []
    mc_successes = 0
    mc_sample_history = []

    for seed in range(10):
        mc_solver = MinConflictsSolver(csp, checker)
        assign_mc, stats_mc = mc_solver.solve(max_iterations=1500, seed=100 + seed, time_limit=15.0)
        mc_times.append(stats_mc["time_taken"])
        mc_iters.append(stats_mc["iterations"])
        mc_hards.append(stats_mc["hard_violations"])
        mc_softs.append(stats_mc["soft_penalty"])
        if stats_mc["success"]:
            mc_successes += 1
        if seed == 0:
            mc_sample_history = stats_mc["cost_history"]

    results["Min-Conflicts"] = {
        "time_taken": round(statistics.mean(mc_times), 4),
        "nodes_expanded": round(statistics.mean(mc_iters), 1),
        "hard_violations": round(statistics.mean(mc_hards), 1),
        "soft_penalty": round(statistics.mean(mc_softs), 1),
        "success_rate": f"{mc_successes}/10 ({mc_successes * 10}%)",
        "sample_history": mc_sample_history
    }

    # 4. Simulated Annealing - Randomized (10 runs) [Bonus]
    print("[4/5] Running Simulated Annealing (10 runs)...")
    sa_times = []
    sa_iters = []
    sa_hards = []
    sa_softs = []
    sa_successes = 0
    sa_sample_history = []

    for seed in range(10):
        sa_solver = SimulatedAnnealingSolver(csp, checker)
        assign_sa, stats_sa = sa_solver.solve(
            initial_temp=80.0, cooling_rate=0.99, time_limit=10.0, seed=200 + seed
        )
        sa_times.append(stats_sa["time_taken"])
        sa_iters.append(stats_sa["iterations"])
        sa_hards.append(stats_sa["hard_violations"])
        sa_softs.append(stats_sa["soft_penalty"])
        if stats_sa["success"]:
            sa_successes += 1
        if seed == 0:
            sa_sample_history = stats_sa["cost_history"]

    results["Simulated Annealing (Bonus)"] = {
        "time_taken": round(statistics.mean(sa_times), 4),
        "nodes_expanded": round(statistics.mean(sa_iters), 1),
        "hard_violations": round(statistics.mean(sa_hards), 1),
        "soft_penalty": round(statistics.mean(sa_softs), 1),
        "success_rate": f"{sa_successes}/10 ({sa_successes * 10}%)",
        "sample_history": sa_sample_history
    }

    # 5. Hybrid (CSP + SA) - Randomized (10 runs) [Bonus]
    print("[5/5] Running Hybrid CSP + Simulated Annealing (10 runs)...")
    hy_times = []
    hy_iters = []
    hy_hards = []
    hy_softs = []
    hy_successes = 0

    for seed in range(10):
        sa_solver = SimulatedAnnealingSolver(csp, checker)
        assign_hy, stats_hy = sa_solver.solve_hybrid(time_limit=15.0, seed=300 + seed)
        if assign_hy:
            hy_times.append(stats_hy["time_taken"])
            hy_iters.append(stats_hy["iterations"])
            hy_hards.append(stats_hy["hard_violations"])
            hy_softs.append(stats_hy["soft_penalty"])
            if stats_hy["success"]:
                hy_successes += 1

    results["Hybrid (CSP + SA) (Bonus)"] = {
        "time_taken": round(statistics.mean(hy_times), 4) if hy_times else 0.0,
        "nodes_expanded": round(statistics.mean(hy_iters), 1) if hy_iters else 0.0,
        "hard_violations": round(statistics.mean(hy_hards), 1) if hy_hards else 0.0,
        "soft_penalty": round(statistics.mean(hy_softs), 1) if hy_softs else 0.0,
        "success_rate": f"{hy_successes}/10 ({hy_successes * 10}%)"
    }

    return results


def print_comparison_table(results: Dict[str, Any], dataset_name: str):
    """Prints GitHub markdown table for experimental comparison."""
    print(f"\n### Experimental Results: {dataset_name.title()} Dataset\n")
    headers = [
        "Metric",
        "Backtracking (baseline)",
        "Backtracking (with heuristics)",
        "Min-Conflicts",
        "Simulated Annealing",
        "Hybrid (CSP + SA)"
    ]
    
    rows = [
        ("Time taken (seconds)", "time_taken"),
        ("Nodes expanded / iterations", "nodes_expanded"),
        ("Hard violations in final result", "hard_violations"),
        ("Soft penalty score", "soft_penalty"),
        ("Success rate (out of 10 runs)", "success_rate")
    ]

    # Markdown table header
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")

    algos = [
        "Backtracking (Baseline)",
        "Backtracking (with Heuristics)",
        "Min-Conflicts",
        "Simulated Annealing (Bonus)",
        "Hybrid (CSP + SA) (Bonus)"
    ]

    for label, key in rows:
        row_str = f"| **{label}** | "
        cols = []
        for a in algos:
            val = results[a].get(key, "N/A")
            cols.append(str(val))
        row_str += " | ".join(cols) + " |"
        print(row_str)


def plot_graphs(small_results: Dict[str, Any], large_results: Dict[str, Any]):
    """Generates convergence and comparison plots required by the assignment."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Graph 1: Min-Conflicts Cost vs. Iterations
    mc_hist = small_results["Min-Conflicts"]["sample_history"]
    if mc_hist:
        plt.figure(figsize=(9, 5))
        iters = [x[0] for x in mc_hist]
        costs = [x[1] for x in mc_hist]
        plt.plot(iters, costs, color="#1f77b4", linewidth=2, label="Min-Conflicts Total Cost")
        plt.axhline(0, color="green", linestyle="--", alpha=0.7, label="Zero Hard Violations Goal")
        plt.title("Min-Conflicts Convergence: Cost vs. Iterations (Small Dataset)", fontsize=13, fontweight="bold")
        plt.xlabel("Iteration", fontsize=11)
        plt.ylabel("Cost = (1000 × Hard Violations) + Soft Penalties", fontsize=11)
        plt.legend()
        plt.tight_layout()
        plt.savefig("min_conflicts_convergence.png", dpi=300)
        plt.close()
        print("\nSaved plot: min_conflicts_convergence.png")

    # Graph 2: Simulated Annealing Convergence
    sa_hist = small_results["Simulated Annealing (Bonus)"]["sample_history"]
    if sa_hist:
        plt.figure(figsize=(9, 5))
        iters = [x[0] for x in sa_hist]
        costs = [x[1] for x in sa_hist]
        plt.plot(iters, costs, color="#e65100", linewidth=1.8, label="Simulated Annealing Cost")
        plt.title("Simulated Annealing Convergence: Cost vs. Iterations (Small Dataset)", fontsize=13, fontweight="bold")
        plt.xlabel("Iteration", fontsize=11)
        plt.ylabel("Total Cost", fontsize=11)
        plt.legend()
        plt.tight_layout()
        plt.savefig("sa_convergence.png", dpi=300)
        plt.close()
        print("Saved plot: sa_convergence.png")

    # Graph 3: Comparative Bar Chart
    plt.figure(figsize=(10, 5))
    algos = ["BT Baseline", "BT Heuristic", "Min-Conflicts", "Sim. Annealing", "Hybrid CSP+SA"]
    small_times = [
        small_results["Backtracking (Baseline)"]["time_taken"],
        small_results["Backtracking (with Heuristics)"]["time_taken"],
        small_results["Min-Conflicts"]["time_taken"],
        small_results["Simulated Annealing (Bonus)"]["time_taken"],
        small_results["Hybrid (CSP + SA) (Bonus)"]["time_taken"]
    ]
    large_times = [
        large_results["Backtracking (Baseline)"]["time_taken"],
        large_results["Backtracking (with Heuristics)"]["time_taken"],
        large_results["Min-Conflicts"]["time_taken"],
        large_results["Simulated Annealing (Bonus)"]["time_taken"],
        large_results["Hybrid (CSP + SA) (Bonus)"]["time_taken"]
    ]

    x = range(len(algos))
    width = 0.35
    plt.bar([i - width/2 for i in x], small_times, width, label="Small Dataset", color="#2ca02c")
    plt.bar([i + width/2 for i in x], large_times, width, label="Large Dataset", color="#d62728")

    plt.xlabel("Algorithm", fontsize=11, fontweight="bold")
    plt.ylabel("Execution Time (Seconds)", fontsize=11, fontweight="bold")
    plt.title("Execution Time Comparison: Small vs. Large Dataset", fontsize=13, fontweight="bold")
    plt.xticks(x, algos)
    plt.legend()
    plt.tight_layout()
    plt.savefig("algorithm_comparison_chart.png", dpi=300)
    plt.close()
    print("Saved plot: algorithm_comparison_chart.png")


def main():
    print("Starting automated experiments across Small and Large datasets...")
    small_res = run_benchmark_for_dataset("data/small_dataset.json", "Small")
    large_res = run_benchmark_for_dataset("data/large_dataset.json", "Large")

    print("\n" + "=" * 60)
    print("              FINAL BENCHMARK COMPARISONS")
    print("=" * 60)
    print_comparison_table(small_res, "Small")
    print_comparison_table(large_res, "Large")

    plot_graphs(small_res, large_res)

    # Save benchmark json for report generation
    summary_data = {
        "small_dataset": small_res,
        "large_dataset": large_res
    }
    with open("benchmark_results.json", "w") as f:
        # strip history arrays to keep JSON clean
        clean_summary = json.loads(json.dumps(summary_data, default=lambda o: []))
        json.dump(clean_summary, f, indent=2)
    print("\nSaved raw benchmark data: benchmark_results.json")
    print("All experimental runs completed successfully!")


if __name__ == "__main__":
    main()
