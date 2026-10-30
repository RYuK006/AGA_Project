"""Emergency Ambulance Routing System - Launcher.

Usage:
    python run.py
or:
    uvicorn app:app --reload --port 8000
"""

import sys
import os
import uvicorn

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    if curr_dir not in sys.path:
        sys.path.insert(0, curr_dir)

    print("=" * 70)
    print("EMERGENCY AMBULANCE ROUTING SYSTEM")
    print("KTU B.Tech S5 - Advanced Graph Algorithms")
    print("=" * 70)
    print("Starting local server at: http://127.0.0.1:8000")
    print("Open your browser and navigate to http://127.0.0.1:8000")
    print("Press Ctrl+C to terminate.")
    print("=" * 70)

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
