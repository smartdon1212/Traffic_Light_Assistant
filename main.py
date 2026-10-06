
"""Simple traffic-light recognition entrypoint.

This script provides a lightweight, color-based recognizer that can be used
for quick testing without a trained model. It accepts a camera index, video
file, or single image path as input and prints/draws the detected light color
for each frame.

Usage examples:
  python main.py --source 0                # camera
  python main.py --source test_videos/1.mp4 # video file
  python main.py --source images/img.jpg   # image file

This is intentionally self-contained so the project can be exercised even if
`vision_module.py` or model files are not yet implemented. If `vision_module`
or `alert_system` exist and expose expected functions, this script will call
them where appropriate.
"""

import argparse
import os
import sys
import logging
import time
import threading
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, Tuple, Dict

try:
    import cv2
    import numpy as np
except Exception as e:
    print("Missing dependency: please install opencv-python and numpy.")
    raise

# Import configuration
try:
    import config
except ImportError:
    # Fallback defaults if config module not found
    class config:
        RED_LOWER_1 = [0, 120, 50]
        RED_UPPER_1 = [10, 255, 255]
        RED_LOWER_2 = [160, 120, 50]
        RED_UPPER_2 = [180, 255, 255]
        YELLOW_LOWER = [15, 120, 50]
        YELLOW_UPPER = [35, 255, 255]
        GREEN_LOWER = [40, 60, 50]
        GREEN_UPPER = [90, 255, 255]
        DEFAULT_MIN_AREA = 100
        ENABLE_MORPHOLOGY = True
        MORPH_KERNEL_SIZE = 5
        MIN_CONTOUR_AREA = 50
        ENABLE_CONFIDENCE = True
        MIN_CONFIDENCE_RATIO = 1.2
        SHOW_FPS = True
        ALERT_DEBOUNCE_SECONDS = 0.5

    # Optional emergency and traffic control integration
    try:
        import accident_detector
    except Exception:
        accident_detector = None

    try:
        import traffic_control
    except Exception:
        traffic_control = None
    try:
        import model_detector
    except Exception:
        model_detector = None
    try:
        import tracker
    except Exception:
        tracker = None
    try:
        import event_queue
    except Exception:
        event_queue = None

# Attempt to import event_queue again at module level if needed
try:
    import event_queue
except Exception as e:
    print(f"Warning: event_queue import failed: {e}")
    event_queue = None

# Basic logging configuration used by the script and simple submodules.
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
# Ensure we have a logs directory and write INFO logs to a rotating file for
# offline inspection. This is best-effort and will not raise on failure.
try:
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "app.log")
    tr_handler = TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=7, encoding="utf-8")
    tr_handler.setLevel(logging.INFO)
    tr_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(tr_handler)
except Exception:
    # If logging to file fails for any reason (permissions, path issues), keep going.
    pass


# Confirmation worker: reacts to operator confirmations pushed from the web UI
def _confirmation_worker():
    if event_queue is None:
        return
    logger.info('Starting confirmation worker thread')
    while True:
        try:
            conf = event_queue.get_confirmation()
            if conf:
                logger.info('Operator confirmation received: %s', conf)
                # Best-effort: forward confirmation to alert_system and traffic_control
                try:
                    import alert_system as _alert
                    if hasattr(_alert, 'send_emergency_alert'):
                        _alert.send_emergency_alert('high', location='operator', extra={
                                                    'via': 'confirmation'})
                except Exception:
                    logger.debug(
                        'Failed to send alert from confirmation', exc_info=True)

                if traffic_control is not None and hasattr(traffic_control, 'handle_emergency'):
                    try:
                        traffic_control.handle_emergency()
                    except Exception:
                        logger.debug('Traffic control failed', exc_info=True)
        except Exception:
            # swallow and continue
            pass
        time.sleep(0.5)


# Start confirmation worker thread
try:
    if event_queue is not None:
        t = threading.Thread(target=_confirmation_worker, daemon=True)
        t.start()
except Exception:
    logger.debug('Failed to start confirmation worker', exc_info=True)


