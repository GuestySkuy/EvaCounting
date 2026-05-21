from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn
import threading
import logging
import cv2
import time
from pathlib import Path

logger = logging.getLogger("APIServer")

class FrameContainer:
    """Thread-safe container to hold the latest video frame."""
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()

    def set(self, frame):
        with self.lock:
            self.frame = frame.copy() if frame is not None else None

    def get(self):
        with self.lock:
            return self.frame

def create_app(db, counter, frame_container=None):
    app = FastAPI(
        title="People Counting API",
        description="API for real-time room occupancy monitoring",
        version="1.0.0"
    )

    # Enable CORS for local testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Endpoints
    @app.get("/api/occupancy")
    def get_occupancy():
        return {
            "current_occupancy": counter.current_occupancy,
            "total_in": counter.total_in,
            "total_out": counter.total_out
        }

    @app.get("/api/video_feed")
    def video_feed():
        if frame_container is None:
            raise HTTPException(status_code=404, detail="Video stream not enabled")

        def generate():
            try:
                while True:
                    frame = frame_container.get()
                    if frame is None:
                        time.sleep(0.04)
                        continue
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    if not ret:
                        time.sleep(0.04)
                        continue
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                    time.sleep(0.04)  # ~25 FPS
            except GeneratorExit:
                logger.debug("Video feed client disconnected")
            except Exception as e:
                logger.error(f"Error in video feed generator: {e}")

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/events")
    def get_events(limit: int = 20):
        return db.get_recent_events(limit=limit)

    @app.get("/api/summary")
    def get_summary():
        return db.get_hourly_summary()

    @app.post("/api/reset")
    def reset_counter():
        try:
            counter.reset()
            db.clear_data()
            # Save an initial 0 snapshot
            db.save_snapshot(0, 0, 0)
            return {"status": "success", "message": "Counters and database reset successfully"}
        except Exception as e:
            logger.error(f"Error resetting counters: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/health")
    def health_check():
        return {
            "status": "healthy",
            "db_path": str(db.db_path)
        }

    # Serve static frontend dashboard
    dashboard_path = Path(__file__).resolve().parent.parent / "dashboard"
    if dashboard_path.exists():
        app.mount("/static", StaticFiles(directory=str(dashboard_path)), name="static")
        
        @app.get("/")
        def serve_dashboard():
            return FileResponse(str(dashboard_path / "index.html"))
            
    return app

def start_api_server(db, counter, frame_container=None, host="0.0.0.0", port=8000):
    """Starts the FastAPI server in a background thread."""
    app = create_app(db, counter, frame_container=frame_container)
    
    # We disable uvicorn signal handlers so it doesn't hijack Ctrl+C from the main process loop
    config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    logger.info(f"API Server started at http://{host}:{port}/")
    return server
