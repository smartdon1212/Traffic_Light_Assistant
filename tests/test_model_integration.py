import numpy as np


def make_two_overlapping_boxes_image():
    import cv2
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # draw two overlapping rectangles (as vehicles)
    cv2.rectangle(img, (40, 50), (120, 150), (0, 0, 255), -1)
    cv2.rectangle(img, (80, 80), (160, 170), (0, 0, 255), -1)
    return img


def test_detect_accident_with_model_monkeypatch(monkeypatch):
    # Create a fake model_detector with overlapping vehicle detections
    fake_dets = [
        {"label": "car", "conf": 0.9, "bbox": [40, 50, 120, 150]},
        {"label": "car", "conf": 0.85, "bbox": [80, 80, 160, 170]},
    ]

    class FakeDetector:
        def detect(self, frame, conf=0.25):
            return fake_dets

    # Monkeypatch model_detector.get_detector to return FakeDetector
    import model_detector as md
    monkeypatch.setattr(md, "get_detector", lambda *args,
                        **kwargs: FakeDetector())

    from accident_detector import detect_accident_with_model
    img = make_two_overlapping_boxes_image()
    detected, severity, conf = detect_accident_with_model(
        img, min_overlap_area=500)
    assert detected is True
    assert severity in ("medium", "high")
    assert 0.0 < conf <= 1.0
