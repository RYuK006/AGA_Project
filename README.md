# Emergency Ambulance Routing System
> **KTU B.Tech S5 Course Project • Advanced Graph Algorithms**  
> *A runnable, visual, and test-verified implementation of shortest-path algorithms on road networks.*

---

## Table of Contents
1. [Overview & Role](#overview--role)
2. [Project Architecture](#project-architecture)
3. [Quickstart & Run Instructions](#quickstart--run-instructions)
4. [Algorithm Implementations (Pure Python)](#algorithm-implementations-pure-python)
5. [Graph Model & Data Sources](#graph-model--data-sources)
6. [Emergency Dispatch Logic](#emergency-dispatch-logic)
7. [The Four Interactive Tabs](#the-four-interactive-tabs)
8. [Automated Test Suite (pytest)](#automated-test-suite-pytest)
9. [Empirical Benchmark Results](#empirical-benchmark-results)
10. [Honesty Rules & Project Assumptions](#honesty-rules--project-assumptions)
11. [Slide Deck & Pitch Script](#slide-deck--pitch-script)
12. [Academic References](#academic-references)

---

## 1. Overview & Role
This project was developed for an academic course evaluator in **Advanced Graph Algorithms (KTU B.Tech S5)** who grades *graph-algorithm comprehension*, not superficial UI polish. Every visualization, trace event, and benchmark metric directly exposes the inner state of:
- **Dijkstra's Algorithm** (Single-Source Shortest Path via binary min-heap)
- **A\* Search** (Goal-Directed Shortest Path via admissible straight-line spatial heuristic)
- **Bellman-Ford Algorithm** ((V-1) edge relaxation passes + Pass V negative cycle detection)

All routing algorithms are implemented **from scratch in pure Python standard libraries (`heapq`, `math`, `time`)**. No third-party shortest-path routing calls (such as NetworkX or OSMnx routing functions) are used.

---

## 2. Project Architecture
```text
AGA_Project/
├── app.py                      # FastAPI REST application serving API and frontend
├── run.py                      # Single-command launcher (python run.py)
├── requirements.txt            # Minimal dependency definitions
├── conftest.py                 # Pytest configuration (PYTHONPATH setup)
├── algorithms/                 # Pure Python graph routing algorithms
│   ├── __init__.py
│   ├── dijkstra.py             # O((V+E) log V) Dijkstra with event logging
│   ├── astar.py                # O((V+E) log V) A* with admissible heuristic
│   └── bellman_ford.py         # O(V*E) Bellman-Ford with V-1 passes + cycle check
├── graph/                      # Graph data structures and network loaders
│   ├── __init__.py
│   ├── graph_model.py          # WeightedDirectedGraph model with Tarjan SCC
│   ├── toy_graph.py            # 5-node ground truth, credit, and cycle graphs
│   └── city_graph.py           # OSM downloader, offline JSON cache, synthetic fallback
├── dispatch/                   # Emergency dispatch decision engine
│   ├── __init__.py
│   └── dispatch_engine.py      # Reversed Dijkstra ranking + hospital scoring formula
├── benchmark/                  # Statistical empirical benchmarking module
│   ├── __init__.py
│   └── runner.py               # N-query comparison and 100% cost equality verification
├── tests/                      # Automated test suite (all 6 criteria passing)
│   └── test_algorithms.py      # Pytest validation file
├── frontend/                   # Dark-on-light, high-contrast presenter UI
│   ├── index.html              # 4-tab interactive single-page application
│   ├── style.css               # Projector-grade, high-contrast academic stylesheet
│   └── app.js                  # Frontend controller (SVG replay, Leaflet, Chart.js)
├── slides/                     # Presentation artifacts
│   ├── capture_screenshots.py  # Playwright automated walkthrough and capture
│   ├── generate_slides.py      # python-pptx 10-slide generator with speaker notes
│   ├── benchmark_results.json  # Empirical benchmark metrics from 300 queries
│   └── screenshots/            # Real captured demo screenshots for slides
├── Emergency_Ambulance_Routing_KTU.pptx # 10-Slide PowerPoint presentation
├── pitch_script.md             # 5-minute spoken script, cue sheet, and 8 viva Q&As
└── README.md                   # This comprehensive manual
```

---

## 3. Quickstart & Run Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.11 and 3.14)
- Web Browser (Chrome, Firefox, Edge)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Launch Application
Run either:
```bash
python run.py
```
or:
```bash
uvicorn app:app --port 8000
```

### Step 3: Open in Browser
Open your browser and navigate to:
```text
http://127.0.0.1:8000
```

---

## 4. Algorithm Implementations (Pure Python)

### 1. Dijkstra's Algorithm (`algorithms/dijkstra.py`)
- **Complexity:** $O((V + E) \log V)$ using binary min-heap (`heapq`).
- **Core Invariant:** Greedy selection. At each step, extracts vertex $u$ with minimum tentative distance from heap. Because all edge weights $w(e) \ge 0$, $\text{dist}[u]$ is finalized upon extraction.
- **Instrumented Log:** Emits ordered event trace (`pop`, `relax`, `updated`) with heap snapshots for step-by-step UI replay.

### 2. A\* Search (`algorithms/astar.py`)
- **Complexity:** $O((V + E) \log V)$ worst case; prunes backward exploration.
- **Evaluation Function:** $f(n) = g(n) + h(n)$
  - $g(n)$: Exact travel time from origin to node $n$.
  - $h(n)$: Admissible straight-line road heuristic:
    $$h(n) = \frac{\text{straight\_line\_distance}(n, \text{goal})}{v_{\max}}$$
  - Since vehicle speed $v_e \le v_{\max}$ across all edges and straight-line distance $\le$ road length, $h(n) \le h^*(n)$ (guaranteed admissible).

### 3. Bellman-Ford Algorithm (`algorithms/bellman_ford.py`)
- **Complexity:** $O(V \cdot E)$
- **Pass Structure:** Executes $V - 1$ complete passes over all directed edges.
- **Cycle Detection:** Executes pass $V$. If any edge $(u, v)$ satisfies $\text{dist}[u] + w < \text{dist}[v]$, an unbounded negative cycle is confirmed and flagged.

---

## 5. Graph Model & Data Sources

### Mathematical Model
$$G = (V, E, w)$$
- **Directed Graph:** Road networks possess one-way restrictions and asymmetrical directional delays. Two-way streets are modeled as 2 distinct directed edges.
- **Weights in Seconds:** $w(u, v) = \frac{\text{length}(u, v)}{\text{speed}(u, v)}$ in seconds.
- **Vertex Snap:** Intersections, hospitals, ambulances, and incidents are snapped to road intersections. Hospital attributes (`beds_free`, `beds_total`, `specialties`) live on vertices, not edges.
- **Strong Connectivity:** Tarjan's SCC algorithm extracts and retains strictly the largest strongly connected component.

### Data Sources
1. **5-Node Ground-Truth Toy Graph:** Nodes S, P, Q, I, H. Edges: S&rarr;P 40s, S&rarr;Q 55s, P&rarr;Q 20s, P&rarr;I 30s, Q&rarr;I 25s, I&rarr;H 60s, H&rarr;I 65s. Shortest path: $S \to P \to I \to H$ (130s).
2. **City Graph (Thiruvananthapuram, Kerala, India):** Drivable OSM road network downloaded via Overpass API and cached to `data/city_graph_thiruvananthapuram.json` for instant offline operation.
3. **Offline Fallback:** Synthetic grid road network with ~15% edge drops, one-way streets, and 80 km/h arterial corridors.
4. **Synthetic Facilities:** 7 hospitals and 8 ambulances placed with fixed seed (`seed=42`).

---

## 6. Emergency Dispatch Logic

### Stage 1: Single-Search Ambulance Ranking via Reversed Dijkstra
To find the travel time from each ambulance $A_j$ to incident $I$ without running $K$ individual Dijkstra searches:
1. Compute the reversed graph $G_{\text{rev}}$ where each directed edge $(u, v, w)$ is flipped to $(v, u, w)$.
2. Run **a single Dijkstra search from incident $I$ on $G_{\text{rev}}$**.
3. Because $\delta_G(A_j, I) = \delta_{G_{\text{rev}}}(I, A_j)$, all ambulances are ranked in a single $O((V+E) \log V)$ search.

### Stage 2 & 3: A\* Hospital Querying & Multi-Criteria Scoring
Candidate hospitals are evaluated via:
$$\text{score}(h) = \text{travel\_time}(h) + \lambda \times \text{unavailability\_penalty}(h)$$
where:
$$\text{unavailability\_penalty}(h) = \left(1.0 - \frac{\text{beds\_free}}{\text{beds\_total}}\right) \times 120\text{s} + \text{specialty\_mismatch\_penalty}$$
$\lambda \in [0.0, 5.0]$ is an interactive UI slider:
- $\lambda = 0$: Pure geographic travel-time routing.
- $\lambda > 0$: Balances travel time against emergency room crowding.

---

## 7. The Four Interactive Tabs

1. **Tab 1: Learn (Toy Graph):** Interactive SVG node-link diagram. Step, Play, and Reset buttons. Live distance table, min-heap chips, and plain-English step captions.
2. **Tab 2: City Dispatch:** Interactive Leaflet map. Click to place incident. Real-time ambulance ranking, hospital scoring breakdown, composite route visualization, and animated side-by-side search frontier (Dijkstra circular vs A* directed cone).
3. **Tab 3: Benchmark:** N-query empirical evaluation (default 300 queries). Interactive Chart.js charts for nodes expanded and runtimes. Full cost-equality audit table with 100% checkmarks.
4. **Tab 4: Negative Weights:** Demonstrates why Dijkstra fails on negative credit edges (13s vs 11s) and demonstrates Bellman-Ford's $V$-th pass negative cycle detection.

---

## 8. Automated Test Suite (pytest)

Run all verification tests:
```bash
pytest -v
```

### Verified Test Output
```text
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Aaron\Desktop\AGA_Project
collected 6 items

tests/test_algorithms.py::test_1_toy_graph_ground_truth PASSED           [ 16%]
tests/test_algorithms.py::test_2_city_graph_500_queries_cost_equality PASSED [ 33%]
tests/test_algorithms.py::test_3_astar_heuristic_admissibility PASSED    [ 50%]
tests/test_algorithms.py::test_4_negative_credit_graph_dijkstra_fails_bellman_succeeds PASSED [ 66%]
tests/test_algorithms.py::test_5_negative_cycle_detection PASSED         [ 83%]
tests/test_algorithms.py::test_6_reversed_graph_dijkstra_equivalence PASSED [100%]

============================== 6 passed in 4.44s ==============================
```

---

## 9. Empirical Benchmark Results

Results collected from $N = 300$ randomized queries on the 238-node road network:

| Metric | Dijkstra (Heap SSSP) | A\* Search (f = g + h) | Bellman-Ford |
| :--- | :--- | :--- | :--- |
| **Path Cost Optimality** | 100.0% Exact Optimal | 100.0% Exact Optimal | 100.0% Exact Optimal |
| **Mean Nodes Expanded** | **120.1 nodes** | **59.9 nodes** (2.01x reduction) | All $V$ nodes per pass |
| **Median Nodes Expanded** | 115.5 nodes | 45.0 nodes | All $V$ nodes per pass |
| **Mean Runtime (ms)** | 1.83 ms | 3.58 ms | 17.76 ms (9.7x slowdown) |
| **Search Space Shape** | Radial circular expansion | Goal-directed cone | Full graph edge scans |

*Interpretation:* A* cuts node expansions by more than half (2.01x efficiency). On small road networks in pure Python, computing trigonometric Haversine distances in the heuristic at every step adds interpreter bytecode overhead, while Bellman-Ford suffers an expected 9.7x runtime slowdown due to its $O(V \cdot E)$ passes.

---

## 10. Honesty Rules & Project Assumptions
- **No False Claims:** We do not claim A* is faster on toy graphs. Speedups and trade-offs are reported solely from the 300-query empirical benchmark.
- **Synthetic Data Labeling:** All hospital bed capacities, specialties, ambulance fleet statuses, and signal-preemption credits are explicitly labeled in the UI as **synthetic simulation data**.
- **Model Assumptions:**
  1. Free-flow travel times (constant speed limits per road classification).
  2. GPS-to-intersection snapping error is assumed negligible.
  3. Hospital scoring formula is the project's own modeling assumption.
  4. Signal preemption credit is an ITS modeling scenario.

---

## 11. Slide Deck & Pitch Script
- **Presentation:** [`Emergency_Ambulance_Routing_KTU.pptx`](file:///C:/Users/Aaron/Desktop/AGA_Project/Emergency_Ambulance_Routing_KTU.pptx) (10 widescreen slides with embedded real screenshots, real empirical numbers, and speaker notes on every slide).
- **Pitch Script:** [`pitch_script.md`](file:///C:/Users/Aaron/Desktop/AGA_Project/pitch_script.md) (5-minute spoken presentation script, 20-second hook, demo walkthrough cue sheet, and 8-question examiner viva defense sheet).

---

## 12. Academic References
1. **Almalki, F. A., Aldhahri, E. A., & Aljojo, N.** (2025). *Ambulance routing optimization based on emergency medical service availability*. **Discover Artificial Intelligence**, 5(1), 1-18.
2. **Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C.** (2022). *Introduction to Algorithms* (4th ed.). MIT Press. (Chapter 22: Single-Source Shortest Paths).
3. **Hart, P. E., Nilsson, N. J., & Raphael, B.** (1968). *A formal basis for the heuristic determination of minimum cost paths*. IEEE Transactions on Systems Science and Cybernetics, 4(2), 100-107.
