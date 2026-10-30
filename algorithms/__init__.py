"""Algorithms package for Emergency Ambulance Routing System.
Includes pure Python implementations of:
- Dijkstra's Algorithm (binary heap, heapq)
- A* Search (f = g + h, straight-line distance / v_max heuristic)
- Bellman-Ford Algorithm (V-1 passes + negative cycle detection)
"""

from .dijkstra import dijkstra, AlgorithmResult
from .astar import astar
from .bellman_ford import bellman_ford

__all__ = ["dijkstra", "astar", "bellman_ford", "AlgorithmResult"]
