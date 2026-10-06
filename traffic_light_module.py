"""Compatibility stub for a model-based traffic light detector.

This exposes `detect(frame, min_area=100) -> Optional[str]` so callers can
swap in a model implementation later. For now it delegates to the heuristic
detector in `main.py`.
"""
from typing import Optional


def detect(frame, min_area: int = 100) -> Optional[str]:
    try:
        from main import detect_traffic_light_color

        return detect_traffic_light_color(frame, min_area=min_area)
    except Exception:
        return None
