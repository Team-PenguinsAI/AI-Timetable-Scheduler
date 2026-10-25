# AI-Based Timetable Scheduler
## B.Tech Second Year | Artificial Intelligence Course Project
**Total Marks: 18 (+12 Bonus) = 30 Marks Target**  
**Team Size:** 3 Students | **Submission:** Source Code Repository, Working Demo, Project Report

---

### Executive Summary
Scheduling academic timetables is an NP-complete combinatorial optimization problem. Every educational institution faces the challenge of scheduling classes, teachers, and rooms across multiple days and periods without collisions while satisfying institutional preferences.

This project implements, evaluates, and compares four major AI search techniques:
1. **Plain Backtracking CSP (Baseline)**
2. **Backtracking CSP with Heuristics (MRV, Degree Heuristic, Forward Checking, and LCV)**
3. **Min-Conflicts Local Search (with Random Walk & Restart Plateau Escaping)**
4. **Simulated Annealing (Bonus +6 Marks)**
5. **Hybrid CSP + Simulated Annealing (Bonus +6 Marks)**

The system is wrapped in an interactive **Streamlit Web Application** supporting real-time data input (JSON/CSV), 2D timetable views (by Class, Teacher, Room), direct export to CSV and Excel, and an interactive **Manual Editor with Instant Conflict Detection**.

---

## 1. Problem Formulation

The timetable scheduling problem is formulated as a formal **Constraint Satisfaction Problem (CSP)** defined by the triple $(X, D, C)$:

### 1.1 Variables ($X$)
Let $C$ be the set of student classes, $S_c$ be the set of subjects enrolled by class $c$, and $w_{c,s}$ be the weekly credit hours required for subject $s$.
Each individual weekly hour corresponds to a single session variable:
$$X = \{ V_{c, s, k} \mid c \in C, \, s \in S_c, \, k \in \{1, 2, \dots, w_{c,s}\} \}$$
Each session $V$ encapsulates:
- `class_name`: The cohort attending the session.
- `subject_code`: The course identifier.
- `session_index`: The lecture instance ($1, 2, \dots$).
- `is_lab`: Boolean indicating laboratory vs. classroom requirement.
- `teacher_name`: Assigned faculty instructor (determined upfront via eligible teacher workload balancing to maintain a compact, tractable domain).

### 1.2 Domains ($D$)
For each session variable $V_i$, the domain $D_i$ represents allowable combinations of time slots and locations:
$$D_i \subseteq \{ (d, p, r) \mid d \in \{0, \dots, \text{days}-1\}, \, p \in \{0, \dots, \text{periods}-1\}, \, r \in \text{Rooms} \}$$
To dramatically prune search space and eliminate thrashing, unary constraints are pre-filtered during domain construction:
1. **Lunch Break ($H9$):** $p \neq \text{class.lunch\_break\_period}$.
2. **Room Type Matching ($H5$):** If $V_i.\text{is\_lab}$, then $r.\text{type} = \text{"lab"}$; else $r.\text{type} = \text{"classroom"}$.
3. **Room Capacity ($H4$):** $r.\text{capacity} \ge \text{class.strength}$.
4. **Teacher Availability ($H6$):** $(d, p) \notin \text{teacher.unavailable\_slots}$.

### 1.3 Constraints ($C$)

#### Hard Constraints (Must NEVER be violated: Weight = 1000 each)
- **H1 (No Teacher Clashing):** A teacher cannot teach two sessions at the same $(d, p)$.
  $$\forall V_i, V_j, \quad (V_i.\text{teacher} = V_j.\text{teacher} \land (d_i, p_i) = (d_j, p_j)) \implies V_i = V_j$$
- **H2 (No Class Clashing):** A class cannot attend two sessions at the same $(d, p)$.
  $$\forall V_i, V_j, \quad (V_i.\text{class} = V_j.\text{class} \land (d_i, p_i) = (d_j, p_j)) \implies V_i = V_j$$
- **H3 (No Room Double-Booking):** A room cannot host two sessions at the same $(d, p)$.
  $$\forall V_i, V_j, \quad (r_i = r_j \land (d_i, p_i) = (d_j, p_j)) \implies V_i = V_j$$
