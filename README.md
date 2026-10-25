# 📅 AI-Based Timetable Scheduler

An intelligent, beginner-friendly college timetable scheduler built with Python and Streamlit. This project solves the academic scheduling problem by formulating it as a **Constraint Satisfaction Problem (CSP)** and implementing multiple classical and modern AI search algorithms.

> **Course:** Artificial Intelligence | **Target Audience:** B.Tech Second Year  
> **Total Marks:** 18 (+12 Bonus) = **30/30 Marks Target**  
> **Algorithms Implemented:** Plain Backtracking, Heuristic Backtracking (MRV + Degree + FC + LCV), Min-Conflicts Local Search, Simulated Annealing (+6 Bonus), and Hybrid CSP + SA (+6 Bonus).

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Installation
Ensure you have Python 3.10+ installed. Install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Web Application
Start the interactive Streamlit UI:
```bash
streamlit run app.py
```
This opens the web dashboard in your browser (`http://localhost:8501`).

### 3. Run Experimental Benchmarks (10 Runs)
Run the automated benchmark suite comparing all 5 algorithms on both Small and Large datasets:
```bash
python run_experiments.py
```
This automatically runs 10 iterations of randomized methods, logs statistics, and generates:
- `min_conflicts_convergence.png`
- `sa_convergence.png`
- `algorithm_comparison_chart.png`
- `benchmark_results.json`

### 4. View or Print the Project Report
Generate the publication-ready HTML report:
```bash
python generate_report.py
```
Open `report.html` in Chrome or Edge and press **Ctrl + P** $\rightarrow$ **Save as PDF**.

---

## 📁 Repository Structure

```text
├── app.py                      # Interactive Streamlit Web Application
├── run_experiments.py          # Benchmark runner (10 runs, tables & graphs)
├── generate_report.py          # Generates printable HTML/PDF project report
├── requirements.txt            # Python dependencies
├── PROJECT_REPORT.md           # 6-10 page submission-ready project report
├── README.md                   # Beginner guide & Viva preparation
│
├── core/
│   ├── __init__.py             # Core package initialization
│   ├── models.py               # Clean data models (Subject, Teacher, Room, Session, etc.)
│   ├── constraints.py          # Complete H1-H9 hard and S1-S5 soft constraint evaluators
│   ├── csp_problem.py          # CSP formulation, unary domain pruning & constraint graph
│   ├── backtracking.py         # Plain Backtracking & Heuristic Backtracking (MRV/Degree/FC)
│   ├── min_conflicts.py        # Min-Conflicts Local Search with random walk & restarts
│   ├── simulated_annealing.py  # Simulated Annealing (+6) & Hybrid CSP+SA (+6)
│   └── utils.py                # 2D Grid formatters, CSV and multi-sheet Excel exporters
│
├── data/
│   ├── small_dataset.json      # 3 classes, 6 teachers, 4 rooms, 5 days x 6 periods
│   ├── large_dataset.json      # 8 classes, 16 teachers, 10 rooms, 5 days x 7 periods
│   ├── small_classes.csv       # CSV equivalent files for class batches
│   ├── small_teachers.csv      # CSV equivalent files for faculty
│   ├── small_subjects.csv      # CSV equivalent files for subjects
│   └── small_rooms.csv         # CSV equivalent files for classrooms & labs
│
├── min_conflicts_convergence.png   # Cost vs. Iterations convergence plot
├── sa_convergence.png              # Simulated Annealing convergence plot
└── algorithm_comparison_chart.png  # Execution time comparison bar chart
```

---

## 🧠 Problem Formulation (How the AI Works)

### 1. Variables
Every single credit hour of a subject for a class is modeled as a **Session Variable**:
- Example: `Session(id="CS-A_CS101_s1", class="CS-A", subject="CS101", teacher="Dr. Sharma")`

### 2. Domains
The domain of a session is the set of all allowable `(day, period, room)` combinations.
**Unary Constraint Pruning:** To keep the search space small and fast, the code automatically prunes illegal values during domain creation:
- Lunch break periods are removed (satisfying H9).
- Rooms with insufficient capacity are removed (satisfying H4).
- Wrong room types (e.g. lab session in classroom) are removed (satisfying H5).
- Teacher unavailable slots are removed (satisfying H6).

