"""Pytest Suite for Advanced Graph Algorithms (KTU B.Tech S5 Course Specification).

Covers all 6 required verification criteria:
1. Ground-Truth Toy Graph: Dijkstra, A*, and Bellman-Ford return cost 130 and path ['S', 'P', 'I', 'H'].
2. Non-negative City Graph: 500 seeded queries verify identical optimal path costs between Dijkstra, A*, and Bellman-Ford (on subgraph).
3. A* Heuristic Admissibility: Verifies h(u, v) <= h*(u, v) across sampled node pairs.
4. Signal-Preemption Credit Graph: Dijkstra fails (greedy visited assumption violated), Bellman-Ford succeeds and matches brute-force optimum.
5. Negative-Weight Cycle Graph: Bellman-Ford Pass V correctly detects and flags negative cycle.
6. Reversed-Graph Dijkstra Equivalence: Verifies single reversed Dijkstra from incident matches individual forward Dijkstra searches from each ambulance.
"""

import random
import pytest
from algorithms.dijkstra import dijkstra
from algorithms.astar import astar
from algorithms.bellman_ford import bellman_ford
from graph.toy_graph import get_toy_graph, get_negative_credit_graph, get_negative_cycle_graph
from graph.city_graph import get_city_graph


def test_1_toy_graph_ground_truth():
    """Test 1: All three algorithms return cost 130 and path ['S', 'P', 'I', 'H']."""
    toy = get_toy_graph()

    d_res = dijkstra(toy, source="S", target="H")
    a_res = astar(toy, source="S", target="H")
    b_res = bellman_ford(toy, source="S", target="H")

    expected_path = ["S", "P", "I", "H"]
    expected_cost = 130.0

    assert d_res.cost == pytest.approx(expected_cost, abs=1e-4), f"Dijkstra cost {d_res.cost} != {expected_cost}"
    assert d_res.path == expected_path, f"Dijkstra path {d_res.path} != {expected_path}"

    assert a_res.cost == pytest.approx(expected_cost, abs=1e-4), f"A* cost {a_res.cost} != {expected_cost}"
    assert a_res.path == expected_path, f"A* path {a_res.path} != {expected_path}"

    assert b_res.cost == pytest.approx(expected_cost, abs=1e-4), f"Bellman-Ford cost {b_res.cost} != {expected_cost}"
    assert b_res.path == expected_path, f"Bellman-Ford path {b_res.path} != {expected_path}"
    assert not b_res.has_negative_cycle, "Toy graph should not have negative cycles"


def test_2_city_graph_500_queries_cost_equality():
    """Test 2: On non-negative city graph, 500 seeded queries verify identical costs.

    Bellman-Ford is verified on an induced subgraph / sample queries due to O(V*E) runtime.
    """
    city, _ = get_city_graph(force_synthetic=True, seed=42)
    nodes = list(city.get_nodes())
    rng = random.Random(42)

    # 500 seeded random query pairs
    pairs = [rng.sample(nodes, 2) for _ in range(500)]

    # Subgraph for Bellman-Ford O(V*E) testing (sample first 30 nodes for fast multi-query test)
    subgraph_nodes = set(nodes[:35])
    subgraph = city.get_subgraph(subgraph_nodes)
    subgraph_list = list(subgraph_nodes)

    for i, (s, t) in enumerate(pairs):
        d_res = dijkstra(city, s, t, record_events=False)
        a_res = astar(city, s, t, record_events=False)

        # Both Dijkstra and A* must find identical costs
        if d_res.cost == float("inf"):
            assert a_res.cost == float("inf")
        else:
            assert abs(d_res.cost - a_res.cost) < 1e-3, (
                f"Query {i} ({s}->{t}): Dijkstra cost {d_res.cost:.2f} != A* cost {a_res.cost:.2f}"
            )

    # Verify Bellman-Ford on subgraph pairs to validate cost equality
    for j in range(25):
        u, v = rng.sample(subgraph_list, 2)
        d_sub = dijkstra(subgraph, u, v, record_events=False)
        b_sub = bellman_ford(subgraph, u, v, record_events=False)
        if d_sub.cost == float("inf"):
            assert b_sub.cost == float("inf")
        else:
            assert abs(d_sub.cost - b_sub.cost) < 1e-3, (
                f"Subgraph query {j} ({u}->{v}): Dijkstra {d_sub.cost:.2f} != Bellman-Ford {b_sub.cost:.2f}"
            )


