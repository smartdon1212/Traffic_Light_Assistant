"""Conservative accident detection stub.

This module provides a simple, conservative API that can be replaced by a
real model later. The function `detect_accident(frame)` returns a tuple:
    (detected: bool, severity: str, confidence: float)

For now the heuristic is very simple: detect a large blob of saturated red
(or very bright region) which might represent an emergency scene in test
images. Keep this conservative to avoid false positives.
"""
from typing import Tuple

import numpy as np

try:
    import cv2
except Exception:
    cv2 = None

try:
    import model_detector
    _HAS_MODEL = True
except Exception:
    model_detector = None
    _HAS_MODEL = False

# Simple state: previous frame for frame-differencing based motion detection
_prev_gray = None


def detect_accident(frame: np.ndarray, min_area: int = 500) -> Tuple[bool, str, float]:
    """Detect a possible accident in `frame`.

    Returns:
        (detected, severity, confidence)
        - detected: True/False
        - severity: 'low'|'medium'|'high'
        - confidence: float in 0..1
    """
    if frame is None:
        return False, "low", 0.0

    # If OpenCV isn't available, return no detection
    if cv2 is None:
        return False, "low", 0.0

    # Convert to HSV and look for large red regions as a crude proxy
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 80, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 80, 50])
    upper_red2 = np.array([180, 255, 255])

    red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(
        hsv, lower_red2, upper_red2)
    red_area = int(np.sum(red_mask > 0))

    # Motion-based signal: simple frame differencing to reduce false positives
    global _prev_gray
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    motion_area = 0
    if _prev_gray is not None:
        diff = cv2.absdiff(gray, _prev_gray)
        _, diff_mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        motion_area = int(np.sum(diff_mask > 0))
    _prev_gray = gray

    # Combine signals: require red_area and some motion nearby to raise confidence
    # Simple combined score
    if red_area < min_area:
        return False, "low", 0.0

    score = red_area + 2 * motion_area

    if score > min_area * 6:
        severity = "high"
    elif score > min_area * 3:
        severity = "medium"
    else:
        severity = "low"

    confidence = min(1.0, score / (min_area * 8.0))
    return True, severity, float(confidence)


def detect_accident_with_model(frame: np.ndarray, min_overlap_area: int = 400) -> Tuple[bool, str, float]:
    """Use model detections to look for collisions in a single frame.

    Strategy (single-frame conservative): if two vehicle-class bboxes overlap
    by more than `min_overlap_area` pixels, treat as collision candidate.
    """
    if not _HAS_MODEL or model_detector is None:
        return False, "low", 0.0

    det = model_detector.get_detector()
    detections = det.detect(frame, conf=0.25)
    # Filter vehicle-like classes (common COCO labels)
    vehicle_labels = set(["car", "truck", "bus", "motorcycle", "bicycle"])
    boxes = []
    for d in detections:
        if d.get("label") in vehicle_labels:
            x1, y1, x2, y2 = d["bbox"]
            boxes.append((int(x1), int(y1), int(
                x2), int(y2), d.get("conf", 0.0)))

    # Check pairwise overlap
    def overlap_area(a, b):
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        return w * h

    max_overlap = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            oa = overlap_area(boxes[i], boxes[j])
            if oa > max_overlap:
                max_overlap = oa

    if max_overlap >= min_overlap_area:
        # Severity mapping based on overlap
        if max_overlap > min_overlap_area * 4:
            sev = "high"
        else:
            sev = "medium"
        # Confidence scaled from overlap
        conf = min(1.0, max_overlap / (min_overlap_area * 6.0))
        return True, sev, float(conf)
    return False, "low", 0.0


def detect_accident_from_tracks(tracks: list, min_stop_frames: int = 2, stop_dist_thresh: float = 5.0, iou_thresh: float = 0.2) -> Tuple[bool, str, float]:
    """Detect accidents from tracker output using temporal cues.

    - sudden stop: a track that was moving then remains nearly stationary for
      `min_stop_frames` frames (center displacement < stop_dist_thresh)
    - collision: two tracks with IOU > iou_thresh in current frame

    Returns (detected, severity, confidence)
    """
    if not tracks:
        return False, "low", 0.0

    # Helper to compute center
    def center(b):
        x1, y1, x2, y2 = b
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    # Check for collisions via IOU on current bboxes
    max_iou = 0.0
    for i in range(len(tracks)):
        for j in range(i + 1, len(tracks)):
            b1 = tuple(map(int, tracks[i]["bbox"]))
            b2 = tuple(map(int, tracks[j]["bbox"]))
            # compute IOU
            xa1, ya1, xa2, ya2 = b1
            xb1, yb1, xb2, yb2 = b2
            xi1 = max(xa1, xb1)
            yi1 = max(ya1, yb1)
            xi2 = min(xa2, xb2)
            yi2 = min(ya2, yb2)
            w = max(0, xi2 - xi1)
            h = max(0, yi2 - yi1)
            inter = w * h
            area_a = max(0, xa2 - xa1) * max(0, ya2 - ya1)
            area_b = max(0, xb2 - xb1) * max(0, yb2 - yb1)
            union = area_a + area_b - inter
            iou_val = (inter / union) if union > 0 else 0.0
            if iou_val > max_iou:
                max_iou = iou_val

    if max_iou >= iou_thresh:
        # collision candidate
        severity = "high" if max_iou > 0.5 else "medium"
        confidence = min(1.0, max_iou * 1.5)
        return True, severity, float(confidence)

    # Check for sudden stop: examine history lengths
    for t in tracks:
        hist = t.get("history", [])
        if len(hist) >= min_stop_frames + 1:
            # compute center displacement between previous and last
            c_prev = center(hist[-(min_stop_frames + 1)])
            c_last = center(hist[-1])
            dist = ((c_prev[0] - c_last[0]) ** 2 +
                    (c_prev[1] - c_last[1]) ** 2) ** 0.5
            if dist < stop_dist_thresh:
                # Consider as stopped after movement -> accident candidate
                return True, "medium", min(1.0, 0.5)

    return False, "low", 0.0