- **H4 (Room Capacity):** $r.\text{capacity} \ge \text{class.strength}$ (enforced via domain filtering).
- **H5 (Room Type):** Labs in labs, lectures in classrooms (enforced via domain filtering).
- **H6 (Teacher Availability):** Sessions scheduled only when teacher is available.
- **H7 (Subject Hours Fulfillment):** Exactly required weekly hours scheduled for every enrolled course.
- **H8 (Teacher Load Limit):** Teacher total weekly sessions $\le \text{max\_weekly\_load}$.
- **H9 (Lunch Break Reservation):** No lecture scheduled during a class's designated lunch period.

#### Soft Constraints (Optimization Objectives: Handled via Penalties)
All 5 soft constraints from the specification are implemented:
1. **S1 (Minimize Class Gaps):** Idle periods between first and last lecture of the day are penalized.
   $$\text{Penalty}_{S1} = 5 \times \text{Number of gap periods}$$
2. **S2 (Spread Theory Lectures):** Avoid scheduling the same theory subject multiple times on the same day.
   $$\text{Penalty}_{S2} = 10 \times (\text{lectures on same day} - 1)$$
3. **S3 (Consecutive Lab Sessions):** 2-hour labs should occupy consecutive periods back-to-back.
   $$\text{Penalty}_{S3} = 15 \text{ points if lab periods are split}$$
4. **S4 (Teacher Preferences):** Respect teacher requests to avoid certain slots (e.g., period 1).
   $$\text{Penalty}_{S4} = 4 \times \text{violations}$$
5. **S5 (Teacher Fatigue Prevention):** Avoid more than 2 consecutive back-to-back lectures for a teacher.
   $$\text{Penalty}_{S5} = 8 \times (\text{consecutive periods} - 2)$$

---

## 2. Cost Function Definition

For local search and quality evaluation, the overall objective function balances hard feasibility and soft preferences:
$$\text{Cost}(\text{Timetable}) = 1000 \times \sum_{k=1}^{9} \text{Count}(H_k) + \sum_{m=1}^{5} \text{Penalty}(S_m)$$

A timetable is legally valid if and only if:
$$\text{Hard Violations} = 0 \iff \text{Cost} < 1000$$

---

## 3. Algorithm Descriptions and Design Choices

### 3.1 Algorithm 1: Backtracking Search (Baseline & Heuristics)
Backtracking is a systematic, depth-first search through the space of partial assignments.
- **Baseline Plain Backtracking:**
  - Evaluates variables in static order of declaration.
  - Tries domain values in static order.
  - Backtracks upon detecting a clash with any previously placed session.
- **Heuristic Backtracking (MRV + Degree + Forward Checking + LCV):**
  - **MRV (Minimum Remaining Values / "Fail-First"):** Selects the unassigned session with the fewest legal values in its domain. This prunes branches early.
  - **Degree Heuristic:** Used as a deterministic tie-breaker for MRV; picks the variable that shares constraints with the largest number of remaining unassigned variables.
  - **Forward Checking (FC):** When variable $X$ is assigned value $(d, p, r)$, incompatible triples are immediately pruned from all neighboring unassigned variables. If any domain is reduced to size zero, the algorithm backtracks immediately without diving down a doomed subtree.
  - **LCV (Least Constraining Value):** Orders domain values so that values eliminating the fewest options for remaining unassigned variables are attempted first.

### 3.2 Algorithm 2: Min-Conflicts Local Search
Min-Conflicts operates on a complete (possibly invalid) timetable assignment and iteratively repairs conflicts.
- **Initial Assignment:** A greedy assignment places each variable into the domain slot creating minimal initial collisions.
- **Conflicted Variable Selection:** In each iteration, variables involved in at least one conflict are identified, and one is picked **uniformly at random** to prevent cyclic loops.
- **Value Selection & Tie-Breaking:** All domain values for the chosen variable are evaluated, and the value minimizing conflicts is selected. Ties are broken randomly.
- **Plateau Escaping:**
  - **Random Walk ($p=0.05$):** With 5% probability, the algorithm picks a random valid domain value instead of the argmin.
  - **Random Restart:** If stuck in a local minimum for $>250$ iterations, the state is re-initialized.

### 3.3 Algorithm 3: Simulated Annealing (Bonus +6 Marks)
Simulated Annealing is a stochastic global optimization technique inspired by metallurgical annealing.
- **Neighborhood Moves:**
  1. *Move Operator (70%):* Relocate a session to another valid $(d, p, r)$ slot.
  2. *Swap Operator (30%):* Swap the assignments of two sessions.
