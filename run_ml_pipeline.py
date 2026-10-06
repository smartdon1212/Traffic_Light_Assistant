"""Run ML detector + tracker pipeline and save annotated output.

Usage:
    python run_ml_pipeline.py --source path/to/video.mp4 --out output.mp4

This script is optional and requires `ultralytics` for model inference. It
will fall back to drawing detections without tracking if model/tracker not
available.
"""
import argparse
import os
import time
import logging

try:
    import cv2
except Exception:
    cv2 = None

logger = logging.getLogger(__name__)


def draw_tracks(frame, tracks):
    for t in tracks:
        x1, y1, x2, y2 = map(int, t['bbox'])
        tid = t.get('id', 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID:{tid}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


def draw_dets(frame, dets):
    for d in dets:
        x1, y1, x2, y2 = map(int, d['bbox'])
        label = d.get('label', '')
        conf = d.get('conf', 0.0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(frame, f"{label}:{conf:.2f}", (x1, y2 + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', '-s', default='0')
    p.add_argument('--out', '-o', default='output.mp4')
    p.add_argument('--max-frames', type=int, default=0)
    args = p.parse_args()

    try:
        import model_detector
        md = model_detector.get_detector()
    except Exception:
        md = None
    try:
        from tracker_sort import SortTracker
        tracker = SortTracker()
    except Exception:
        try:
            from tracker import Tracker as FallbackTracker
            tracker = FallbackTracker()
        except Exception:
            tracker = None

    if cv2 is None:
        print("OpenCV not available; cannot run pipeline")
        return

    cap = cv2.VideoCapture(args.source if not str(
        args.source).isdigit() else int(args.source))
    if not cap.isOpened():
        print(f"Unable to open source: {args.source}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.out, fourcc, fps, (width, height))

    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            dets = []
            if md is not None:
                dets = md.detect(frame, conf=0.25)

            tracks = []
            if tracker is not None:
                # tracker expects detections with 'bbox'
                tracks = tracker.update(dets if dets else [])

            # Draw
            if dets:
                draw_dets(frame, dets)
            if tracks:
                draw_tracks(frame, tracks)

            out.write(frame)
            frame_count += 1
            if args.max_frames and frame_count >= args.max_frames:
                break
    finally:
        cap.release()
        out.release()

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
