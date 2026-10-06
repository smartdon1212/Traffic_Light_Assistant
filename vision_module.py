"""Simple vision module wrapper used by the demo.

Provides a tiny `detect(frame, min_area=100)` function that delegates to the
heuristic detector in `main.detect_traffic_light_color`. This keeps the demo
API stable while avoiding duplication of heavy logic.
"""
from typing import Optional


def detect(frame, min_area: int = 100) -> Optional[str]:
    try:
        # Import the heuristic from main; main guards running the script with
        # if __name__ == "__main__": so importing is safe.
        from main import detect_traffic_light_color

        return detect_traffic_light_color(frame, min_area=min_area)
    except Exception:
        return None
