import numpy as np


def make_image_with_circle(bgr_color, center=(50, 50), radius=20, size=(100, 100, 3)):
    img = np.zeros(size, dtype=np.uint8)
    # OpenCV expects BGR
    import cv2

    cv2.circle(img, center, radius, bgr_color, -1)
    return img


def test_detect_red():
    from main import detect_traffic_light_color

    # Bright red in BGR
    img = make_image_with_circle((0, 0, 255))
    color, confidence = detect_traffic_light_color(img, min_area=10)
    assert color == "red", f"Expected 'red', got '{color}'"
    assert confidence > 0, f"Expected positive confidence, got {confidence}"


def test_detect_yellow():
    from main import detect_traffic_light_color

    # Yellow (BGR)
    img = make_image_with_circle((0, 255, 255))
    color, confidence = detect_traffic_light_color(img, min_area=10)
    assert color == "yellow", f"Expected 'yellow', got '{color}'"
    assert confidence > 0, f"Expected positive confidence, got {confidence}"


def test_detect_green():
    from main import detect_traffic_light_color

    # Green (BGR)
    img = make_image_with_circle((0, 255, 0))
    color, confidence = detect_traffic_light_color(img, min_area=10)
    assert color == "green", f"Expected 'green', got '{color}'"
    assert confidence > 0, f"Expected positive confidence, got {confidence}"


def test_detect_none_on_empty():
    """Test that empty image returns None."""
    from main import detect_traffic_light_color

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    color, confidence = detect_traffic_light_color(img, min_area=100)
    assert color is None, f"Expected None for empty image, got '{color}'"
    assert confidence == 0.0, f"Expected 0.0 confidence, got {confidence}"


def test_detect_small_area():
    """Test that small detections below min_area are filtered."""
    from main import detect_traffic_light_color

    img = make_image_with_circle((0, 0, 255), radius=2)  # Very small circle
    color, confidence = detect_traffic_light_color(img, min_area=500)
    assert color is None, f"Expected None for small area, got '{color}'"


def test_multiple_colors_picks_largest():
    """Test that with multiple colors, the largest area wins."""
    from main import detect_traffic_light_color

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    import cv2

    # Red circle (larger)
    cv2.circle(img, (30, 50), 20, (0, 0, 255), -1)
    # Yellow circle (smaller)
    cv2.circle(img, (70, 50), 5, (0, 255, 255), -1)

    color, confidence = detect_traffic_light_color(img, min_area=10)
    assert color == "red", f"Expected red (larger color), got '{color}'"