def test_3_astar_heuristic_admissibility():
    """Test 3: Heuristic admissibility h(u, goal) <= h*(u, goal) on sampled node pairs."""
    city, _ = get_city_graph(force_synthetic=True, seed=42)
    nodes = list(city.get_nodes())
    rng = random.Random(101)

    sampled_pairs = [rng.sample(nodes, 2) for _ in range(100)]

    for u, goal in sampled_pairs:
        h_val = city.heuristic(u, goal)
        d_res = dijkstra(city, u, goal, record_events=False)
        true_cost = d_res.cost

        if true_cost < float("inf"):
            # Admissibility condition: h(n) <= h*(n)
            # Add small floating-point tolerance (1e-5)
            assert h_val <= true_cost + 1e-5, (
                f"Inadmissible heuristic detected for pair ({u}, {goal}): "
                f"h={h_val:.3f} > true_cost={true_cost:.3f}"
            )


def test_4_negative_credit_graph_dijkstra_fails_bellman_succeeds():
    """Test 4: Signal-preemption credit graph where Dijkstra fails and Bellman-Ford succeeds."""
    credit_graph = get_negative_credit_graph()

    d_res = dijkstra(credit_graph, source="S", target="H")
    b_res = bellman_ford(credit_graph, source="S", target="H")

    # Brute force enumeration of simple paths in this 4-node DAG:
    # Path 1: S -> A -> H: 3.0 + 10.0 = 13.0
    # Path 2: S -> B -> H: 5.0 + 20.0 = 25.0
    # Path 3: S -> B -> A -> H: 5.0 + (-4.0) + 10.0 = 11.0 (True Optimum)
    brute_force_optimum = 11.0
    brute_force_optimal_path = ["S", "B", "A", "H"]

    assert b_res.cost == pytest.approx(brute_force_optimum, abs=1e-4), (
        f"Bellman-Ford cost {b_res.cost} does not match brute-force optimum {brute_force_optimum}"
    )
    assert b_res.path == brute_force_optimal_path, (
        f"Bellman-Ford path {b_res.path} does not match optimal path {brute_force_optimal_path}"
    )

    # Dijkstra greedily finalizes node A when popping it with dist 3.0,
    # missing the path through B with credit (-4.0), resulting in cost 13.0
    assert d_res.cost != b_res.cost, (
        f"Expected Dijkstra to fail on negative credit graph, but both returned {d_res.cost}"
    )
    assert d_res.cost == pytest.approx(13.0, abs=1e-4)
    assert d_res.path == ["S", "A", "H"]


def test_5_negative_cycle_detection():
    """Test 5: Bellman-Ford Pass V correctly detects and flags negative cycle."""
    cycle_graph = get_negative_cycle_graph()

    b_res = bellman_ford(cycle_graph, source="S", target="H")
    assert b_res.has_negative_cycle is True, "Bellman-Ford failed to detect negative-weight cycle"


def test_6_reversed_graph_dijkstra_equivalence():
    """Test 6: Reversed-graph Dijkstra from incident matches individual forward searches from ambulances."""
    city, _ = get_city_graph(force_synthetic=True, seed=42)
    incident_node = list(city.get_nodes())[0]

    # Reversed graph Dijkstra from incident
    g_rev = city.get_reversed_graph()
    rev_res = dijkstra(g_rev, source=incident_node, target=None, record_events=False)

    ambulances = getattr(city, "ambulances", [])
    assert len(ambulances) > 0, "Graph should have ambulances attached"

    for amb in ambulances:
        amb_node = amb["node_id"]
        rev_dist = rev_res.distances.get(amb_node, float("inf"))

        # Individual forward Dijkstra from this ambulance to incident
        fwd_res = dijkstra(city, source=amb_node, target=incident_node, record_events=False)
        fwd_dist = fwd_res.cost

        if fwd_dist < float("inf"):
            assert abs(rev_dist - fwd_dist) < 1e-4, (
                f"Discrepancy for ambulance {amb['id']} at node {amb_node}: "
                f"Reversed Dijkstra dist={rev_dist:.3f} != Forward Dijkstra dist={fwd_dist:.3f}"
            )
