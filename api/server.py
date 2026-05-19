from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import threading
import logging
from pathlib import Path

logger = logging.getLogger("APIServer")

def create_app(db, counter):
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

def start_api_server(db, counter, host="0.0.0.0", port=8000):
    """Starts the FastAPI server in a background thread."""
    app = create_app(db, counter)
    
    # We disable uvicorn signal handlers so it doesn't hijack Ctrl+C from the main process loop
    config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    logger.info(f"API Server started at http://{host}:{port}/")
    return server