### 3. Hard Constraints (Must NEVER be violated)
- **H1:** A teacher cannot teach two sessions at the same time.
- **H2:** A class cannot have two sessions at the same time.
- **H3:** A room cannot be used for two sessions at the same time.
- **H4:** Room capacity $\ge$ class strength.
- **H5:** Lab sessions in lab rooms; theory in classrooms.
- **H6:** Teacher only scheduled in available slots.
- **H7:** Every subject gets exactly its required weekly hours.
- **H8:** Teacher's load does not exceed their maximum weekly load.
- **H9:** Class has its lunch break with no scheduled sessions.

### 4. Soft Constraints (Optimization Preferences)
- **S1 (Minimize Class Gaps):** 5 points penalty per free period between classes.
- **S2 (Subject Spread):** 10 points penalty if a theory lecture is repeated on the same day.
- **S3 (Consecutive Labs):** 15 points penalty if a 2-hour lab is split across non-consecutive periods.
- **S4 (Teacher Preferences):** 4 points penalty if scheduled in avoided slots (e.g., period 1).
- **S5 (Teacher Fatigue):** 8 points penalty for $>2$ back-to-back lectures for a teacher.

### 5. Cost Function
$$\text{Cost} = 1000 \times (\text{Hard Violations}) + (\text{Soft Penalties})$$

---

## 🔬 Search Algorithms Explained Simply

### 1. Baseline Backtracking
- Standard Depth-First Search.
- Picks the next unassigned variable in order.
- Tries values one by one and checks if they clash with already scheduled sessions.
- Backtracks when a dead end is reached.

### 2. Heuristic Backtracking
Adds three powerful techniques:
- **MRV (Minimum Remaining Values):** Pick the variable with the fewest legal values left ("Fail-First principle").
- **Degree Heuristic:** Tie-breaker that picks the variable with the most conflicts on unassigned variables.
- **Forward Checking:** As soon as variable $X$ is assigned, delete conflicting values from neighboring variables' domains. If any domain becomes empty, backtrack immediately!
- **LCV (Least Constraining Value):** Try values that leave the most flexibility for other variables.

### 3. Min-Conflicts Local Search
- Starts with a complete schedule (possibly with collisions).
- In each step:
  1. Finds all variables currently involved in clashes.
  2. Picks one conflicted variable at random.
  3. Moves it to the domain value that minimizes conflicts (ties broken randomly).
  4. **Plateau Escaping:** 5% chance of a random walk, plus random restart if stuck.

### 4. Simulated Annealing (+6 Bonus Marks)
- Explores neighbor schedules using **Move** (relocate a session) and **Swap** (swap two sessions).
- Uses a cooling temperature $T$ that decreases geometrically: $T_{k+1} = 0.99 \times T_k$.
- Always accepts moves that improve the schedule ($\Delta \text{Cost} < 0$).
- Occasionally accepts worse moves ($\Delta \text{Cost} > 0$) with probability $e^{-\Delta \text{Cost} / T}$ to escape local minima!

### 5. Hybrid CSP + Simulated Annealing (+6 Bonus Marks)
- **Phase 1:** Backtracking CSP quickly finds a 100% valid schedule (0 hard violations).
- **Phase 2:** Simulated Annealing optimizes soft constraints (gaps, fatigue, spread) without creating any hard clashes.

---

## 📊 Experimental Results

Tested across 10 independent runs:

| Algorithm | Small Dataset Time | Large Dataset Time | Hard Violations | Soft Penalty Score |
| :--- | :---: | :---: | :---: | :---: |
| **Backtracking (Baseline)** | 0.0026 s | 0.0585 s | 0 | 253 (Small) / 837 (Large) |
| **Backtracking (Heuristics)** | 0.0394 s | 1.1515 s | 0 | 237 (Small) / 539 (Large) |
| **Min-Conflicts** | **0.0010 s** | **0.0050 s** | 0 | 145 (Small) / 471 (Large) |
| **Simulated Annealing (Bonus)** | 1.4567 s | 3.2578 s | 0 | **0.4 (Small) / 20.0 (Large)** |
| **Hybrid CSP + SA (Bonus)** | 0.7875 s | 2.8654 s | 0 | **11.0 (Small) / 51.9 (Large)** |

