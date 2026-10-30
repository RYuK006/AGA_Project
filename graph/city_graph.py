"""City Graph Loader and Generator.

Supports:
1. Live OpenStreetMap (OSM) download via Overpass API for Thiruvananthapuram, Kerala, India.
2. Offline JSON cache (`data/city_graph_thiruvananthapuram.json`) for instant startup.
3. Offline Synthetic Grid Fallback (120x120 or customizable grid with one-way streets,
   corridors, ~15% edge removals, and largest SCC extraction).
4. Reproducible seeded placement of hospitals and ambulances with capacity and specialties.
"""

import os
import json
import random
import math
import logging
from typing import Dict, Any, List, Optional
import requests

from .graph_model import WeightedDirectedGraph

logger = logging.getLogger("city_graph")

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CACHE_FILE = os.path.join(CACHE_DIR, "city_graph_thiruvananthapuram.json")


# Standard speed limits in m/s (default speed profiles)
SPEED_PROFILES = {
    "motorway": 22.2,     # 80 km/h
    "trunk": 19.4,        # 70 km/h
    "primary": 16.7,      # 60 km/h
    "secondary": 13.9,    # 50 km/h
    "tertiary": 11.1,     # 40 km/h
    "residential": 8.3,   # 30 km/h
    "unclassified": 8.3,  # 30 km/h
    "living_street": 5.5, # 20 km/h
    "default": 11.1       # 40 km/h
}


