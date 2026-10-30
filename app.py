"""FastAPI Application for Emergency Ambulance Routing System.

KTU B.Tech S5 Course: Advanced Graph Algorithms.
Provides REST APIs for:
1. Tab 1: Learn - Step-by-step toy graph execution (Dijkstra, A*, Bellman-Ford)
2. Tab 2: City Dispatch - Reversed Dijkstra ambulance ranking + A* hospital scoring
3. Tab 3: Benchmark - N-query empirical comparison and cost-equality validation
4. Tab 4: Negative Weights - Dijkstra failure vs Bellman-Ford success, negative cycle detection
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from algorithms.dijkstra import dijkstra
from algorithms.astar import astar
from algorithms.bellman_ford import bellman_ford
from graph.toy_graph import get_toy_graph, get_negative_credit_graph, get_negative_cycle_graph
from graph.city_graph import get_city_graph
from dispatch.dispatch_engine import dispatch_emergency_call
from benchmark.runner import run_benchmark

app = FastAPI(
    title="Emergency Ambulance Routing System",
    description="Algorithmic Demonstration of Dijkstra, A*, and Bellman-Ford on Road Networks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory city graph instance
city_graph, city_source_info = get_city_graph(force_synthetic=False, seed=42)

# Mount frontend static directory
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def read_root():
    """Serve the single-page application frontend."""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Frontend index.html not yet built. Please access /docs for API documentation."}


# -------------------------------------------------------------
# TAB 1: LEARN (TOY GRAPH)
# -------------------------------------------------------------
@app.get("/api/toy-graph")
def get_toy_graph_data():
    """Return the 5-node ground-truth toy graph structure and layout coordinates."""
    toy = get_toy_graph()
    return {
        "nodes": toy.nodes,
        "edges": toy.get_edges(),
        "ground_truth": {
            "source": "S",
            "target": "H",
            "expected_path": ["S", "P", "I", "H"],
            "expected_cost": 130.0
        }
    }


class RunToyRequest(BaseModel):
    algorithm: str # "dijkstra", "astar", "bellman_ford"
    source: str = "S"
    target: str = "H"


@app.post("/api/run-toy")
def run_toy_algorithm(req: RunToyRequest):
    """Run specified algorithm on the toy graph and return step-by-step event log."""
    toy = get_toy_graph()
    algo = req.algorithm.lower()

    if algo == "dijkstra":
        res = dijkstra(toy, req.source, req.target, record_events=True, max_events=500)
    elif algo in ["astar", "a*"]:
        res = astar(toy, req.source, req.target, record_events=True, max_events=500)
    elif algo in ["bellman_ford", "bellman-ford"]:
        res = bellman_ford(toy, req.source, req.target, record_events=True, max_events=500)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm: {req.algorithm}")

    return {
        "algorithm": algo,
        "path": res.path,
        "cost": res.cost,
        "nodes_expanded": res.nodes_expanded,
        "edges_relaxed": res.edges_relaxed,
        "runtime_ms": res.runtime_ms,
        "events": res.events,
        "distances": res.distances,
        "has_negative_cycle": res.has_negative_cycle
    }


# -------------------------------------------------------------
# TAB 2: CITY DISPATCH
# -------------------------------------------------------------
@app.get("/api/city-graph")
def get_city_graph_data():
    """Return city road network metadata, hospitals, ambulances, and source type."""
    edges_preview = []
    # Deliver lightweight edge list for frontend Leaflet rendering
    for u, v, w in city_graph.get_edges()[:1500]:
        n_u = city_graph.nodes.get(u, {})
        n_v = city_graph.nodes.get(v, {})
        if n_u and n_v and "lat" in n_u and "lat" in n_v:
            edges_preview.append({
                "u": u,
                "v": v,
                "lat1": n_u["lat"],
                "lon1": n_u["lon"],
                "lat2": n_v["lat"],
                "lon2": n_v["lon"],
                "weight": w
            })

    return {
        "source_info": city_source_info,
        "total_nodes": len(city_graph.nodes),
        "total_edges": len(city_graph.get_edges()),
        "v_max_mps": city_graph.v_max,
        "hospitals": getattr(city_graph, "hospitals", []),
        "ambulances": getattr(city_graph, "ambulances", []),
        "sample_edges": edges_preview,
        "bounding_box": {
            "center_lat": 8.5000,
            "center_lon": 76.9500
        }
    }


class DispatchRequest(BaseModel):
    incident_lat: float
    incident_lon: float
    specialty: str = "trauma"
    lambda_param: float = 1.0


@app.post("/api/dispatch")
def dispatch_call(req: DispatchRequest):
    """Execute complete emergency dispatch decision pipeline."""
    try:
        result = dispatch_emergency_call(
            graph=city_graph,
            incident_lat_or_y=req.incident_lat,
            incident_lon_or_x=req.incident_lon,
            required_specialty=req.specialty,
            lambda_param=req.lambda_param,
            max_events_cap=800
        )

        # Helper to convert node ids to coordinates list for Leaflet polylines
        def path_to_coords(node_path):
            coords = []
            for nid in node_path:
                node = city_graph.nodes.get(nid)
                if node and "lat" in node and "lon" in node:
                    coords.append([node["lat"], node["lon"]])
            return coords

        # Helper to extract explored node coordinates in expansion order
        def explored_to_coords(order):
            pts = []
            for idx, nid in enumerate(order):
                node = city_graph.nodes.get(nid)
                if node and "lat" in node and "lon" in node:
                    pts.append({
                        "order": idx,
                        "node_id": nid,
                        "lat": node["lat"],
                        "lon": node["lon"]
                    })
            return pts

        return {
            "incident_node": result.incident_node,
            "incident_coords": [
                city_graph.nodes[result.incident_node]["lat"],
                city_graph.nodes[result.incident_node]["lon"]
            ],
            "ranked_ambulances": result.ranked_ambulances,
            "ranked_hospitals": [
                {
                    "hospital_id": h.hospital_id,
                    "name": h.name,
                    "node_id": h.node_id,
                    "travel_time_s": round(h.travel_time_s, 1),
                    "beds_free": h.beds_free,
                    "beds_total": h.beds_total,
                    "occupancy_pct": round(h.occupancy_ratio * 100.0, 1),
                    "specialties": h.specialties,
                    "specialty_match": h.specialty_match,
                    "unavailability_penalty": round(h.unavailability_penalty, 1),
                    "total_score": round(h.total_score, 1),
                    "path_coords": path_to_coords(h.path),
                    "astar_stats": h.astar_stats
                }
                for h in result.ranked_hospitals
            ],
            "selected_ambulance": result.selected_ambulance,
            "selected_hospital_id": result.selected_hospital.hospital_id if result.selected_hospital else None,
            "leg1_coords": path_to_coords(result.leg1_path),
            "leg1_time_s": round(result.leg1_time_s, 1),
            "leg2_coords": path_to_coords(result.leg2_path),
            "leg2_time_s": round(result.leg2_time_s, 1),
            "total_mission_time_s": round(result.total_mission_time_s, 1),
            "frontier_comparison": {
                "dijkstra": {
                    "nodes_expanded": result.dijkstra_forward_result.nodes_expanded,
                    "edges_relaxed": result.dijkstra_forward_result.edges_relaxed,
                    "runtime_ms": round(result.dijkstra_forward_result.runtime_ms, 2),
                    "cost": round(result.dijkstra_forward_result.cost, 1),
                    "explored_nodes": explored_to_coords(result.dijkstra_forward_result.visited_order)
                },
                "astar": {
                    "nodes_expanded": result.astar_forward_result.nodes_expanded,
                    "edges_relaxed": result.astar_forward_result.edges_relaxed,
                    "runtime_ms": round(result.astar_forward_result.runtime_ms, 2),
                    "cost": round(result.astar_forward_result.cost, 1),
                    "explored_nodes": explored_to_coords(result.astar_forward_result.visited_order)
                }
            },
            "scoring_assumption_note": result.scoring_assumption_note
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# TAB 3: BENCHMARK
# -------------------------------------------------------------
class BenchmarkRequest(BaseModel):
    num_queries: int = 300
    bellman_sample_size: int = 25
    seed: int = 42


@app.post("/api/benchmark")
def run_benchmark_endpoint(req: BenchmarkRequest):
    """Run statistical performance benchmark across Dijkstra, A*, and Bellman-Ford."""
    summary = run_benchmark(
        graph=city_graph,
        num_queries=min(req.num_queries, 600),
        bellman_sample_size=min(req.bellman_sample_size, 50),
        seed=req.seed
    )
    return summary


# -------------------------------------------------------------
# TAB 4: NEGATIVE WEIGHTS
# -------------------------------------------------------------
@app.get("/api/negative-graphs")
def get_negative_graphs_meta():
    """Return definitions and layouts for negative-credit and negative-cycle demonstration graphs."""
    credit_g = get_negative_credit_graph()
    cycle_g = get_negative_cycle_graph()

    return {
        "credit_graph": {
            "nodes": credit_g.nodes,
            "edges": credit_g.get_edges(),
            "source": "S",
            "target": "H",
            "assumption_note": (
                "Modelling Assumption: Edge B->A (-4.0s) represents an emergency vehicle "
                "signal-preemption green wave credit. This demonstrates why Dijkstra's greedy "
                "finalization produces a suboptimal route (13.0s) while Bellman-Ford finds the global optimum (11.0s)."
            )
        },
        "cycle_graph": {
            "nodes": cycle_g.nodes,
            "edges": cycle_g.get_edges(),
            "source": "S",
            "target": "H",
            "assumption_note": (
                "Modelling Assumption: Edge Z->X (-10.0s) creates a negative-weight cycle (sum = -2.0s). "
                "Bellman-Ford's V-th pass detects that distances continue decreasing indefinitely, flagging the error."
            )
        }
    }


class RunNegativeRequest(BaseModel):
    graph_type: str # "credit" or "cycle"
    algorithm: str  # "dijkstra" or "bellman_ford"


@app.post("/api/run-negative")
def run_negative_test(req: RunNegativeRequest):
    """Run Dijkstra or Bellman-Ford on the chosen negative-weight graph."""
    if req.graph_type == "credit":
        g = get_negative_credit_graph()
    elif req.graph_type == "cycle":
        g = get_negative_cycle_graph()
    else:
        raise HTTPException(status_code=400, detail="Invalid graph_type. Must be 'credit' or 'cycle'.")

    algo = req.algorithm.lower()
    if algo == "dijkstra":
        res = dijkstra(g, source="S", target="H", record_events=True, max_events=500)
    elif algo in ["bellman_ford", "bellman-ford"]:
        res = bellman_ford(g, source="S", target="H", record_events=True, max_events=500)
    else:
        raise HTTPException(status_code=400, detail="Algorithm must be 'dijkstra' or 'bellman_ford'.")

    return {
        "graph_type": req.graph_type,
        "algorithm": algo,
        "path": res.path,
        "cost": res.cost,
        "nodes_expanded": res.nodes_expanded,
        "edges_relaxed": res.edges_relaxed,
        "runtime_ms": res.runtime_ms,
        "events": res.events,
        "distances": res.distances,
        "has_negative_cycle": res.has_negative_cycle
    }