---

## 🎓 Viva Voce / Presentation Q&A Preparation

Here are answers to the top 10 questions professors ask during demonstrations:

#### Q1: Why formulate timetable generation as a CSP instead of using regular programming?
> **Answer:** Standard procedural programming requires deeply nested loops that struggle to handle overlapping constraints and scale exponentially. A CSP formulation cleanly separates the **problem definition** (variables, domains, constraints) from the **search algorithm**, allowing us to reuse powerful heuristics (like MRV and Forward Checking) that guarantee completeness and prune vast swathes of invalid states.

#### Q2: What is the difference between systematic search and local search?
> **Answer:** Systematic search (Backtracking) builds a solution incrementally (partial assignment), systematically exploring branches, and is **complete** (guaranteed to find a solution or prove none exists). Local search (Min-Conflicts, Simulated Annealing) starts with a **complete assignment** and iteratively modifies it to repair conflicts; it is typically much faster for large solvable instances but is generally incomplete.

#### Q3: Why is unary constraint filtering done upfront?
> **Answer:** If we included invalid rooms (e.g. theory in a lab or a 40-student class in a 20-seat room) in the domain, the search tree would have thousands of dead ends. Pruning unary constraints before search reduces the domain size by over 60%, drastically speeding up backtracking and Min-Conflicts.

#### Q4: How does MRV (Minimum Remaining Values) improve Backtracking?
> **Answer:** MRV implements the "Fail-First" principle. By selecting the variable with the smallest remaining domain, it either finds a viable branch immediately or detects an inevitable dead end with minimal branching, pruning doomed subtrees before they blow up.

#### Q5: How do you handle plateaus in Min-Conflicts?
> **Answer:** If the algorithm reaches a local minimum where every move has equal or higher conflicts, standard greedy search gets stuck. We implement two plateau-escaping techniques:
> 1. **Random Walk:** A 5% probability of picking a random legal value instead of the argmin.
> 2. **Random Restart:** If stuck for multiple iterations, re-initializing the assignment from a new starting state.

#### Q6: What neighborhood moves are used in Simulated Annealing?
> **Answer:** We defined two operators:
> 1. **Move Operator (70%):** Moves a single session to another legal (day, period, room) slot.
> 2. **Swap Operator (30%):** Swaps the time slots of two sessions.

#### Q7: Why is a Hybrid (Backtracking + SA) approach beneficial?
> **Answer:** Backtracking is mathematically optimal at eliminating hard clashes but halts at the very first feasible solution without optimizing timetable quality. Simulated Annealing is exceptional at smooth continuous cost reduction. The Hybrid method combines both: Backtracking provides feasibility, and SA refines soft constraints to give a comfortable schedule for students and faculty.

#### Q8: How does the Manual Schedule Editor detect conflicts in real time?
> **Answer:** When a user selects a session and a proposed new slot, the editor creates a temporary trial assignment in memory and passes it to the `ConstraintChecker`. It runs checks against $H1$–$H9$ and flags double-booked teachers, room clashes, lunch conflicts, or capacity issues within a fraction of a millisecond.

#### Q9: What is the purpose of the cost function multiplier ($1000 \times \text{Hard}$)?
> **Answer:** The multiplier creates a strict hierarchy: satisfying hard constraints is always prioritized over soft preferences. A schedule with even 1 hard clash ($\text{Cost} \ge 1000$) will always be considered worse than a valid schedule with dozens of soft penalties ($\text{Cost} < 1000$).

#### Q10: How can this system be exported for administrative use?
> **Answer:** The system exports master flat CSV files and multi-sheet Microsoft Excel (`.xlsx`) workbooks where each student cohort (e.g., CSE-A, CSE-B) receives its own formatted weekly grid sheet.
