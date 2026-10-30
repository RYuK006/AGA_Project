"""Weighted Directed Graph Model for Road Networks and Algorithm Visualizations.

Adjacency List Representation:
  dict[node] -> list[(neighbor, weight_in_seconds)]

Adheres strictly to problem specification:
- Directed edges: two-way road = 2 edges, one-way road = 1 edge.
- w(u, v) = length / speed in seconds.
- Hospital attributes (beds_free, beds_total, specialties) reside on nodes.
- Largest Strongly Connected Component (SCC) extraction via Tarjan's algorithm.
- Admissible A* heuristic: h(n) = distance(n, goal) / v_max.
"""

import math
from typing import Dict, List, Tuple, Any, Optional, Set


class WeightedDirectedGraph:
    def __init__(self, is_geographic: bool = True, default_speed: float = 13.89):
        """
        Parameters:
        - is_geographic: If True, coords are (lat, lon) and distance is Haversine (meters).
                         If False, coords are (x, y) Cartesian.
        - default_speed: Default speed in meters/second (13.89 m/s = 50 km/h).
        """
        self.adj: Dict[Any, List[Tuple[Any, float]]] = {}
        self.nodes: Dict[Any, Dict[str, Any]] = {}
        self.edge_meta: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
        self.is_geographic = is_geographic
        self.default_speed = default_speed
        self.v_max: float = default_speed

    def add_node(self, node_id: Any, lat: Optional[float] = None, lon: Optional[float] = None,
                 x: Optional[float] = None, y: Optional[float] = None, **attrs):
        if node_id not in self.adj:
            self.adj[node_id] = []
        node_info = {
            "lat": lat,
            "lon": lon,
            "x": x if x is not None else lon,
            "y": y if y is not None else lat,
            **attrs
        }
        self.nodes[node_id] = node_info

    def add_edge(self, u: Any, v: Any, weight: float, length: Optional[float] = None,
                 speed: Optional[float] = None, **attrs):
        if u not in self.adj:
            self.add_node(u)
        if v not in self.adj:
            self.add_node(v)

        self.adj[u].append((v, float(weight)))

        if speed is not None and speed > self.v_max:
            self.v_max = speed

        self.edge_meta[(u, v)] = {
            "weight": float(weight),
            "length": float(length) if length is not None else None,
            "speed": float(speed) if speed is not None else None,
            **attrs
        }

    def get_neighbors(self, u: Any) -> List[Tuple[Any, float]]:
        return self.adj.get(u, [])

    def get_nodes(self) -> List[Any]:
        return list(self.nodes.keys())

    def get_edges(self) -> List[Tuple[Any, Any, float]]:
        result = []
        for u, neighbors in self.adj.items():
            for v, w in neighbors:
                result.append((u, v, w))
        return result

    def get_reversed_graph(self) -> "WeightedDirectedGraph":
        """Return a new graph with every directed edge (u, v, w) reversed to (v, u, w).

        Essential for single-search ambulance ranking from the incident.
        """
        rev = WeightedDirectedGraph(is_geographic=self.is_geographic, default_speed=self.default_speed)
        rev.v_max = self.v_max

        for n, meta in self.nodes.items():
            rev.nodes[n] = dict(meta)
            rev.adj[n] = []

        for u, neighbors in self.adj.items():
            for v, w in neighbors:
                rev.adj[v].append((u, w))
                meta = self.edge_meta.get((u, v), {})
                rev.edge_meta[(v, u)] = dict(meta)

        return rev

    def straight_line_distance(self, u: Any, v: Any) -> float:
        """Compute spatial straight-line distance between nodes u and v.

        Returns meters if geographic (Haversine), else Euclidean distance.
        """
        node_u = self.nodes.get(u)
        node_v = self.nodes.get(v)
        if not node_u or not node_v:
            return 0.0

        if self.is_geographic:
            lat1, lon1 = node_u.get("lat"), node_u.get("lon")
            lat2, lon2 = node_v.get("lat"), node_v.get("lon")
            if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                return 0.0
            # Haversine formula
            R = 6371000.0  # Earth radius in meters
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
            return R * c
        else:
            x1, y1 = node_u.get("x", 0.0), node_u.get("y", 0.0)
            x2, y2 = node_v.get("x", 0.0), node_v.get("y", 0.0)
            return math.hypot(x2 - x1, y2 - y1)

    def heuristic(self, u: Any, target: Any) -> float:
        """Admissible A* heuristic: h(n) = distance(n, target) / v_max (in seconds).

        Since no vehicle can travel faster than v_max, distance / v_max <= true_time.
        Guaranteed admissible: h(n) <= h*(n).
        """
        if u == target:
            return 0.0
        dist = self.straight_line_distance(u, target)
        if self.v_max <= 0:
            return 0.0
        return dist / self.v_max

    def snap_to_nearest(self, lat_or_y: float, lon_or_x: float) -> Any:
        """Find the nearest road intersection node to the given coordinates."""
        best_node = None
        best_dist = float("inf")

        for node_id, meta in self.nodes.items():
            if self.is_geographic:
                n_lat, n_lon = meta.get("lat"), meta.get("lon")
                if n_lat is None or n_lon is None:
                    continue
                d = math.hypot(n_lat - lat_or_y, n_lon - lon_or_x)
            else:
                n_x, n_y = meta.get("x", 0.0), meta.get("y", 0.0)
                d = math.hypot(n_x - lon_or_x, n_y - lat_or_y)

            if d < best_dist:
                best_dist = d
                best_node = node_id

        return best_node

    def extract_largest_scc(self) -> "WeightedDirectedGraph":
        """Compute Strongly Connected Components (SCCs) using Tarjan's algorithm

        and return a new graph retaining ONLY the largest SCC.
        """
        index = 0
        indices: Dict[Any, int] = {}
        lowlinks: Dict[Any, int] = {}
        stack: List[Any] = []
        on_stack: Set[Any] = set()
        sccs: List[List[Any]] = []

        def strongconnect(node):
            nonlocal index
            indices[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for neighbor, _ in self.adj.get(node, []):
                if neighbor not in indices:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif neighbor in on_stack:
                    lowlinks[node] = min(lowlinks[node], indices[neighbor])

            if lowlinks[node] == indices[node]:
                current_scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    current_scc.append(w)
                    if w == node:
                        break
                sccs.append(current_scc)

        for n in list(self.nodes.keys()):
            if n not in indices:
                strongconnect(n)

        if not sccs:
            return self

        # Identify largest SCC by number of nodes
        largest_scc_nodes = set(max(sccs, key=len))

        # Build induced subgraph
        subgraph = WeightedDirectedGraph(is_geographic=self.is_geographic, default_speed=self.default_speed)
        subgraph.v_max = self.v_max

        for n in largest_scc_nodes:
            subgraph.nodes[n] = dict(self.nodes[n])
            subgraph.adj[n] = []

        for u in largest_scc_nodes:
            for v, w in self.adj.get(u, []):
                if v in largest_scc_nodes:
                    subgraph.adj[u].append((v, w))
                    if (u, v) in self.edge_meta:
                        subgraph.edge_meta[(u, v)] = dict(self.edge_meta[(u, v)])

        return subgraph

    def get_subgraph(self, subset_nodes: Set[Any]) -> "WeightedDirectedGraph":
        """Create an induced subgraph for the specified subset of nodes."""
        sub = WeightedDirectedGraph(is_geographic=self.is_geographic, default_speed=self.default_speed)
        sub.v_max = self.v_max
        for n in subset_nodes:
            if n in self.nodes:
                sub.nodes[n] = dict(self.nodes[n])
                sub.adj[n] = []
        for u in subset_nodes:
            for v, w in self.adj.get(u, []):
                if v in subset_nodes:
                    sub.adj[u].append((v, w))
                    if (u, v) in self.edge_meta:
                        sub.edge_meta[(u, v)] = dict(self.edge_meta[(u, v)])
        return sub

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary for JSON caching and API transfer."""
        edges_list = []
        for u, neighbors in self.adj.items():
            for v, w in neighbors:
                meta = self.edge_meta.get((u, v), {})
                edges_list.append({
                    "u": u,
                    "v": v,
                    "weight": w,
                    "length": meta.get("length"),
                    "speed": meta.get("speed")
                })

        return {
            "is_geographic": self.is_geographic,
            "default_speed": self.default_speed,
            "v_max": self.v_max,
            "nodes": {str(k): v for k, v in self.nodes.items()},
            "edges": edges_list
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeightedDirectedGraph":
        """Reconstruct graph from dictionary."""
        g = cls(is_geographic=data.get("is_geographic", True),
                default_speed=data.get("default_speed", 13.89))
        g.v_max = data.get("v_max", 13.89)

        for node_id, meta in data.get("nodes", {}).items():
            # Keep node IDs as ints if they represent integer OSM/grid IDs
            nid = int(node_id) if node_id.isdigit() else node_id
            g.nodes[nid] = meta
            g.adj[nid] = []

        for e in data.get("edges", []):
            u = int(e["u"]) if str(e["u"]).isdigit() else e["u"]
            v = int(e["v"]) if str(e["v"]).isdigit() else e["v"]
            w = float(e["weight"])
            g.adj[u].append((v, w))
            g.edge_meta[(u, v)] = {
                "weight": w,
                "length": e.get("length"),
                "speed": e.get("speed")
            }

        return g