def haversine_dist(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def generate_synthetic_city(grid_size: int = 15, seed: int = 42) -> WeightedDirectedGraph:
    """Generate a synthetic drivable city road network on a grid.

    Includes:
    - Base grid of intersections (lat/lon centered near Thiruvananthapuram 8.50, 76.95)
    - Fast 'arterial highway' corridors (22.2 m/s)
    - One-way streets (single directed edge) and two-way roads (two edges)
    - ~15% random edge removal to model cul-de-sacs, rivers, and realistic topology
    - Retains only the largest Strongly Connected Component (SCC).
    """
    print("[INFO] Generating synthetic city grid road network (Offline Fallback)...")
    rng = random.Random(seed)

    g = WeightedDirectedGraph(is_geographic=True, default_speed=11.1)

    # Center around Thiruvananthapuram coords (8.50 lat, 76.95 lon)
    base_lat = 8.5000
    base_lon = 76.9500
    lat_step = 0.0035  # ~380m per step
    lon_step = 0.0035  # ~380m per step

    # Create grid nodes
    for r in range(grid_size):
        for c in range(grid_size):
            node_id = r * grid_size + c
            lat = base_lat + (r - grid_size / 2.0) * lat_step
            lon = base_lon + (c - grid_size / 2.0) * lon_step
            g.add_node(node_id, lat=lat, lon=lon, grid_r=r, grid_c=c)

    # Corridors: center rows/columns are fast arterial corridors
    highway_rows = {grid_size // 2}
    highway_cols = {grid_size // 2}

    for r in range(grid_size):
        for c in range(grid_size):
            u = r * grid_size + c

            # Horizontal edge (East)
            if c + 1 < grid_size:
                v = r * grid_size + (c + 1)
                dist_m = haversine_dist(g.nodes[u]["lat"], g.nodes[u]["lon"],
                                        g.nodes[v]["lat"], g.nodes[v]["lon"])

                is_highway = (r in highway_rows)
                speed = 22.2 if is_highway else 11.1
                weight = dist_m / speed

                # ~15% edge drop unless highway
                if is_highway or rng.random() > 0.15:
                    is_oneway = (not is_highway) and (rng.random() < 0.25)
                    g.add_edge(u, v, weight, length=dist_m, speed=speed, highway=is_highway)
                    if not is_oneway:
                        g.add_edge(v, u, weight, length=dist_m, speed=speed, highway=is_highway)

            # Vertical edge (North)
            if r + 1 < grid_size:
                v = (r + 1) * grid_size + c
                dist_m = haversine_dist(g.nodes[u]["lat"], g.nodes[u]["lon"],
                                        g.nodes[v]["lat"], g.nodes[v]["lon"])

                is_highway = (c in highway_cols)
                speed = 22.2 if is_highway else 11.1
                weight = dist_m / speed

                if is_highway or rng.random() > 0.15:
                    is_oneway = (not is_highway) and (rng.random() < 0.25)
                    g.add_edge(u, v, weight, length=dist_m, speed=speed, highway=is_highway)
                    if not is_oneway:
                        g.add_edge(v, u, weight, length=dist_m, speed=speed, highway=is_highway)

    # Retain only the largest SCC
    g_scc = g.extract_largest_scc()
    print(f"[INFO] Synthetic city created: {len(g_scc.nodes)} intersections, {len(g_scc.get_edges())} directed edges (largest SCC).")
    return g_scc


def fetch_osm_thiruvananthapuram(timeout: int = 10) -> Optional[WeightedDirectedGraph]:
    """Attempt to download road network for Thiruvananthapuram from OpenStreetMap via Overpass."""
    print("[INFO] Attempting to download OpenStreetMap data for Thiruvananthapuram via Overpass API...")
    # Bounding box around central Thiruvananthapuram (compact for fast loading and low latency)
    bbox = "8.4800,76.9200,8.5300,76.9700"
    query = f"""
    [out:json][timeout:{timeout}];
    (
      way["highway"~"motorway|trunk|primary|secondary|tertiary|residential"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
    ]

    for url in endpoints:
        try:
            resp = requests.post(url, data={"data": query}, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                if elements:
                    g = parse_osm_elements(elements)
                    if len(g.nodes) >= 50:
                        print(f"[INFO] Successfully downloaded OSM graph ({len(g.nodes)} nodes). Extracting largest SCC...")
                        g_scc = g.extract_largest_scc()
                        return g_scc
        except Exception as e:
            logger.warning(f"Overpass download failed on {url}: {e}")

    print("[WARN] OSM download timed out or failed. Falling back to synthetic city.")
    return None


def parse_osm_elements(elements: List[Dict[str, Any]]) -> WeightedDirectedGraph:
    """Parse Overpass OSM elements into WeightedDirectedGraph."""
    g = WeightedDirectedGraph(is_geographic=True)
    raw_nodes = {}

    for el in elements:
        if el.get("type") == "node":
            raw_nodes[el["id"]] = (el["lat"], el["lon"])

    for el in elements:
        if el.get("type") == "way":
            tags = el.get("tags", {})
            highway = tags.get("highway", "default")
            speed = SPEED_PROFILES.get(highway, SPEED_PROFILES["default"])
            oneway = tags.get("oneway") in ["yes", "1", "true"]

            node_refs = el.get("nodes", [])
            for i in range(len(node_refs) - 1):
                u_id, v_id = node_refs[i], node_refs[i + 1]
                if u_id in raw_nodes and v_id in raw_nodes:
                    lat_u, lon_u = raw_nodes[u_id]
                    lat_v, lon_v = raw_nodes[v_id]

                    g.add_node(u_id, lat=lat_u, lon=lon_u)
                    g.add_node(v_id, lat=lat_v, lon=lon_v)

                    dist_m = haversine_dist(lat_u, lon_u, lat_v, lon_v)
                    weight = dist_m / speed

                    g.add_edge(u_id, v_id, weight, length=dist_m, speed=speed, highway=highway)
                    if not oneway:
                        g.add_edge(v_id, u_id, weight, length=dist_m, speed=speed, highway=highway)

    return g


def attach_synthetic_facilities(graph: WeightedDirectedGraph, seed: int = 42):
    """Place reproducible seeded hospitals and ambulances snapped to intersections.

    Hospital attributes live strictly on the hospital nodes.
    """
    rng = random.Random(seed)
    nodes = list(graph.get_nodes())
    if len(nodes) < 15:
        return

    # Seeded random sample of nodes
    sampled_nodes = rng.sample(nodes, 16)
    hospital_nodes = sampled_nodes[:7]
    ambulance_nodes = sampled_nodes[7:15]

    hospital_defs = [
        {"name": "Govt Medical College Hospital", "specialties": ["trauma", "cardiac", "general"], "beds_total": 50, "beds_free": 6},
        {"name": "General Hospital Thiruvananthapuram", "specialties": ["general", "trauma"], "beds_total": 40, "beds_free": 12},
        {"name": "SCTIMST Super-Specialty", "specialties": ["cardiac", "neurology"], "beds_total": 30, "beds_free": 3},
        {"name": "KIMS Healthcare Centre", "specialties": ["trauma", "cardiac", "general"], "beds_total": 45, "beds_free": 18},
        {"name": "Ananthapuri Multi-Specialty", "specialties": ["cardiac", "general"], "beds_total": 35, "beds_free": 8},
        {"name": "Cosmopolitan Hospital", "specialties": ["general", "trauma"], "beds_total": 30, "beds_free": 15},
        {"name": "PRS Hospital Karamana", "specialties": ["general"], "beds_total": 25, "beds_free": 4},
    ]

    hospitals = []
    for i, nid in enumerate(hospital_nodes):
        h_info = hospital_defs[i]
        node_meta = graph.nodes[nid]
        h_record = {
            "id": f"HOSP_{i+1}",
            "name": h_info["name"],
            "node_id": nid,
            "lat": node_meta.get("lat"),
            "lon": node_meta.get("lon"),
            "beds_free": h_info["beds_free"],
            "beds_total": h_info["beds_total"],
            "specialties": h_info["specialties"],
            "is_synthetic": True
        }
        node_meta["hospital_data"] = h_record
        hospitals.append(h_record)

    ambulances = []
    for i, nid in enumerate(ambulance_nodes):
        node_meta = graph.nodes[nid]
        amb_record = {
            "id": f"AMB_{i+1:02d}",
            "name": f"Ambulance Unit {i+1}",
            "node_id": nid,
            "lat": node_meta.get("lat"),
            "lon": node_meta.get("lon"),
            "status": "available",
            "is_synthetic": True
        }
        node_meta["ambulance_data"] = amb_record
        ambulances.append(amb_record)

    graph.hospitals = hospitals
    graph.ambulances = ambulances


def get_city_graph(force_synthetic: bool = False, seed: int = 42) -> Tuple[WeightedDirectedGraph, str]:
    """Load the city graph from cache, live OSM, or synthetic grid fallback.

    Returns:
    - (graph, source_status_string)
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 1. Check local JSON cache
    if not force_synthetic and os.path.exists(CACHE_FILE):
        try:
            print(f"[INFO] Loading cached city graph from {CACHE_FILE}...")
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            g = WeightedDirectedGraph.from_dict(cache_data["graph"])
            g.hospitals = cache_data.get("hospitals", [])
            g.ambulances = cache_data.get("ambulances", [])
            source_info = cache_data.get("source_info", "Loaded from local JSON cache (Thiruvananthapuram)")
            print(f"[INFO] Loaded cached city graph: {len(g.nodes)} nodes, {len(g.get_edges())} edges. Source: {source_info}")
            return g, source_info
        except Exception as e:
            print(f"[WARN] Failed to load cache file: {e}. Will rebuild...")

    # 2. Attempt OSM download if not forcing synthetic
    g = None
    source_info = ""
    if not force_synthetic:
        g = fetch_osm_thiruvananthapuram()
        if g is not None:
            source_info = "OpenStreetMap live download (Thiruvananthapuram, Kerala, India)"

    # 3. Fallback to synthetic city grid
    if g is None:
        g = generate_synthetic_city(grid_size=16, seed=seed)
        source_info = "Synthetic City Grid (16x16, ~250 intersections, 15% edge drop, highway corridors) [OFFLINE FALLBACK]"

    # Attach hospitals and ambulances
    attach_synthetic_facilities(g, seed=seed)

    # 4. Cache to JSON
    try:
        cache_payload = {
            "source_info": source_info,
            "graph": g.to_dict(),
            "hospitals": g.hospitals,
            "ambulances": g.ambulances
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_payload, f)
        print(f"[INFO] Cached city graph to {CACHE_FILE}")
    except Exception as e:
        print(f"[WARN] Could not write cache file: {e}")

    return g, source_info
