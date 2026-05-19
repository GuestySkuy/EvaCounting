from ultralytics import YOLO
import logging
from app.config import MODEL_PATH, INFERENCE_SIZE, CONFIDENCE_THRESHOLD, TARGET_CLASSES

logger = logging.getLogger("Detector")

class ObjectDetector:
    def __init__(self, model_path=MODEL_PATH, conf_threshold=CONFIDENCE_THRESHOLD):
        logger.info(f"Loading YOLO model from: {model_path}")
        self.model = YOLO(model_path)
        self.conf = conf_threshold
        self.imgsz = INFERENCE_SIZE
        self.classes = TARGET_CLASSES
        logger.info("YOLO model loaded successfully.")

    def detect(self, frame):
        """
        Runs YOLO inference on a single frame.
        Returns:
            list of dicts: [{'box': [x1, y1, x2, y2], 'conf': float, 'class': int}]
        """
        results = self.model.predict(
            source=frame,
            conf=self.conf,
            imgsz=self.imgsz,
            classes=self.classes,
            verbose=False
        )
        
        detections = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            for box in boxes:
                # Get bounding box coordinates in xyxy format
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                conf = float(box.conf[0].cpu().item())
                cls_id = int(box.cls[0].cpu().item())
                
                detections.append({
                    "box": [int(x) for x in xyxy],
                    "confidence": conf,
                    "class_id": cls_id
                })
                
        return detections