def detect_traffic_light_color(frame: np.ndarray, min_area: int = 100) -> Tuple[Optional[str], float]:
    """Detect basic traffic-light color in a frame using HSV thresholds.

    Returns: (color, confidence) where color is one of 'red', 'yellow', 'green', or None,
             and confidence is a value from 0.0 to 1.0 indicating detection confidence.
    This is a heuristic and intended for tests / demo only.
    """
    if frame is None:
        return None, 0.0

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Red can be at low or high hue values in HSV, so combine two ranges.
    lower_red1 = np.array(config.RED_LOWER_1)
    upper_red1 = np.array(config.RED_UPPER_1)
    lower_red2 = np.array(config.RED_LOWER_2)
    upper_red2 = np.array(config.RED_UPPER_2)

    red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(
        hsv, lower_red2, upper_red2)

    lower_yellow = np.array(config.YELLOW_LOWER)
    upper_yellow = np.array(config.YELLOW_UPPER)
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    lower_green = np.array(config.GREEN_LOWER)
    upper_green = np.array(config.GREEN_UPPER)
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # Apply morphological operations to clean masks
    if config.ENABLE_MORPHOLOGY:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                           (config.MORPH_KERNEL_SIZE, config.MORPH_KERNEL_SIZE))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)

    # Compute areas
    red_area = int(np.sum(red_mask > 0))
    yellow_area = int(np.sum(yellow_mask > 0))
    green_area = int(np.sum(green_mask > 0))

    areas = {"red": red_area, "yellow": yellow_area, "green": green_area}

    # Sort by area to get top 2 colors
    sorted_areas = sorted(areas.items(), key=lambda kv: kv[1], reverse=True)
    best_color, best_area = sorted_areas[0]
    second_best_area = sorted_areas[1][1]

    # Heuristic threshold to avoid tiny noisy detections
    if best_area < min_area:
        return None, 0.0

    # Calculate confidence based on area ratio
    confidence = 0.5  # Default neutral confidence
    if config.ENABLE_CONFIDENCE and second_best_area > 0:
        ratio = best_area / (second_best_area + 1e-6)
        # Normalize ratio to 0-1 range (ratio of 1.0 = no confidence, ratio > 5.0 = high confidence)
        confidence = min(1.0, (ratio - 1.0) / 5.0)
    else:
        # High confidence if no competition from other colors
        confidence = min(1.0, best_area / 10000.0)

    return best_color, confidence


