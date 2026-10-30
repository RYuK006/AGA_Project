"""Dijkstra's Single-Source Shortest Path Algorithm.

Theoretical Complexity: O((V + E) log V) using a binary min-heap (heapq).
Constraint: Edge weights w(u, v) >= 0.

Returns AlgorithmResult with execution statistics and an ordered event log
for frontend step-by-step playback and search frontier animation.
"""

import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class AlgorithmResult:
    path: List[Any]
    cost: float
    nodes_expanded: int
    edges_relaxed: int
    runtime_ms: float
    events: List[Dict[str, Any]] = field(default_factory=list)
    has_negative_cycle: bool = False
    distances: Dict[Any, float] = field(default_factory=dict)
    visited_order: List[Any] = field(default_factory=list)


def dijkstra(
    graph,
    source: Any,
    target: Optional[Any] = None,
    max_events: int = 1500,
    record_events: bool = True
) -> AlgorithmResult:
    """Run Dijkstra's algorithm from `source`.

    If `target` is provided, stops immediately upon popping `target`.
    If `target` is None, computes shortest paths to all reachable nodes (full SSSP).

    Parameters:
    - graph: Object with .get_neighbors(node) returning list of (neighbor, weight)
    - source: start node ID
    - target: optional destination node ID
    - max_events: maximum number of step events to keep for visual replay
    - record_events: whether to log events for visual playback
    """
    start_time = time.perf_counter()

    # Distances map: node -> shortest distance from source
    dist: Dict[Any, float] = {source: 0.0}
    parent: Dict[Any, Optional[Any]] = {source: None}
    visited = set()

    # Min-heap stores tuples: (distance, tie_breaker_counter, node)
    counter = 0
    pq: List[Tuple[float, int, Any]] = [(0.0, counter, source)]

    events: List[Dict[str, Any]] = []
    visited_order: List[Any] = []
    nodes_expanded = 0
    edges_relaxed = 0

    if record_events and len(events) < max_events:
        events.append({
            "type": "init",
            "source": source,
            "target": target,
            "dist": 0.0,
            "caption": f"Initialize Dijkstra: set dist[{source}] = 0, push to priority queue."
        })

    while pq:
        d, _, u = heapq.heappop(pq)

        if u in visited:
            continue
        visited.add(u)
        visited_order.append(u)
        nodes_expanded += 1

        if record_events and len(events) < max_events:
            # Capture top-5 items in heap for pedagogical display
            heap_peek = [item[2] for item in sorted(pq)[:5]]
            events.append({
                "type": "pop",
                "node": u,
                "dist": d,
                "heap_peek": heap_peek,
                "caption": f"Popped node {u} with current minimum distance {d:.1f}s."
            })

        # Early termination if target reached
        if target is not None and u == target:
            if record_events and len(events) < max_events:
                events.append({
                    "type": "target_reached",
                    "node": u,
                    "dist": d,
                    "caption": f"Target {target} popped from queue. Optimal shortest path confirmed ({d:.1f}s)."
                })
            break

        # Relax outgoing edges
        for v, weight in graph.get_neighbors(u):
            edges_relaxed += 1
            old_dist = dist.get(v, float("inf"))
            new_dist = d + weight

            if new_dist < old_dist:
                dist[v] = new_dist
                parent[v] = u
                counter += 1
                heapq.heappush(pq, (new_dist, counter, v))

                if record_events and len(events) < max_events:
                    old_str = "inf" if old_dist == float("inf") else f"{old_dist:.1f}"
                    events.append({
                        "type": "relax",
                        "u": u,
                        "v": v,
                        "edge_w": weight,
                        "old_dist": old_dist,
                        "new_dist": new_dist,
                        "updated": True,
                        "caption": f"Relaxing edge {u}->{v}: {d:.1f} + {weight:.1f} = {new_dist:.1f} < {old_str}, updated."
                    })
            else:
                if record_events and len(events) < max_events:
                    events.append({
                        "type": "relax",
                        "u": u,
                        "v": v,
                        "edge_w": weight,
                        "old_dist": old_dist,
                        "new_dist": new_dist,
                        "updated": False,
                        "caption": f"Inspecting edge {u}->{v}: {d:.1f} + {weight:.1f} = {new_dist:.1f} >= {old_dist:.1f}, no update."
                    })

    end_time = time.perf_counter()
    runtime_ms = (end_time - start_time) * 1000.0

    # Reconstruct path if target requested
    path = []
    cost = float("inf")
    if target is not None:
        if target in dist:
            cost = dist[target]
            curr = target
            while curr is not None:
                path.append(curr)
                curr = parent.get(curr)
            path.reverse()
    else:
        # If no target specified, cost is 0.0 for source
        cost = 0.0

    return AlgorithmResult(
        path=path,
        cost=cost,
        nodes_expanded=nodes_expanded,
        edges_relaxed=edges_relaxed,
        runtime_ms=runtime_ms,
        events=events,
        has_negative_cycle=False,
        distances=dist,
        visited_order=visited_order
    )
