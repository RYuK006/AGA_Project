"""A* Search Algorithm for Point-to-Point Shortest Travel Time.

Theoretical Complexity: O((V + E) log V) worst case using binary min-heap.
Evaluation Function: f(n) = g(n) + h(n)
where:
  - g(n) is the exact shortest travel time from source to n discovered so far.
  - h(n) is the admissible heuristic estimate from n to target.
    In road routing: h(n) = euclidean_distance(n, target) / v_max.
    Since speed <= v_max everywhere, travel_time >= distance / v_max,
    making h(n) <= h*(n) (guaranteed admissible).
"""

import heapq
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from .dijkstra import AlgorithmResult


def astar(
    graph,
    source: Any,
    target: Any,
    heuristic_func: Optional[Callable[[Any, Any], float]] = None,
    max_events: int = 1500,
    record_events: bool = True
) -> AlgorithmResult:
    """Run A* search from source to target.

    Parameters:
    - graph: Object with .get_neighbors(node) returning list of (neighbor, weight)
    - source: start node ID
    - target: destination node ID
    - heuristic_func: function (node, target) -> float estimate in seconds.
      If None, defaults to graph.heuristic(node, target) or 0.0.
    - max_events: maximum number of step events to keep for visual replay
    - record_events: whether to log events for visual playback
    """
    start_time = time.perf_counter()

    if heuristic_func is None:
        if hasattr(graph, "heuristic"):
            heuristic_func = graph.heuristic
        else:
            heuristic_func = lambda u, v: 0.0

    # g_score: exact travel time from source to node
    g_score: Dict[Any, float] = {source: 0.0}
    parent: Dict[Any, Optional[Any]] = {source: None}
    visited = set()

    h_init = heuristic_func(source, target)
    f_init = 0.0 + h_init

    # Heap contains tuples: (f_score, counter, node, g_score)
    counter = 0
    pq: List[Tuple[float, int, Any, float]] = [(f_init, counter, source, 0.0)]

    events: List[Dict[str, Any]] = []
    visited_order: List[Any] = []
    nodes_expanded = 0
    edges_relaxed = 0

    if record_events and len(events) < max_events:
        events.append({
            "type": "init",
            "source": source,
            "target": target,
            "g": 0.0,
            "h": h_init,
            "f": f_init,
            "caption": f"Initialize A*: g[{source}]=0, h[{source}]={h_init:.1f}s, f={f_init:.1f}s. Pushed to queue."
        })

    target_reached = False

    while pq:
        f, _, u, g = heapq.heappop(pq)

        if u in visited:
            continue
        visited.add(u)
        visited_order.append(u)
        nodes_expanded += 1

        h_val = heuristic_func(u, target)

        if record_events and len(events) < max_events:
            heap_peek = [item[2] for item in sorted(pq)[:5]]
            events.append({
                "type": "pop",
                "node": u,
                "g": g,
                "h": h_val,
                "f": f,
                "heap_peek": heap_peek,
                "caption": f"Popped node {u}: g={g:.1f}s, h={h_val:.1f}s -> priority f = g + h = {f:.1f}s."
            })

        if u == target:
            target_reached = True
            if record_events and len(events) < max_events:
                events.append({
                    "type": "target_reached",
                    "node": u,
                    "dist": g,
                    "caption": f"Target {target} reached with optimal cost {g:.1f}s! Search stops."
                })
            break

        for v, weight in graph.get_neighbors(u):
            edges_relaxed += 1
            if v in visited:
                continue
            tentative_g = g + weight
            old_g = g_score.get(v, float("inf"))

            if tentative_g < old_g:
                g_score[v] = tentative_g
                parent[v] = u
                h_v = heuristic_func(v, target)
                f_v = tentative_g + h_v
                counter += 1
                heapq.heappush(pq, (f_v, counter, v, tentative_g))

                if record_events and len(events) < max_events:
                    old_str = "inf" if old_g == float("inf") else f"{old_g:.1f}"
                    events.append({
                        "type": "relax",
                        "u": u,
                        "v": v,
                        "edge_w": weight,
                        "old_g": old_g,
                        "new_g": tentative_g,
                        "h_v": h_v,
                        "f_v": f_v,
                        "updated": True,
                        "caption": f"Relaxing edge {u}->{v}: new g={tentative_g:.1f}s < {old_str}s. New f={f_v:.1f}s."
                    })
            else:
                if record_events and len(events) < max_events:
                    events.append({
                        "type": "relax",
                        "u": u,
                        "v": v,
                        "edge_w": weight,
                        "old_g": old_g,
                        "new_g": tentative_g,
                        "h_v": heuristic_func(v, target),
                        "f_v": tentative_g + heuristic_func(v, target),
                        "updated": False,
                        "caption": f"Edge {u}->{v}: proposed g={tentative_g:.1f}s >= existing g={old_g:.1f}s. No update."
                    })

    end_time = time.perf_counter()
    runtime_ms = (end_time - start_time) * 1000.0

    path = []
    cost = float("inf")
    if target_reached:
        cost = g_score[target]
        curr = target
        while curr is not None:
            path.append(curr)
            curr = parent.get(curr)
        path.reverse()

    return AlgorithmResult(
        path=path,
        cost=cost,
        nodes_expanded=nodes_expanded,
        edges_relaxed=edges_relaxed,
        runtime_ms=runtime_ms,
        events=events,
        has_negative_cycle=False,
        distances=g_score,
        visited_order=visited_order
    )
