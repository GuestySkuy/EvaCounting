import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "counting.db"

# Camera Settings
# Can be an integer (webcam index, e.g., 0 or 1) or a string (video file path)
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
if CAMERA_SOURCE.isdigit():
    CAMERA_SOURCE = int(CAMERA_SOURCE)

CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", 640))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", 480))
CAMERA_FPS = int(os.getenv("CAMERA_FPS", 30))

# Inference Settings
NCNN_MODEL_NEW = BASE_DIR / "models" / "yolo11n_ncnn_model"
NCNN_MODEL_STD = BASE_DIR / "models" / "yolo11n_ncnn"
PT_MODEL_PATH = BASE_DIR / "models" / "yolo11n.pt"

if NCNN_MODEL_NEW.exists() and NCNN_MODEL_NEW.is_dir():
    DEFAULT_MODEL_PATH = str(NCNN_MODEL_NEW)
elif NCNN_MODEL_STD.exists() and NCNN_MODEL_STD.is_dir():
    DEFAULT_MODEL_PATH = str(NCNN_MODEL_STD)
else:
    DEFAULT_MODEL_PATH = str(PT_MODEL_PATH)

MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
INFERENCE_SIZE = int(os.getenv("INFERENCE_SIZE", 320))  # 320 is lighter for RPi, 640 is standard
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.4))
TARGET_CLASSES = [0]  # 0 is 'person' in COCO dataset

# Tracking Settings
TRACKER_TYPE = os.getenv("TRACKER_TYPE", "bytetrack.yaml")  # bytetrack.yaml or botsort.yaml

# Counting Line Settings (Vertical line in the middle, top to bottom)
# Line is defined by two points: (x1, y1) to (x2, y2)
# To make Left-to-Right = IN, we start from bottom and go to top.
LINE_START = (int(CAMERA_WIDTH / 2), CAMERA_HEIGHT)
LINE_END = (int(CAMERA_WIDTH / 2), 0)
LINE_DIRECTION = "vertical"  # horizontal (up/down) or vertical (left/right)

