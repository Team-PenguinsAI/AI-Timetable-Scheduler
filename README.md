# AI-Based College Timetable Scheduler

An intelligent timetable generation system formulated as a Constraint Satisfaction Problem (CSP). This project evaluates and benchmarks systematic search (Backtracking with MRV, Degree Heuristic, and Forward Checking) against local search (Min-Conflicts) and stochastic metaheuristics (Simulated Annealing and a Hybrid CSP + Simulated Annealing pipeline).

---

## Contributors & Work Distribution

* **Samman Gupta** ([@sammangupta477](https://github.com/sammangupta477)) – CSP Problem Formulation, Constraint Checker (H1–H9, S1–S5), Systematic Backtracking with MRV & Forward Checking
* **Rahul Saini** ([@rahulsaini859790-design](https://github.com/rahulsaini859790-design)) – Min-Conflicts Local Search with Plateau Escapes, Simulated Annealing, Benchmarking Suite & Statistical Analysis
* **Vasudev Kumawat** ([@vasukumar7742-wq](https://github.com/vasukumar7742-wq)) – Interactive Streamlit Dashboard, Real-time Manual Conflict Detection System, Data Pipelines & Export Services

---

## Problem Formulation

* **Variables**: Each individual lecture or lab session: `(Class, Subject, SessionIndex)`.
* **Domains**: Valid `(Day, Period, Room)` combinations satisfying class strength and room type constraints.
* **Hard Constraints (H1–H9)**:
  1. **H1**: No teacher is scheduled for two sessions simultaneously.
  2. **H2**: No class has two sessions simultaneously.
  3. **H3**: No room is used for two sessions simultaneously.
  4. **H4**: Room capacity >= class strength.
  5. **H5**: Lab sessions in laboratory rooms; theory sessions in classrooms.
  6. **H6**: Sessions scheduled strictly within teacher available slots.
  7. **H7**: Exact weekly hours met for every subject.
  8. **H8**: Teacher hours do not exceed max weekly load limits.
  9. **H9**: Compulsory lunch breaks with zero session overlap.

* **Soft Constraints (S1–S5)**:
  * **S1**: Minimize free gaps in daily student schedules.
  * **S2**: Spread theory lectures across distinct days.
  * **S3**: Maintain consecutive periods for multi-hour lab sessions.
  * **S4**: Respect teacher preferred/avoided periods.
  * **S5**: Avoid more than two consecutive lectures for instructors.

* **Cost Function**:
  $$\text{Cost} = 1000 \times (\text{Hard Violations}) + \sum \text{Soft Penalties}$$

---

## Algorithms Implemented

1. **Baseline Backtracking**: Plain Depth-First Search over CSP variables.
2. **Heuristic Backtracking**: Depth-First Search enhanced with **MRV** (Minimum Remaining Values), **Degree Heuristic** for tie-breaking, and **Forward Checking** domain filtering.
3. **Min-Conflicts Local Search**: Iterative improvement algorithm with random-walk escaping to resolve plateaus and local optima.
4. **Simulated Annealing**: Stochastic search using state neighborhoods, exponential cooling schedule, and Boltzmann acceptance criteria.
5. **Hybrid CSP + Simulated Annealing**: Backtracking solver to establish zero hard violations, followed by Simulated Annealing to optimize soft penalties.

---

## Setup & Execution

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Team-PenguinsAI/AI-Timetable-Scheduler.git](https://github.com/Team-PenguinsAI/AI-Timetable-Scheduler.git)
   cd AI-Timetable-Scheduler