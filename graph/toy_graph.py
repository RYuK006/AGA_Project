"""Toy Graph and Teaching Demonstrations for KTU Advanced Graph Algorithms.

Contains:
1. Ground-Truth Toy Graph (5 nodes: S, P, Q, I, H)
   Expected shortest path S -> H = 130s via S -> P -> I -> H.
2. Signal-Preemption Credit Graph (demonstrating Dijkstra failure vs Bellman-Ford success)
3. Negative-Weight Cycle Graph (demonstrating V-th pass cycle detection)
"""

from .graph_model import WeightedDirectedGraph


def get_toy_graph() -> WeightedDirectedGraph:
    """Construct the course-specified 5-node ground-truth toy graph.

    Nodes:
    - S: Ambulance Station
    - P: Junction P
    - Q: Junction Q
    - I: Incident Scene
    - H: Hospital

    Edges and weights (in seconds):
    - S -> P: 40
    - S -> Q: 55
    - P -> Q: 20
    - P -> I: 30
    - Q -> I: 25
    - I -> H: 60
    - H -> I: 65

    Ground truth: Shortest path S -> H = 130 s via S -> P -> I -> H.
    (Alternative S->Q->I->H is 55 + 25 + 60 = 140 s;
     S->P->Q->I->H is 40 + 20 + 25 + 60 = 145 s).
    """
    g = WeightedDirectedGraph(is_geographic=False, default_speed=1.0)
    g.v_max = 1.0

    # Node positions chosen for clear canvas rendering and admissible Euclidean distance:
    # d(u, v) <= w(u, v) ensures h(u, v) = d / v_max is 100% admissible.
    g.add_node("S", x=0.0, y=0.0, ui_x=120, ui_y=250, label="Station (S)", role="station")
    g.add_node("P", x=30.0, y=-5.0, ui_x=320, ui_y=140, label="Junction P", role="junction")
    g.add_node("Q", x=32.0, y=8.0, ui_x=320, ui_y=360, label="Junction Q", role="junction")
    g.add_node("I", x=55.0, y=0.0, ui_x=540, ui_y=250, label="Incident (I)", role="incident")
    g.add_node("H", x=105.0, y=0.0, ui_x=760, ui_y=250, label="Hospital (H)", role="hospital")

    # Add edges
    g.add_edge("S", "P", 40.0, length=40.0, speed=1.0)
    g.add_edge("S", "Q", 55.0, length=55.0, speed=1.0)
    g.add_edge("P", "Q", 20.0, length=20.0, speed=1.0)
    g.add_edge("P", "I", 30.0, length=30.0, speed=1.0)
    g.add_edge("Q", "I", 25.0, length=25.0, speed=1.0)
    g.add_edge("I", "H", 60.0, length=60.0, speed=1.0)
    g.add_edge("H", "I", 65.0, length=65.0, speed=1.0)

    return g


def get_negative_credit_graph() -> WeightedDirectedGraph:
    """Construct the Signal-Preemption Credit graph.

    Scenario:
    An intelligent traffic system (ITS) grants a negative-weight 'credit'
    (-4.0 seconds) for emergency vehicle green-wave signal preemption on edge B->A.

    Edges:
    - S -> A: 3.0 s
    - S -> B: 5.0 s
    - B -> A: -4.0 s (Signal preemption green-wave credit)
    - A -> H: 10.0 s
    - B -> H: 20.0 s

    Analysis:
    - Path S -> A -> H: Cost = 3 + 10 = 13.0 s
    - Path S -> B -> A -> H: Cost = 5 + (-4) + 10 = 11.0 s (True Optimum)

    Dijkstra Behavior:
    - Pops S (0), pushes A (3) and B (5).
    - Greedily pops A (3) and marks A visited, assuming distance 3 is finalized.
    - Relaxes A -> H to 13.
    - Pops B (5). Since A is already visited, B -> A is ignored.
    - Dijkstra terminates returning suboptimal path [S, A, H] with cost 13.0 s!

    Bellman-Ford Behavior:
    - Pass 1 relaxes S->A (3), S->B (5), A->H (13), B->H (25).
    - Pass 2 relaxes B->A: 5 + (-4) = 1.0 < 3.0! Then relaxes A->H: 1 + 10 = 11.0 < 13.0!
    - Correctly finds optimal path [S, B, A, H] with cost 11.0 s.
    """
    g = WeightedDirectedGraph(is_geographic=False, default_speed=1.0)
    g.v_max = 1.0

    g.add_node("S", x=0.0, y=0.0, ui_x=120, ui_y=250, label="Station (S)", role="station")
    g.add_node("A", x=40.0, y=-20.0, ui_x=360, ui_y=150, label="Standard Street A", role="junction")
    g.add_node("B", x=40.0, y=20.0, ui_x=360, ui_y=350, label="Preempted Ave B", role="junction")
    g.add_node("H", x=90.0, y=0.0, ui_x=680, ui_y=250, label="Hospital (H)", role="hospital")

    g.add_edge("S", "A", 3.0, length=3.0, speed=1.0)
    g.add_edge("S", "B", 5.0, length=5.0, speed=1.0)
    g.add_edge("B", "A", -4.0, length=4.0, speed=1.0, is_credit=True)
    g.add_edge("A", "H", 10.0, length=10.0, speed=1.0)
    g.add_edge("B", "H", 20.0, length=20.0, speed=1.0)

    return g


def get_negative_cycle_graph() -> WeightedDirectedGraph:
    """Construct a graph containing a negative-weight cycle.

    Scenario:
    Faulty sensor feedback creates an unbounded negative feedback loop.
    Cycle: X -> Y (4s) -> Z (4s) -> X (-10s).
    Cycle weight sum = 4 + 4 - 10 = -2s < 0.

    Bellman-Ford Pass V will detect that edge Z->X can still be relaxed,
    confirming an infinite negative cycle.
    """
    g = WeightedDirectedGraph(is_geographic=False, default_speed=1.0)
    g.v_max = 1.0

    g.add_node("S", x=0.0, y=0.0, ui_x=100, ui_y=250, label="Ambulance Depot (S)", role="station")
    g.add_node("X", x=30.0, y=-20.0, ui_x=320, ui_y=160, label="Loop Node X", role="cycle")
    g.add_node("Y", x=60.0, y=-20.0, ui_x=520, ui_y=160, label="Loop Node Y", role="cycle")
    g.add_node("Z", x=45.0, y=20.0, ui_x=420, ui_y=340, label="Loop Node Z", role="cycle")
    g.add_node("H", x=90.0, y=0.0, ui_x=720, ui_y=250, label="Hospital (H)", role="hospital")

    g.add_edge("S", "X", 10.0, length=10.0, speed=1.0)
    g.add_edge("X", "Y", 4.0, length=4.0, speed=1.0)
    g.add_edge("Y", "Z", 4.0, length=4.0, speed=1.0)
    g.add_edge("Z", "X", -10.0, length=10.0, speed=1.0, is_credit=True)
    g.add_edge("Y", "H", 15.0, length=15.0, speed=1.0)

    return g
