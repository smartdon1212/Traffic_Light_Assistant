"""Lightweight IOU-based tracker for demo use.

This tracker assigns persistent IDs to detections across frames using a
simple greedy IOU matching. It's not as robust as SORT/DeepSORT but has
no external dependencies and is suitable for integration and testing.

API:
- Tracker(max_lost=5, iou_threshold=0.3)
- update(detections) -> List[track_dict]

Each detection is expected to be a dict with key 'bbox' = [x1,y1,x2,y2].
Each track_dict has: {'id', 'bbox', 'history': [bboxes], 'lost_frames'}

"""
from typing import List, Dict, Tuple
import itertools


def iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    xa1, ya1, xa2, ya2 = a
    xb1, yb1, xb2, yb2 = b
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
    if union == 0:
        return 0.0
    return inter / union


class Track:
    def __init__(self, tid: int, bbox: Tuple[int, int, int, int]):
        self.id = tid
        self.bbox = bbox
        self.history = [bbox]
        self.lost_frames = 0

    def to_dict(self) -> Dict:
        return {"id": self.id, "bbox": self.bbox, "history": list(self.history), "lost_frames": self.lost_frames}


class Tracker:
    def __init__(self, max_lost: int = 5, iou_threshold: float = 0.3):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self._next_id = 1
        self.tracks: List[Track] = []

    def _match(self, detections: List[Dict]) -> None:
        # Build IOU matrix between tracks and detections
        if len(self.tracks) == 0:
            return
        iou_matrix = []
        for t in self.tracks:
            row = []
            for d in detections:
                row.append(iou(t.bbox, tuple(map(int, d.get("bbox")))))
            iou_matrix.append(row)

        # Greedy matching: pick highest IOU and assign if above threshold
        assigned_tracks = set()
        assigned_dets = set()
        pairs = []  # (track_idx, det_idx, iou)
        for ti, di in itertools.product(range(len(self.tracks)), range(len(detections))):
            pairs.append((ti, di, iou_matrix[ti][di]))
        pairs.sort(key=lambda x: x[2], reverse=True)

        for ti, di, val in pairs:
            if val < self.iou_threshold:
                break
            if ti in assigned_tracks or di in assigned_dets:
                continue
            # assign
            assigned_tracks.add(ti)
            assigned_dets.add(di)
            self.tracks[ti].bbox = tuple(map(int, detections[di].get("bbox")))
            self.tracks[ti].history.append(self.tracks[ti].bbox)
            self.tracks[ti].lost_frames = 0

        # Unassigned tracks: increment lost_frames
        for idx, t in enumerate(self.tracks):
            if idx not in assigned_tracks:
                t.lost_frames += 1

        # Unassigned detections: create new tracks
        for di, d in enumerate(detections):
            if di not in assigned_dets:
                self._create_track(d)

    def _create_track(self, detection: Dict) -> None:
        bbox = tuple(map(int, detection.get("bbox")))
        t = Track(self._next_id, bbox)
        self._next_id += 1
        self.tracks.append(t)

    def _prune(self) -> None:
        # Remove tracks that have been lost for too many frames
        self.tracks = [
            t for t in self.tracks if t.lost_frames <= self.max_lost]

    def update(self, detections: List[Dict]) -> List[Dict]:
        """Update tracker with current frame detections.

        detections: list of dicts, each with 'bbox'
        Returns list of track dicts.
        """
        # If no existing tracks, create from detections
        if len(self.tracks) == 0:
            for d in detections:
                self._create_track(d)
            self._prune()
            return [t.to_dict() for t in self.tracks]

        # Match detections to tracks
        self._match(detections)
        self._prune()
        return [t.to_dict() for t in self.tracks]
