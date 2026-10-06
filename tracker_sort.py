"""SORT tracker (lightweight implementation).

This file provides a simple SORT implementation using filterpy's KalmanFilter
for motion prediction and Hungarian algorithm for assignment. If filterpy is
not installed, the module falls back to raising at import time; callers can
catch and use the IOU tracker instead.

Usage:
    from tracker_sort import SortTracker
    t = SortTracker()
    tracks = t.update(detections)

`detections` is a list of dicts with key 'bbox' = [x1,y1,x2,y2]
Return: list of dicts with 'id', 'bbox', 'history'

Note: This is a compact implementation for demo. For production use a
well-tested SORT package.
"""
from typing import List, Dict, Tuple

try:
    from filterpy.kalman import KalmanFilter
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    _HAS_SORT_DEPS = True
except Exception:
    KalmanFilter = None
    np = None
    linear_sum_assignment = None
    _HAS_SORT_DEPS = False


class SortTracker:
    def __init__(self, max_age: int = 5, min_hits: int = 1):
        if not _HAS_SORT_DEPS:
            raise ImportError(
                "filterpy and scipy are required for SortTracker")
        self.max_age = max_age
        self.min_hits = min_hits
        self.trackers = []
        self._next_id = 1

    def _init_kf(self, bbox: Tuple[int, int, int, int]) -> KalmanFilter:
        # State: [x, y, s, r, vx, vy, vs]
        # x,y center, s scale (area), r aspect ratio
        kf = KalmanFilter(dim_x=7, dim_z=4)
        kf.F = np.eye(7)
        for i in range(4):
            kf.F[i, i+3] = 1.0
        kf.H = np.zeros((4, 7))
        kf.H[0, 0] = 1.0
        kf.H[1, 1] = 1.0
        kf.H[2, 2] = 1.0
        kf.H[3, 3] = 1.0
        # Reasonable covariances
        kf.R *= 10.0
        kf.P *= 10.0
        kf.Q *= 0.01
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        x = x1 + w / 2.0
        y = y1 + h / 2.0
        s = w * h
        r = w / float(h + 1e-6)
        kf.x[:4, 0] = np.array([x, y, s, r]).reshape((4,))
        return kf

    def update(self, detections: List[Dict]) -> List[Dict]:
        # Predict existing trackers
        for trk in self.trackers:
            trk['kf'].predict()
            trk['age'] += 1

        # Build detection array
        dets = []
        for d in detections:
            dets.append(d['bbox'])
        dets = np.array(dets) if len(dets) > 0 else np.empty((0, 4))

        # Associate
        if len(self.trackers) == 0:
            matched, unmatched_dets, unmatched_trks = [], list(
                range(len(dets))), []
        else:
            trk_preds = []
            for trk in self.trackers:
                # extract predicted bbox from kf state
                x, y, s, r = trk['kf'].x[:4, 0]
                w = (s * r) ** 0.5
                h = s / (w + 1e-6)
                x1 = x - w / 2.0
                y1 = y - h / 2.0
                x2 = x + w / 2.0
                y2 = y + h / 2.0
                trk_preds.append([x1, y1, x2, y2])
            trk_preds = np.array(trk_preds)

            if dets.size == 0:
                matched, unmatched_dets, unmatched_trks = [
                ], [], list(range(len(self.trackers)))
            else:
                # cost matrix using IOU
                iou_mat = np.zeros((len(trk_preds), len(dets)), dtype=float)
                for t_i, t in enumerate(trk_preds):
                    for d_i, d in enumerate(dets):
                        xa1, ya1, xa2, ya2 = t
                        xb1, yb1, xb2, yb2 = d
                        xi1 = max(xa1, xb1)
                        yi1 = max(ya1, yb1)
                        xi2 = min(xa2, xb2)
                        yi2 = min(ya2, yb2)
                        w = max(0, xi2 - xi1)
                        h = max(0, yi2 - yi1)
                        inter = w * h
                        area_a = max(0, xa2 - xa1) * max(0, ya2 - ya1)
                        area_b = max(0, xb2 - xb1) * max(0, yb2 - y1)
                        union = area_a + area_b - inter
                        iou_mat[t_i, d_i] = 0.0 if union <= 0 else inter / union
                # Hungarian: maximize IOU -> minimize -IOU cost
                row_ind, col_ind = linear_sum_assignment(-iou_mat)
                matched, unmatched_trks, unmatched_dets = [], list(
                    range(len(self.trackers))), list(range(len(dets)))
                for r, c in zip(row_ind, col_ind):
                    if iou_mat[r, c] >= 0.3:
                        matched.append((r, c))
                        unmatched_trks.remove(r)
                        unmatched_dets.remove(c)

        # Update matched trackers with assigned detections
        for trk_idx, det_idx in matched:
            bbox = tuple(map(int, detections[det_idx]['bbox']))
            trk = self.trackers[trk_idx]
            trk['kf'].update(self._bbox_to_z(bbox))
            trk['history'].append(bbox)
            trk['age'] = 0
            trk['time_since_update'] = 0

        # Create new trackers for unmatched detections
        for di in unmatched_dets:
            bbox = tuple(map(int, detections[di]['bbox']))
            kf = self._init_kf(bbox)
            trk = {'id': self._next_id, 'kf': kf, 'history': [
                bbox], 'age': 0, 'time_since_update': 0}
            self._next_id += 1
            self.trackers.append(trk)

        # Remove dead trackers
        self.trackers = [t for t in self.trackers if t['age'] <= self.max_age]

        # Return track dicts
        out = []
        for t in self.trackers:
            out.append({'id': t['id'], 'bbox': t['history']
                       [-1], 'history': list(t['history'])})
        return out

    def _bbox_to_z(self, bbox: Tuple[int, int, int, int]):
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        x = x1 + w / 2.0
        y = y1 + h / 2.0
        s = w * h
        r = w / float(h + 1e-6)
        return np.array([x, y, s, r])


*** End Patch
