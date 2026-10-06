"""ML model inference wrapper (optional).

Provides a conservative wrapper around an object detector (YOLOv8 via
`ultralytics`) and exposes a simple `detect(frame)` API that returns a
list of detections with label, confidence, and bbox.

This module is optional: if `ultralytics` isn't installed, the wrapper will
log a warning and provide an empty detection list. To enable real ML
inference install `ultralytics`:

    python -m pip install ultralytics

"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    _HAS_ULTRALYTICS = True
except Exception:
    YOLO = None
    _HAS_ULTRALYTICS = False


class ModelDetector:
    def __init__(self, model_path: str | None = None, device: str = 'cpu'):
        """Lazy-load a YOLO model. If `model_path` is None it will try to use
        the default COCO-pretrained model shipped with ultralytics.
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self._loaded = False

    def load(self) -> None:
        if not _HAS_ULTRALYTICS:
            logger.warning("ultralytics not installed; ML detection disabled")
            return
        if self._loaded:
            return
        try:
            if self.model_path:
                self.model = YOLO(self.model_path)
            else:
                # Using 'yolov8n.pt' name relies on ultralytics package data; if
                # not available an explicit model path should be provided.
                self.model = YOLO('yolov8n.pt')
            self.model.fuse()  # opportunistic optimization
            self._loaded = True
            logger.info("ML model loaded (device=%s)", self.device)
        except Exception as e:
            logger.exception("Failed to load model: %s", e)
            self.model = None
            self._loaded = False

    def detect(self, frame, conf: float = 0.3) -> List[Dict]:
        """Detect objects in `frame`.

        Returns a list of dicts with keys: label (str), conf (float), bbox ([x1,y1,x2,y2]).
        """
        if not _HAS_ULTRALYTICS:
            return []
        if not self._loaded:
            self.load()
        if not self.model:
            return []

        try:
            results = self.model(frame, conf=conf)
            detections = []
            # ultralytics returns a list of Results for each image (we pass 1)
            if len(results) > 0:
                r = results[0]
                boxes = r.boxes
                for box in boxes:
                    xyxy = box.xyxy[0].tolist()  # [x1,y1,x2,y2]
                    score = float(box.conf[0])
                    cls = int(box.cls[0])
                    label = r.names.get(cls, str(cls)) if hasattr(
                        r, 'names') else str(cls)
                    detections.append({
                        'label': label,
                        'conf': score,
                        'bbox': [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])]
                    })
            return detections
        except Exception:
            logger.exception("Model inference failed")
            return []


# Single shared detector for convenience
_shared_detector: ModelDetector | None = None


def get_detector(model_path: str | None = None, device: str = 'cpu') -> ModelDetector:
    global _shared_detector
    if _shared_detector is None:
        _shared_detector = ModelDetector(model_path=model_path, device=device)
    return _shared_detector
