"""Event queue and shared state between main.py detection pipeline and web_ui.

This module provides a thread-safe queue for passing detection events (frames,
accidents, confirmations) between the main detection loop and the web UI.

Uses a temporary file for inter-process frame sharing since Flask and main.py
run in separate processes and cannot share Python global variables.
"""
import queue
import threading
import base64
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# Thread-safe queues
event_queue = queue.Queue(maxsize=100)  # events from main.py
confirmation_queue = queue.Queue()      # confirmations from web UI
_latest_frame_b64 = None  # Latest frame as base64 (for web UI display)
_frame_lock = threading.Lock()  # Lock for thread-safe frame updates

# Inter-process frame sharing via temporary file
FRAME_CACHE_FILE = Path(os.getenv('TEMP', '/tmp')) / 'traffic_light_frame.b64'


class Event:
    """An event in the detection pipeline."""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type  # 'frame', 'accident', 'light', etc.
        self.data = data
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "data": self.data
        }


def frame_to_base64(frame: np.ndarray) -> str:
    """Encode frame to base64 for JSON transport."""
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode('utf-8')


def push_event(event_type: str, data: Dict[str, Any]) -> None:
    """Push a detection event to the queue (non-blocking; drops if queue full)."""
    try:
        event_queue.put_nowait(Event(event_type, data))
    except queue.Full:
        pass  # drop oldest event if queue is full


def push_frame(frame: np.ndarray) -> None:
    """Store the latest frame as base64 for web UI display (non-blocking).

    Writes to a temporary file for inter-process sharing (Flask runs in separate process).
    """
    global _latest_frame_b64
    try:
        b64 = frame_to_base64(frame)
        with _frame_lock:
            _latest_frame_b64 = b64

        # Also write to file for inter-process sharing with Flask
        try:
            FRAME_CACHE_FILE.write_text(b64)
        except Exception:
            pass  # Silently fail if file write fails
    except Exception:
        pass  # Silently fail if encoding fails


def get_latest_events(max_count: int = 10) -> list:
    """Get recent events (non-blocking drain of queue)."""
    events = []
    while len(events) < max_count:
        try:
            e = event_queue.get_nowait()
            events.append(e.to_dict())
        except queue.Empty:
            break
    return events


def get_latest_frame() -> Optional[str]:
    """Get latest frame as base64-encoded JPEG string.

    Reads from temporary file for inter-process sharing with main.py.
    Falls back to in-process cache if file doesn't exist.
    """
    try:
        if FRAME_CACHE_FILE.exists():
            return FRAME_CACHE_FILE.read_text()
    except Exception:
        pass

    # Fallback to in-process cache
    with _frame_lock:
        return _latest_frame_b64


def push_confirmation(confirmed: bool, event_id: int = None, operator: str = "unknown") -> None:
    """Push an operator confirmation to the queue."""
    confirmation_queue.put({
        "confirmed": confirmed,
        "event_id": event_id,
        "operator": operator,
        "timestamp": datetime.now().isoformat()
    })


def get_confirmation() -> Optional[Dict]:
    """Get a pending confirmation (non-blocking)."""
    try:
        return confirmation_queue.get_nowait()
    except queue.Empty:
        return None
