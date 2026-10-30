"""Automated demo walkthrough and screenshot capture using Playwright.

Captures real screenshots from the running web application for:
- Tab 1: Learn (Toy Graph with full S->P->I->H path highlighted and live state)
- Tab 2: City Dispatch (Ambulance assignment, hospital ranking, route, search frontier)
- Tab 3: Benchmark (Empirical charts and 100% cost equality verification)
- Tab 4: Negative Weights (Dijkstra failure 13s vs Bellman-Ford optimum 11s)
Also executes the 300-query benchmark and saves real numbers to `benchmark_results.json`.
"""

import os
import sys
import json
import time

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from playwright.sync_api import sync_playwright
from benchmark.runner import run_benchmark
from graph.city_graph import get_city_graph

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def capture_all():
    print("[INFO] Capturing real demo screenshots with Playwright...")

    # Run real benchmark first and save empirical results
    print("[INFO] Executing empirical benchmark (300 queries)...")
    city, _ = get_city_graph(force_synthetic=False, seed=42)
    bench_summary = run_benchmark(city, num_queries=300, bellman_sample_size=30, seed=42)
    bench_file = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(bench_file, "w", encoding="utf-8") as f:
        json.dump({
            "sample_size": bench_summary.sample_size,
            "bellman_sample_size": bench_summary.bellman_sample_size,
            "graph_nodes_count": bench_summary.graph_nodes_count,
            "graph_edges_count": bench_summary.graph_edges_count,
            "cost_equality_pass_rate": bench_summary.cost_equality_pass_rate,
            "dijkstra_nodes_mean": bench_summary.dijkstra_nodes.mean,
            "dijkstra_nodes_median": bench_summary.dijkstra_nodes.median,
            "astar_nodes_mean": bench_summary.astar_nodes.mean,
            "astar_nodes_median": bench_summary.astar_nodes.median,
            "dijkstra_time_mean": bench_summary.dijkstra_time_ms.mean,
            "astar_time_mean": bench_summary.astar_time_ms.mean,
            "bellman_time_mean": bench_summary.bellman_time_ms.mean if bench_summary.bellman_time_ms else 0.0,
            "node_reduction_ratio": bench_summary.node_reduction_ratio,
            "runtime_speedup_ratio": bench_summary.runtime_speedup_ratio,
            "bellman_slowdown_ratio": bench_summary.bellman_slowdown_ratio,
            "interpretation": bench_summary.interpretation
        }, f, indent=2)
    print(f"[INFO] Saved empirical benchmark metrics to {bench_file}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[INFO] Navigating to http://127.0.0.1:8000 ...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # ----------------------------------------------------
        # 1. Tab 1: Learn
        # ----------------------------------------------------
        print("[INFO] Capturing Tab 1: Learn...")
        # Step through to target reached
        for _ in range(12):
            page.click("#btn-toy-step")
            page.wait_for_timeout(100)
        page.wait_for_timeout(500)
        tab1_path = os.path.join(SCREENSHOTS_DIR, "tab1_learn.png")
        page.screenshot(path=tab1_path)
        print(f"[INFO] Saved {tab1_path}")

        # ----------------------------------------------------
        # 2. Tab 2: City Dispatch
        # ----------------------------------------------------
        print("[INFO] Capturing Tab 2: City Dispatch...")
        page.click('button[data-tab="tab-dispatch"]')
        page.wait_for_timeout(500)
        page.click("#btn-quick-incident")
        page.wait_for_timeout(300)
        page.click("#btn-run-dispatch")
        page.wait_for_timeout(1500)  # Wait for route draw & frontier animation
        tab2_path = os.path.join(SCREENSHOTS_DIR, "tab2_dispatch.png")
        page.screenshot(path=tab2_path)
        print(f"[INFO] Saved {tab2_path}")

        # ----------------------------------------------------
        # 3. Tab 3: Benchmark
        # ----------------------------------------------------
        print("[INFO] Capturing Tab 3: Benchmark...")
        page.click('button[data-tab="tab-benchmark"]')
        page.wait_for_timeout(500)
        page.click("#btn-run-benchmark")
        # Wait until benchmark completes and table populates
        page.wait_for_selector("#bench-tbody tr", timeout=30000)
        page.wait_for_timeout(1200)
        tab3_path = os.path.join(SCREENSHOTS_DIR, "tab3_benchmark.png")
        page.screenshot(path=tab3_path)
        print(f"[INFO] Saved {tab3_path}")

        # ----------------------------------------------------
        # 4. Tab 4: Negative Weights
        # ----------------------------------------------------
        print("[INFO] Capturing Tab 4: Negative Weights...")
        page.click('button[data-tab="tab-negative"]')
        page.wait_for_timeout(500)
        page.click("#btn-neg-compare")
        page.wait_for_timeout(1000)
        tab4_path = os.path.join(SCREENSHOTS_DIR, "tab4_negative.png")
        page.screenshot(path=tab4_path)
        print(f"[INFO] Saved {tab4_path}")

        browser.close()
        print("[SUCCESS] All screenshots and benchmark numbers successfully captured!")


if __name__ == "__main__":
    capture_all()