def process_source(source: str, show: bool = True, min_area: int = 100, max_frames: int = 0) -> None:
    """Process camera/video/image source and run color-based recognition."""
    is_camera = False
    if source.isdigit():
        src = int(source)
        is_camera = True
    else:
        src = source

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        # Try reading as single image
        if os.path.exists(source):
            img = cv2.imread(source)
            if img is None:
                print(f"Failed to read image: {source}")
                return
            color, confidence = detect_traffic_light_color(
                img, min_area=min_area)
            logger.info("Detected (image): %s (confidence: %.2f)",
                        color, confidence)
            try_alert_system(color)
            if show:
                # Add detection info to image
                text = f"{color or 'unknown'} ({confidence:.2%})" if color else "unknown"
                cv2.putText(img, f"Light: {text}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.imshow("result", img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            return
        else:
            print(f"Unable to open source: {source}")
            return

    frame_count = 0
    last_alert_time = {}  # Track last alert time per color for debouncing
    fps_counter = FPSCounter()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # timestamp for this frame
            current_time = time.time()

            color, confidence = detect_traffic_light_color(
                frame, min_area=min_area)
            text = f"{color or 'unknown'} ({confidence:.2%})" if color else "unknown"

            # Draw label on frame
            cv2.putText(frame, f"Light: {text}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Draw FPS counter
            if config.SHOW_FPS:
                fps = fps_counter.get_fps()
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            logger.info("Frame %d: detected=%s, confidence=%.2f",
                        frame_count, text, confidence)

            # Push traffic light event to event queue for web UI
            try:
                if event_queue is not None and color:
                    event_queue.push_event('light', {
                        'color': color,
                        'confidence': float(confidence),
                        'frame_id': frame_count
                    })
            except Exception:
                logger.debug(
                    "Failed to push traffic light event", exc_info=True)

            # Model + tracker based detection (preferred if available)
            detected, severity, em_conf = False, "low", 0.0
            try:
                # Initialize model detector and tracker objects lazily
                if 'model_detector_obj' not in locals() and model_detector is not None:
                    model_detector_obj = model_detector.get_detector()
                if 'tracker_obj' not in locals() and tracker is not None:
                    tracker_obj = tracker.Tracker()

                # If we have a model detector, run it and pass detections to tracker
                if model_detector is not None and model_detector_obj is not None:
                    model_dets = model_detector_obj.detect(frame, conf=0.3)
                    # model_dets already have 'bbox' entries; pass to tracker if available
                    if tracker is not None and tracker_obj is not None:
                        tracks = tracker_obj.update(model_dets)
                        # Try track-based accident detection
                        if accident_detector is not None and hasattr(accident_detector, 'detect_accident_from_tracks'):
                            detected, severity, em_conf = accident_detector.detect_accident_from_tracks(
                                tracks)
                    # Also run single-frame model overlap heuristic as fallback
                    if not detected and accident_detector is not None and hasattr(accident_detector, 'detect_accident_with_model'):
                        det_model, sev_model, conf_model = accident_detector.detect_accident_with_model(
                            frame)
                        if det_model:
                            detected, severity, em_conf = det_model, sev_model, conf_model
                else:
                    # Fallback to old heuristic detector
                    if accident_detector is not None and hasattr(accident_detector, 'detect_accident'):
                        detected, severity, em_conf = accident_detector.detect_accident(
                            frame)
            except Exception:
                detected, severity, em_conf = False, "low", 0.0

            # If an accident is detected, notify emergency backends and apply traffic control
            if detected:
                # Push accident event to event queue for web UI
                try:
                    if event_queue is not None:
                        event_queue.push_event('accident', {
                            'detected': True,
                            'severity': severity,
                            'confidence': float(em_conf),
                            'frame_id': frame_count
                        })
                except Exception:
                    logger.debug(
                        "Failed to push accident event", exc_info=True)

                # Debounce emergency alerts
                last_em = last_alert_time.get("__emergency__", 0)
                if current_time - last_em >= getattr(config, "EMERGENCY_DEBOUNCE_SECONDS", 5.0):
                    try:
                        import alert_system as _alert

                        if hasattr(_alert, "send_emergency_alert"):
                            _alert.send_emergency_alert(severity, location=None, extra={
                                                        "confidence": em_conf})
                    except Exception:
                        logger.debug(
                            "Emergency alert dispatch failed", exc_info=True)

                    # Apply traffic control if enabled
                    if getattr(config, "ENABLE_TRAFFIC_CONTROL", False) and traffic_control is not None:
                        try:
                            traffic_control.handle_emergency()
                        except Exception:
                            logger.debug(
                                "Traffic control failed", exc_info=True)

                    last_alert_time["__emergency__"] = current_time
            # Notify alert system with debouncing
            current_time = time.time()
            if color and config.ENABLE_ALERTS:
                last_time = last_alert_time.get(color, 0)
                if current_time - last_time >= config.ALERT_DEBOUNCE_SECONDS:
                    try_alert_system(color)
                    last_alert_time[color] = current_time

            # Push annotated frame to event queue for web UI display
            try:
                if event_queue is not None:
                    event_queue.push_frame(frame)
            except Exception:
                logger.debug(
                    "Failed to push frame to event queue", exc_info=True)

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                logger.info("Reached max frames (%d), exiting", max_frames)
                break

            if show:
                cv2.imshow("Traffic Light Recognition", frame)
                # If camera, allow real-time quitting
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()
        logger.info("Processed %d frames", frame_count)


class FPSCounter:
    """Simple FPS counter for performance monitoring."""

    def __init__(self, window_size: int = 30):
        """Initialize FPS counter with rolling window.

        Args:
            window_size: Number of frames to average over
        """
        self.window_size = window_size
        self.timestamps = []

    def get_fps(self) -> float:
        """Get current FPS based on recent frames."""
        current_time = time.time()
        self.timestamps.append(current_time)

        # Keep only recent timestamps
        if len(self.timestamps) > self.window_size:
            self.timestamps.pop(0)

        if len(self.timestamps) < 2:
            return 0.0

        time_delta = self.timestamps[-1] - self.timestamps[0]
        if time_delta == 0:
            return 0.0

        return (len(self.timestamps) - 1) / time_delta


def try_alert_system(state: Optional[str]) -> None:
    """If an alert_system module exists and exposes send_alert, call it."""
    if state is None:
        return
    try:
        import alert_system

        if hasattr(alert_system, "send_alert"):
            alert_system.send_alert(state)
    except Exception as e:
        # Not critical; keep main script usable without alert_system.
        logger.debug("Alert system call failed: %s", e)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Traffic light recognition demo")
    p.add_argument("--source", "-s", default="0",
                   help="Camera index (0) or path to video/image")
    p.add_argument("--no-show", dest="show", action="store_false",
                   help="Disable OpenCV window display")
    p.add_argument("--min-area", dest="min_area", type=int, default=100,
                   help="Minimum mask area to consider a detection (default: 100)")
    p.add_argument("--max-frames", dest="max_frames", type=int, default=0,
                   help="If >0, exit after processing this many frames (useful for tests).")
    return p.parse_args()


def main():
    args = parse_args()
    process_source(args.source, show=args.show,
                   min_area=args.min_area, max_frames=args.max_frames)


if __name__ == "__main__":
    main()
