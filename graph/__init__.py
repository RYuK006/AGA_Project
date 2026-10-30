"""Graph module for Emergency Ambulance Routing System.
Includes:
- WeightedDirectedGraph model with adjacency list, reversal, and SCC extraction
- Toy graph definitions (5-node standard, negative-credit, negative-cycle)
- City graph loader (OSM Thiruvananthapuram with offline JSON cache and synthetic grid fallback)
"""

from .graph_model import WeightedDirectedGraph
from .toy_graph import get_toy_graph, get_negative_credit_graph, get_negative_cycle_graph
from .city_graph import get_city_graph

__all__ = [
    "WeightedDirectedGraph",
    "get_toy_graph",
    "get_negative_credit_graph",
    "get_negative_cycle_graph",
    "get_city_graph",
]