- **Cooling Schedule:** Geometric cooling $T_{k+1} = \alpha \times T_k$ with $T_0 = 80.0$, $\alpha = 0.99$, and $T_{\min} = 0.1$.
- **Metropolis Criterion:** An uphill move with $\Delta E > 0$ is accepted with probability:
  $$P(\text{accept}) = \exp\left(-\frac{\Delta E}{T}\right)$$

### 3.4 Algorithm 4: Hybrid Approach (Bonus +6 Marks)
- **Phase 1 (Feasibility):** Runs Heuristic Backtracking CSP to obtain a guaranteed clash-free timetable with $\text{Hard Violations} = 0$.
- **Phase 2 (Optimization):** Feeds the valid schedule into Simulated Annealing, allowing only moves that maintain hard-constraint feasibility ($\text{Hard Violations} = 0$) while strictly reducing soft penalties (gaps, subject spread, teacher fatigue).

---

## 4. Experimental Results and Comparative Analysis

Experiments were conducted on both sample datasets over **10 independent runs** for randomized algorithms.

### 4.1 Small Dataset Benchmark (3 Classes, 6 Teachers, 4 Rooms, 5x6 Periods = 47 Sessions)

| Metric | Backtracking (baseline) | Backtracking (with heuristics) | Min-Conflicts | Simulated Annealing | Hybrid (CSP + SA) |
| --- | :---: | :---: | :---: | :---: | :---: |
| **Time taken (seconds)** | 0.0026 s | 0.0394 s | 0.0010 s | 1.4567 s | 0.7875 s |
| **Nodes expanded / iterations** | 48 | 48 | 1.1 | 6660 | 3672 |
| **Hard violations in final result** | 0 | 0 | 0 | 0 | 0 |
| **Soft penalty score** | 253 | 237 | 145 | **0.4** | **11** |
| **Success rate (out of 10 runs)** | 1/1 (100%) | 1/1 (100%) | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) |

### 4.2 Large Dataset Benchmark (8 Classes, 16 Teachers, 10 Rooms, 5x7 Periods = 124 Sessions)

| Metric | Backtracking (baseline) | Backtracking (with heuristics) | Min-Conflicts | Simulated Annealing | Hybrid (CSP + SA) |
| --- | :---: | :---: | :---: | :---: | :---: |
| **Time taken (seconds)** | 0.0585 s | 1.1515 s | 0.0050 s | 3.2578 s | 2.8654 s |
| **Nodes expanded / iterations** | 125 | 125 | 0.9 | 6660 | 3672 |
| **Hard violations in final result** | 0 | 0 | 0 | 0 | 0 |
| **Soft penalty score** | 837 | 539 | 471.5 | **20.0** | **51.9** |
| **Success rate (out of 10 runs)** | 1/1 (100%) | 1/1 (100%) | 10/10 (100%) | 10/10 (100%) | 10/10 (100%) |

---

### 4.3 Detailed Analytical Answers

#### 1. Which method was faster?
- **Min-Conflicts Local Search** was the fastest solver overall, reaching a clash-free schedule in **0.001 to 0.005 seconds**. Because unary constraints are filtered during domain initialization, Min-Conflicts repairs the few initial collisions in fewer than 2 iterations on average.
- Between the systematic search methods, **Baseline Backtracking** exhibited lower raw execution time on these solvable instances due to near-zero heuristic evaluation overhead, whereas **Heuristic Backtracking** did extra work updating domain lists on every step.

#### 2. Which gave better soft-constraint quality?
- **Simulated Annealing** and the **Hybrid CSP + SA** method achieved dramatically superior soft-constraint quality.
- While systematic Backtracking stops at the *first feasible leaf node* (leaving soft penalties at 237–837 points), Simulated Annealing drove the soft penalty down to **0.4 points** on the Small dataset and **20.0 points** on the Large dataset.
- The **Hybrid method** delivers the optimal combination: 100% mathematical guarantee of zero clashes plus high timetable quality (low gaps, spread lectures, and consecutive labs).

#### 3. What happens as the problem grows?
- In unconstrained systematic search, the worst-case branching complexity is $O(d^n)$, meaning runtime explodes exponentially if tight bottlenecks cause deep thrashing. MRV and Forward Checking keep the search focused, preventing runaway exponential blowup.
- In Min-Conflicts, runtime scales approximately linearly $O(n)$ with the number of variables in under-constrained problems, but can degrade if the constraint density approaches the phase transition threshold.
- Simulated Annealing scales predictably with the cooling schedule ($O(\text{iterations})$), maintaining consistent optimization performance regardless of dataset scale.

