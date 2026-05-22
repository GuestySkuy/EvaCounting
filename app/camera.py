import cv2
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Camera")

class VideoStream:
    def __init__(self, source=0, width=640, height=480, fps=30):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap = None
        self.frame = None
        self.grabbed = False
        self.started = False
        self.read_lock = threading.Lock()
        self.thread = None

    def start(self):
        if self.started:
            logger.warning("Stream already started.")
            return self
            
        logger.info(f"Connecting to camera source: {self.source}")
        self.cap = cv2.VideoCapture(self.source)
        
        # Only set properties if source is a webcam index (integer)
        if isinstance(self.source, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            # Limit buffer size to 1 frame to prevent queue accumulation delay (lag)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Read back actual resolution
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Camera initialized with resolution: {self.width}x{self.height}")
        else:
            # Video file
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Video file opened with resolution: {self.width}x{self.height}")

        self.grabbed, self.frame = self.cap.read()
        if not self.grabbed:
            logger.error("Failed to read initial frame from camera source.")
            return self
            
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            grabbed, frame = self.cap.read()
            
            # If we are reading a video file and reach the end, reset to the beginning for continuous loop (useful for testing)
            if not grabbed:
                if not isinstance(self.source, int):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    logger.error("Camera disconnected or lost connection.")
                    self.started = False
                    break
                    
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame
                
            # Sleep timing optimization:
            # For live webcam, cap.read() blocks at the hardware level, so we sleep minimal (1ms) to keep the buffer flushed and delay at 0.
            # For video files, we sleep according to the FPS to maintain accurate playback speed.
            if isinstance(self.source, int):
                time.sleep(0.001)
            else:
                time.sleep(1 / self.fps)

    def read(self):
        with self.read_lock:
            if self.frame is None:
                return False, None
            return self.grabbed, self.frame.copy()

    def stop(self):
        logger.info("Stopping camera stream...")
        self.started = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        logger.info("Camera stream stopped.")
        
    def __del__(self):
        self.stop()
