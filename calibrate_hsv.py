"""Interactive HSV calibration utility.

Run this script and use the trackbars to adjust HSV lower/upper bounds for
red/yellow/green. Press 's' to save the current thresholds to `config.py`
(if found) or print them to stdout.

Usage:
    python calibrate_hsv.py
"""
import cv2
import numpy as np
import os

WINDOW = "HSV Calibration"

# Default starting values (match config defaults)
state = {
    "r_h_low": 0, "r_s_low": 120, "r_v_low": 50,
    "r_h_high": 10, "r_s_high": 255, "r_v_high": 255,
    "r2_h_low": 160, "r2_s_low": 120, "r2_v_low": 50,
    "r2_h_high": 180, "r2_s_high": 255, "r2_v_high": 255,
    "y_h_low": 15, "y_s_low": 120, "y_v_low": 50,
    "y_h_high": 35, "y_s_high": 255, "y_v_high": 255,
    "g_h_low": 40, "g_s_low": 60, "g_v_low": 50,
    "g_h_high": 90, "g_s_high": 255, "g_v_high": 255,
}

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("No webcam found — running with a blank frame for calibration")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
else:
    ret, frame = cap.read()
    if not ret:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

# Create trackbars
for k, v in state.items():
    cv2.createTrackbar(k, WINDOW, v, 255, lambda x: None)

print("Press 's' to print/save thresholds, 'q' or ESC to exit")

while True:
    if cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Read trackbar values
    for k in list(state.keys()):
        state[k] = cv2.getTrackbarPos(k, WINDOW)

    r_mask1 = cv2.inRange(hsv, (state["r_h_low"], state["r_s_low"], state["r_v_low"]),
                          (state["r_h_high"], state["r_s_high"], state["r_v_high"]))
    r_mask2 = cv2.inRange(hsv, (state["r2_h_low"], state["r2_s_low"], state["r2_v_low"]),
                          (state["r2_h_high"], state["r2_s_high"], state["r2_v_high"]))
    r_mask = cv2.bitwise_or(r_mask1, r_mask2)

    y_mask = cv2.inRange(hsv, (state["y_h_low"], state["y_s_low"], state["y_v_low"]),
                         (state["y_h_high"], state["y_s_high"], state["y_v_high"]))
    g_mask = cv2.inRange(hsv, (state["g_h_low"], state["g_s_low"], state["g_v_low"]),
                         (state["g_h_high"], state["g_s_high"], state["g_v_high"]))

    # Stack for display
    masks = np.hstack([
        cv2.cvtColor(r_mask, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(y_mask, cv2.COLOR_GRAY2BGR),
        cv2.cvtColor(g_mask, cv2.COLOR_GRAY2BGR),
    ])

    disp = cv2.resize(np.vstack([frame, masks]), (800, 600))
    cv2.imshow(WINDOW, disp)

    key = cv2.waitKey(50) & 0xFF
    if key == ord("q") or key == 27:
        break
    if key == ord("s"):
        # Print a config-friendly snippet
        print("# Paste these into config.py")
        print(
            f"RED_LOWER_1 = [{state['r_h_low']}, {state['r_s_low']}, {state['r_v_low']}]")
        print(
            f"RED_UPPER_1 = [{state['r_h_high']}, {state['r_s_high']}, {state['r_v_high']}]")
        print(
            f"RED_LOWER_2 = [{state['r2_h_low']}, {state['r2_s_low']}, {state['r2_v_low']}]")
        print(
            f"RED_UPPER_2 = [{state['r2_h_high']}, {state['r2_s_high']}, {state['r2_v_high']}]")
        print(
            f"YELLOW_LOWER = [{state['y_h_low']}, {state['y_s_low']}, {state['y_v_low']}]")
        print(
            f"YELLOW_UPPER = [{state['y_h_high']}, {state['y_s_high']}, {state['y_v_high']}]")
        print(
            f"GREEN_LOWER = [{state['g_h_low']}, {state['g_s_low']}, {state['g_v_low']}]")
        print(
            f"GREEN_UPPER = [{state['g_h_high']}, {state['g_s_high']}, {state['g_v_high']}]")

cv2.destroyAllWindows()
if cap.isOpened():
    cap.release()