#### 4. When would you use each method?
- **Min-Conflicts:** Best for **fast real-time timetable generation** or interactive applications where an instant valid schedule is required in milliseconds.
- **Heuristic Backtracking (CSP):** Best when you need a **strict mathematical proof of satisfiability or unsatisfiability** (e.g., verifying whether an academic curriculum is mathematically solvable given room and teacher limits).
- **Hybrid CSP + Simulated Annealing:** Best for **production college deployment**, where institutional administrators care deeply about teacher satisfaction, student gap reduction, and consecutive lab sessions.

---

## 5. Application Implementation

The application is written in Python using **Streamlit**:
1. **Data Input & Solvability Validation:** Accepts preloaded Small/Large benchmarks, custom JSON uploads, and entity CSV uploads. Basic validation checks teacher qualifications and room slot adequacy.
2. **Algorithm Selector:** Dropdown enables instantaneous switching between Baseline, Heuristics, Min-Conflicts, Simulated Annealing, and Hybrid.
3. **Multi-Perspective Grid Views:** Color-coded 2D timetable matrices organized **By Class**, **By Teacher**, and **By Room**.
4. **Interactive Manual Editor & Live Conflict Detector:** Users can select any session and move it to a different slot. The backend immediately evaluates hard constraints $H1$–$H9$ and displays alert cards with exact conflict details.
5. **Master Exporter:** One-click download as flat CSV and formatted multi-sheet Excel workbooks (`.xlsx`).

---

## 6. Limitations and Future Work
- **Limitations:** Currently assumes fixed 1-period slots (with 2-period labs modeled as linked sessions). Real universities occasionally require 1.5-hour slots or multi-batch elective groupings.
- **Future Work:**
  1. Extend CSP formulation to support multi-track elective baskets.
  2. Implement Genetic Algorithms (GA) with crossover operators for multi-objective Pareto optimization.
  3. Integrate auto-sync with Google Calendar or Microsoft Outlook for faculty schedules.

---

## 7. Team Member Contributions

| Team Member | Assigned Responsibilities | Deliverables |
| :--- | :--- | :--- |
| **Member 1 (Lead AI / CSP)** | Problem modeling, CSP formulation, Backtracking (Baseline + MRV/Degree/FC/LCV), Dataset design. | `core/models.py`, `core/csp_problem.py`, `core/backtracking.py`, JSON/CSV datasets. |
| **Member 2 (Optimization & Local Search)** | Min-Conflicts, Simulated Annealing, Hybrid solver, Cost function, Benchmark runner. | `core/constraints.py`, `core/min_conflicts.py`, `core/simulated_annealing.py`, `run_experiments.py`. |
| **Member 3 (UI / App / Integration)** | Streamlit Web App, 2D Grid renderers, Manual Editor with live clash detector, CSV/Excel export, Project Report. | `app.py`, `core/utils.py`, `README.md`, `PROJECT_REPORT.md`. |

---

## 8. Presentation & Viva Script (8-10 Minutes)

1. **Minutes 0:00 - 1:30 | Introduction & Problem Formulation:**
   - Introduce variables (sessions), domains (slot-room triples), and unary pruning.
   - Explain hard constraints ($H1-H9$) vs. soft constraints ($S1-S5$).
2. **Minutes 1:30 - 4:00 | Algorithm Walkthrough:**
   - Explain why Plain Backtracking is slow under bottlenecks and how MRV + Forward Checking prunes search branches.
   - Contrast systematic search with Min-Conflicts local repair.
   - Present the Bonus algorithms: Simulated Annealing and Hybrid CSP+SA.
3. **Minutes 4:00 - 6:30 | Live Application Demo:**
   - Open Streamlit app. Load Small Dataset $\rightarrow$ Click "Generate".
   - Switch grid perspective: Class view $\rightarrow$ Teacher view $\rightarrow$ Room view.
   - Open "Manual Schedule Editor" $\rightarrow$ Intentionally create a conflict (move session to lunch break or double-book a teacher) $\rightarrow$ Show the instant red warning alert!
   - Export timetable to Excel (.xlsx) and show the generated spreadsheet.
4. **Minutes 6:30 - 8:30 | Experimental Results & Analytical Q&A:**
   - Present the comparison table and convergence graphs (`min_conflicts_convergence.png`, `sa_convergence.png`).
   - Answer the 4 analytical questions.
5. **Minutes 8:30 - 10:00 | Conclusion & Q&A:**
   - Summarize team member roles and handle professor questions.
