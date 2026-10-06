import numpy as np


def make_image_with_red_blob(center=(50, 50), radius=20, size=(100, 100, 3)):
    import cv2
    img = np.zeros(size, dtype=np.uint8)
    cv2.circle(img, center, radius, (0, 0, 255), -1)
    return img


def test_accident_detection_on_large_red():
    from accident_detector import detect_accident
    img = make_image_with_red_blob(radius=25)
    detected, severity, conf = detect_accident(img, min_area=50)
    assert detected is True
    assert severity in ("low", "medium", "high")
    assert 0.0 < conf <= 1.0


def test_no_accident_on_empty():
    from accident_detector import detect_accident
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    detected, severity, conf = detect_accident(img, min_area=50)
    assert detected is False
    assert conf == 0.0
