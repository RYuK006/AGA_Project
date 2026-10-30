"""Bellman-Ford Single-Source Shortest Path Algorithm.

Theoretical Complexity: O(V * E)
Handles arbitrary directed edge weights, including negative weights.
Executes (V - 1) full edge relaxation passes, followed by a V-th pass
to detect reachable negative-weight cycles.
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from .dijkstra import AlgorithmResult


def bellman_ford(
    graph,
    source: Any,
    target: Optional[Any] = None,
    max_events: int = 1500,
    record_events: bool = True
) -> AlgorithmResult:
    """Run Bellman-Ford algorithm from `source`.

    Parameters:
    - graph: Object with .get_nodes() and .get_edges() returning list of (u, v, weight)
    - source: start node ID
    - target: optional destination node ID
    - max_events: maximum number of step events to keep for visual replay
    - record_events: whether to log events for visual playback
    """
    start_time = time.perf_counter()

    nodes = list(graph.get_nodes())
    v_count = len(nodes)
    edges = list(graph.get_edges())
    e_count = len(edges)

    dist: Dict[Any, float] = {node: float("inf") for node in nodes}
    dist[source] = 0.0
    parent: Dict[Any, Optional[Any]] = {node: None for node in nodes}

    events: List[Dict[str, Any]] = []
    edges_relaxed = 0
    nodes_expanded = 0
    has_negative_cycle = False
    cycle_nodes: List[Any] = []

    if record_events and len(events) < max_events:
        events.append({
            "type": "init",
            "source": source,
            "target": target,
            "v_count": v_count,
            "e_count": e_count,
            "caption": f"Bellman-Ford Init: |V|={v_count}, |E|={e_count}. Set dist[{source}]=0, others=inf. Will run up to {v_count - 1} passes."
        })

    # V - 1 passes
    for pass_num in range(1, max(1, v_count)):
        any_update = False
        pass_relaxed = 0

        if record_events and len(events) < max_events:
            events.append({
                "type": "pass_start",
                "pass_num": pass_num,
                "caption": f"--- Starting Pass {pass_num} of {v_count - 1} ---"
            })

        for u, v, weight in edges:
            edges_relaxed += 1
            if dist[u] != float("inf"):
                new_dist = dist[u] + weight
                old_dist = dist[v]
                if new_dist < old_dist:
                    dist[v] = new_dist
                    parent[v] = u
                    any_update = True
                    pass_relaxed += 1
                    nodes_expanded += 1

                    if record_events and len(events) < max_events:
                        old_str = "inf" if old_dist == float("inf") else f"{old_dist:.1f}"
                        events.append({
                            "type": "relax",
                            "pass_num": pass_num,
                            "u": u,
                            "v": v,
                            "edge_w": weight,
                            "old_dist": old_dist,
                            "new_dist": new_dist,
                            "updated": True,
                            "caption": f"Pass {pass_num} relaxing ({u}->{v}, w={weight}): dist[{u}]({dist[u] - weight:.1f}) + {weight} = {new_dist:.1f} < {old_str}, updated."
                        })

        if record_events and len(events) < max_events:
            events.append({
                "type": "pass_end",
                "pass_num": pass_num,
                "updates": pass_relaxed,
                "caption": f"Pass {pass_num} complete. {pass_relaxed} edge relaxations performed."
            })

        # Early termination if no edges were updated in this pass
        if not any_update:
            if record_events and len(events) < max_events:
                events.append({
                    "type": "converged",
                    "pass_num": pass_num,
                    "caption": f"Early convergence achieved at pass {pass_num}: no edges changed. Graph is stable."
                })
            break

    # Pass V: Check for negative-weight cycles
    if record_events and len(events) < max_events:
        events.append({
            "type": "pass_start",
            "pass_num": v_count,
            "caption": f"--- Pass {v_count} (Verification Pass): Checking for negative-weight cycles ---"
        })

    for u, v, weight in edges:
        edges_relaxed += 1
        if dist[u] != float("inf") and dist[u] + weight < dist[v]:
            has_negative_cycle = True
            cycle_nodes.append(v)
            if record_events and len(events) < max_events:
                events.append({
                    "type": "negative_cycle_detected",
                    "u": u,
                    "v": v,
                    "edge_w": weight,
                    "caption": f"ALERT: Negative cycle detected! Edge ({u}->{v}, w={weight}) can still be relaxed after {v_count - 1} passes ({dist[u]:.1f} + {weight} < {dist[v]:.1f})."
                })
            break

    end_time = time.perf_counter()
    runtime_ms = (end_time - start_time) * 1000.0

    path = []
    cost = float("inf")
    if target is not None and not has_negative_cycle:
        if dist[target] != float("inf"):
            cost = dist[target]
            curr = target
            visited_check = set()
            while curr is not None and curr not in visited_check:
                visited_check.add(curr)
                path.append(curr)
                curr = parent.get(curr)
            path.reverse()
    elif target is not None and has_negative_cycle:
        cost = float("-inf")

    return AlgorithmResult(
        path=path,
        cost=cost,
        nodes_expanded=nodes_expanded,
        edges_relaxed=edges_relaxed,
        runtime_ms=runtime_ms,
        events=events,
        has_negative_cycle=has_negative_cycle,
        distances=dist,
        visited_order=list(dist.keys())
    )
