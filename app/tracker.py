from ultralytics import YOLO
import logging
from app.config import MODEL_PATH, INFERENCE_SIZE, CONFIDENCE_THRESHOLD, TARGET_CLASSES, TRACKER_TYPE

logger = logging.getLogger("Tracker")

class ObjectTracker:
    def __init__(self, model_path=MODEL_PATH, conf_threshold=CONFIDENCE_THRESHOLD, tracker_type=TRACKER_TYPE):
        logger.info(f"Loading YOLO model for tracking from: {model_path}")
        self.model = YOLO(model_path)
        self.conf = conf_threshold
        self.imgsz = INFERENCE_SIZE
        self.classes = TARGET_CLASSES
        self.tracker_type = tracker_type
        logger.info(f"YOLO tracker initialized with tracker type: {self.tracker_type}")

    def track(self, frame):
        """
        Runs YOLO tracking on a single frame.
        Returns:
            list of dicts: [{'box': [x1, y1, x2, y2], 'track_id': int, 'confidence': float, 'class_id': int}]
        """
        # We run model.track which handles detection + tracking (ByteTrack or BoT-SORT)
        # persist=True maintains IDs across frames
        results = self.model.track(
            source=frame,
            persist=True,
            conf=self.conf,
            imgsz=self.imgsz,
            classes=self.classes,
            tracker=self.tracker_type,
            verbose=False
        )
        
        tracked_objects = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            
            # If nothing is tracked or no boxes exist, return empty list
            if boxes is None or len(boxes) == 0:
                return tracked_objects
                
            for box in boxes:
                # Check if this box has a tracking ID (might be None in the first frames or if lost)
                if box.id is None:
                    continue
                    
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                track_id = int(box.id[0].cpu().item())
                conf = float(box.conf[0].cpu().item())
                cls_id = int(box.cls[0].cpu().item())
                
                tracked_objects.append({
                    "box": [int(x) for x in xyxy],
                    "track_id": track_id,
                    "confidence": conf,
                    "class_id": cls_id
                })
                
        return tracked_objects
