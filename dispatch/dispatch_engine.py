"""Emergency Ambulance Dispatch Engine.

Implements the multi-stage dispatch workflow:
1. Dijkstra on the REVERSED graph from the incident node to rank all ambulances
   in a single SSSP execution (O((V+E) log V) instead of K individual searches).
2. A* Search from incident to candidate hospitals using admissible straight-line heuristic.
3. Multi-criteria hospital ranking using configurable trade-off parameter lambda:
     score(h) = travel_time(h) + lambda * unavailability_penalty(h)
   where unavailability_penalty combines capacity congestion (1 - beds_free/beds_total)
   and specialty mismatch penalty.
   NOTE: This scoring formula is the project's own modeling assumption.
4. End-to-end composite route generation: Ambulance -> Incident -> Selected Hospital.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from algorithms.dijkstra import dijkstra, AlgorithmResult
from algorithms.astar import astar
from graph.graph_model import WeightedDirectedGraph


@dataclass
class HospitalScore:
    hospital_id: str
    name: str
    node_id: Any
    travel_time_s: float
    beds_free: int
    beds_total: int
    occupancy_ratio: float
    specialties: List[str]
    specialty_match: bool
    unavailability_penalty: float
    total_score: float
    path: List[Any]
    astar_stats: Dict[str, Any]


@dataclass
class DispatchResult:
    incident_node: Any
    ranked_ambulances: List[Dict[str, Any]]
    ranked_hospitals: List[HospitalScore]
    selected_ambulance: Dict[str, Any]
    selected_hospital: HospitalScore
    leg1_path: List[Any]
    leg1_time_s: float
    leg2_path: List[Any]
    leg2_time_s: float
    total_mission_time_s: float
    dijkstra_forward_result: AlgorithmResult
    astar_forward_result: AlgorithmResult
    scoring_assumption_note: str = (
        "Project Assumption: score(h) = travel_time(h) + lambda * unavailability_penalty(h). "
        "Allows dynamic multi-criteria balancing between geographic proximity and emergency room crowding."
    )


def dispatch_emergency_call(
    graph: WeightedDirectedGraph,
    incident_lat_or_y: float,
    incident_lon_or_x: float,
    required_specialty: str = "trauma",
    lambda_param: float = 1.0,
    max_events_cap: int = 1200
) -> DispatchResult:
    """Execute complete emergency dispatch decision pipeline.

    Parameters:
    - graph: WeightedDirectedGraph of the road network
    - incident_lat_or_y, incident_lon_or_x: incident coordinates
    - required_specialty: e.g. "trauma", "cardiac", "general"
    - lambda_param: weight given to hospital unavailability penalty
    - max_events_cap: cap for visual event log
    """
    # 0. Snap incident coordinates to nearest road network intersection
    incident_node = graph.snap_to_nearest(incident_lat_or_y, incident_lon_or_x)
    if incident_node is None:
        raise ValueError("Could not snap incident to any road intersection node.")

    # -------------------------------------------------------------
    # STAGE 1: Dijkstra on Reversed Graph to Rank Ambulances
    # -------------------------------------------------------------
    # In directed graph G, travel time from ambulance A -> incident I
    # is identical to distance from I -> A in the reversed graph G_rev.
    g_rev = graph.get_reversed_graph()

    # Single search from incident in reversed graph
    rev_dijkstra = dijkstra(g_rev, source=incident_node, target=None, record_events=False)

    ranked_ambulances = []
    ambulances_list = getattr(graph, "ambulances", [])

    for amb in ambulances_list:
        amb_node = amb["node_id"]
        travel_time = rev_dijkstra.distances.get(amb_node, float("inf"))

        if travel_time < float("inf"):
            # Compute exact forward route from this ambulance to incident
            # (using dijkstra with target=incident_node)
            fwd_res = dijkstra(graph, source=amb_node, target=incident_node, record_events=False)
            amb_path = fwd_res.path
        else:
            amb_path = []

        ranked_ambulances.append({
            "id": amb["id"],
            "name": amb["name"],
            "node_id": amb_node,
            "lat": amb.get("lat"),
            "lon": amb.get("lon"),
            "travel_time_s": travel_time,
            "path": amb_path
        })

    # Sort ambulances by travel time ascending
    ranked_ambulances.sort(key=lambda x: x["travel_time_s"])
    selected_ambulance = ranked_ambulances[0] if ranked_ambulances else None

    # -------------------------------------------------------------
    # STAGE 2: A* Search to Candidate Hospitals and Hospital Scoring
    # -------------------------------------------------------------
    hospitals_list = getattr(graph, "hospitals", [])
    ranked_hospitals: List[HospitalScore] = []

    for hosp in hospitals_list:
        hosp_node = hosp["node_id"]

        # Run A* from incident to hospital node
        astar_res = astar(graph, source=incident_node, target=hosp_node,
                          max_events=max_events_cap, record_events=True)

        travel_time = astar_res.cost
        beds_free = hosp.get("beds_free", 0)
        beds_total = max(1, hosp.get("beds_total", 1))
        occupancy = 1.0 - (beds_free / float(beds_total))

        # Check specialty match
        specs = hosp.get("specialties", [])
        has_specialty = (required_specialty in specs) or ("general" in specs and required_specialty == "general")
        specialty_penalty = 0.0 if has_specialty else 150.0  # equivalent to 2.5 min delay

        # Congestion penalty scaled to time units (e.g. 0 to 120 seconds penalty for 100% full hospital)
        capacity_penalty = occupancy * 120.0
        total_unavailability = capacity_penalty + specialty_penalty

        # Configurable scoring formula: score(h) = travel_time + lambda * unavailability_penalty
        total_score = travel_time + (lambda_param * total_unavailability)

        ranked_hospitals.append(HospitalScore(
            hospital_id=hosp["id"],
            name=hosp["name"],
            node_id=hosp_node,
            travel_time_s=travel_time,
            beds_free=beds_free,
            beds_total=beds_total,
            occupancy_ratio=occupancy,
            specialties=specs,
            specialty_match=has_specialty,
            unavailability_penalty=total_unavailability,
            total_score=total_score,
            path=astar_res.path,
            astar_stats={
                "nodes_expanded": astar_res.nodes_expanded,
                "edges_relaxed": astar_res.edges_relaxed,
                "runtime_ms": astar_res.runtime_ms,
                "visited_order": astar_res.visited_order[:300]
            }
        ))

    # Sort hospitals by total score ascending (lower is better)
    ranked_hospitals.sort(key=lambda x: x.total_score)
    selected_hospital = ranked_hospitals[0] if ranked_hospitals else None

    # -------------------------------------------------------------
    # STAGE 3: Comparative Forward Search (Dijkstra vs A*)
    # -------------------------------------------------------------
    # Run Dijkstra forward from incident to selected hospital to enable side-by-side search frontier comparison
    target_hosp_node = selected_hospital.node_id if selected_hospital else None

    dijkstra_fwd = dijkstra(
        graph,
        source=incident_node,
        target=target_hosp_node,
        max_events=max_events_cap,
        record_events=True
    )

    astar_fwd = astar(
        graph,
        source=incident_node,
        target=target_hosp_node,
        max_events=max_events_cap,
        record_events=True
    )

    # -------------------------------------------------------------
    # STAGE 4: Assemble Composite Mission Route
    # -------------------------------------------------------------
    leg1_path = selected_ambulance["path"] if selected_ambulance else []
    leg1_time = selected_ambulance["travel_time_s"] if selected_ambulance else 0.0

    leg2_path = selected_hospital.path if selected_hospital else []
    leg2_time = selected_hospital.travel_time_s if selected_hospital else 0.0

    total_mission_time = leg1_time + leg2_time

    return DispatchResult(
        incident_node=incident_node,
        ranked_ambulances=ranked_ambulances,
        ranked_hospitals=ranked_hospitals,
        selected_ambulance=selected_ambulance,
        selected_hospital=selected_hospital,
        leg1_path=leg1_path,
        leg1_time_s=leg1_time,
        leg2_path=leg2_path,
        leg2_time_s=leg2_time,
        total_mission_time_s=total_mission_time,
        dijkstra_forward_result=dijkstra_fwd,
        astar_forward_result=astar_fwd
    )
