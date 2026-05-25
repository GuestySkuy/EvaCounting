import sys
import os
import time
import argparse
import cv2
import logging
from pathlib import Path

# Add project root to path so we can import from app
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import (
    CAMERA_SOURCE, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS,
    CONFIDENCE_THRESHOLD, LINE_START, LINE_END, DB_PATH,
    FRAME_SKIP_INTERVAL, USE_ROI, ROI_BOX, ROI_X1, ROI_Y1, ROI_X2, ROI_Y2
)
from app.camera import VideoStream
from app.tracker import ObjectTracker
from app.counter import LineCounter
from app.database import DatabaseManager
from api.server import start_api_server, FrameContainer

# Setup Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Main")

def main():
    parser = argparse.ArgumentParser(description="Real-Time People Counting System")
    parser.add_argument("--source", type=str, default=str(CAMERA_SOURCE),
                        help=f"Camera source index or video file path (default: {CAMERA_SOURCE})")
    parser.add_argument("--headless", action="store_true",
                        help="Run without displaying OpenCV window (recommended for Raspberry Pi)")
    parser.add_argument("--reset-db", action="store_true",
                        help="Clear the database before starting")
    parser.add_argument("--with-api", action="store_true",
                        help="Start the FastAPI backend server in a background thread")
    args = parser.parse_args()

    # Parse camera source
    source = args.source
    if source.isdigit():
        source = int(source)

    logger.info("=== Starting People Counting System ===")
    logger.info(f"Source: {source} | Headless: {args.headless}")

    # Initialize Database
    db = DatabaseManager(DB_PATH)
    if args.reset_db:
        db.clear_data()
        logger.info("Database cleared as requested.")

    # Fetch latest count state from database to restore counts on restart
    stats = db.get_current_stats()
    logger.info(f"Restoring stats from database: IN={stats['total_in']}, OUT={stats['total_out']}")

    # Initialize Camera
    stream = VideoStream(
        source=source,
        width=CAMERA_WIDTH,
        height=CAMERA_HEIGHT,
        fps=CAMERA_FPS
    )
    
    try:
        stream.start()
    except Exception as e:
        logger.error(f"Failed to start camera: {e}")
        return

    # Let camera warm up and check stream stability
    time.sleep(1.0)
    grabbed, frame = stream.read()
    if not grabbed or frame is None:
        logger.error("Failed to retrieve frames from camera source. Exiting.")
        stream.stop()
        return

    # Initialize Tracker
    tracker = ObjectTracker(conf_threshold=CONFIDENCE_THRESHOLD)

    # Initialize Counter and restore counts
    counter = LineCounter(line_start=LINE_START, line_end=LINE_END, buffer_pixels=15)
    counter.total_in = stats["total_in"]
    counter.total_out = stats["total_out"]

    # Start API server if requested
    api_server = None
    frame_container = None
    if args.with_api:
        frame_container = FrameContainer()
        api_server = start_api_server(db, counter, frame_container=frame_container)

    # Timing and FPS variables
    prev_time = time.time()
    last_snapshot_time = time.time()
    snapshot_interval = 30  # seconds
    
    # Frame Skipping & Rolling FPS Average state
    frame_idx = 0
    last_tracked_objects = []
    fps_history = []
    max_fps_history_len = 30

    if not args.headless:
        cv2.namedWindow("People Counting System", cv2.WINDOW_NORMAL)

    logger.info("Pipeline started. Processing frames...")

    try:
        while True:
            grabbed, frame = stream.read()
            if not grabbed or frame is None:
                # If it's a video file, it loops automatically inside VideoStream.
                # If it's a webcam and fails, sleep and retry.
                time.sleep(0.01)
                continue

            frame_idx += 1

            # Step 1: Run Tracker (ByteTrack) with Frame Skipping and ROI
            if FRAME_SKIP_INTERVAL <= 1 or frame_idx == 1 or frame_idx % FRAME_SKIP_INTERVAL == 0:
                if USE_ROI and ROI_BOX is not None:
                    # Crop frame to ROI for faster inference
                    frame_roi = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
                    tracked_objects = tracker.track(frame_roi)
                    
                    # Shift coordinates back to original full frame space
                    for obj in tracked_objects:
                        x1, y1, x2, y2 = obj["box"]
                        obj["box"] = [x1 + ROI_X1, y1 + ROI_Y1, x2 + ROI_X1, y2 + ROI_Y1]
                else:
                    tracked_objects = tracker.track(frame)
                
                last_tracked_objects = tracked_objects
            else:
                # Reuse the tracking results from the last processed frame
                tracked_objects = [obj.copy() for obj in last_tracked_objects]

            # Step 2: Update real-time presence count + line crossing events
            counter.detected_count = len(tracked_objects)
            events = counter.update(tracked_objects)

            # Step 3: Log events to Database immediately
            for ev in events:
                db.log_crossing(
                    track_id=ev["track_id"],
                    direction=ev["direction"],
                    confidence=ev["confidence"]
                )

            # Step 4: Periodically save occupancy snapshot (every 30s)
            curr_time = time.time()
            if curr_time - last_snapshot_time >= snapshot_interval:
                db.save_snapshot(
                    total_in=counter.total_in,
                    total_out=counter.total_out,
                    current_occupancy=counter.current_occupancy
                )
                last_snapshot_time = curr_time
                logger.info(f"Occupancy Snapshot Saved: IN={counter.total_in} | OUT={counter.total_out} | CURRENT={counter.current_occupancy}")

            # Step 5: Render annotations and display/stream
            if not args.headless or args.with_api:
                # Calculate FPS with rolling average of latencies to get the true frame rate
                curr_time = time.time()
                time_diff = curr_time - prev_time
                prev_time = curr_time

                fps_history.append(time_diff)
                if len(fps_history) > max_fps_history_len:
                    fps_history.pop(0)

                total_time = sum(fps_history)
                fps = len(fps_history) / total_time if total_time > 0 else 0.0

                # Draw ROI border if active (Thin cyan box)
                if USE_ROI and ROI_BOX is not None:
                    rx1, ry1, rx2, ry2 = ROI_BOX
                    cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255, 255, 0), 1, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "ROI ACTIVE", (rx1 + 10, ry1 + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, lineType=cv2.LINE_AA)

                # Draw counting line (Red)
                cv2.line(frame, LINE_START, LINE_END, (0, 0, 255), 3)

                # Draw bounding boxes and IDs
                for obj in tracked_objects:
                    x1, y1, x2, y2 = obj["box"]
                    track_id = obj["track_id"]
                    
                    # Box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Centroid
                    cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
                    
                    # Label
                    cv2.putText(frame, f"ID: {track_id}", (x1, max(y1 - 10, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Overlay Statistics (Focusing only on CURRENT occupancy)
                overlay = frame.copy()
                cv2.rectangle(overlay, (10, 10), (240, 80), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                
                cv2.putText(frame, f"CURRENT: {counter.current_occupancy}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"FPS: {fps:.1f}", (20, 68),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

                # Update frame container for API stream
                if args.with_api and frame_container is not None:
                    frame_container.set(frame)

                # Display local OpenCV window if not headless
                if not args.headless:
                    cv2.imshow("People Counting System", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            else:
                # In headless mode, sleep slightly to prevent high CPU loop (YOLO tracking takes time, but this prevents spinning)
                time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Program interrupted by user.")
    finally:
        # Save final snapshot before exiting
        db.save_snapshot(
            total_in=counter.total_in,
            total_out=counter.total_out,
            current_occupancy=counter.current_occupancy
        )
        logger.info(f"Final occupancy snapshot saved: IN={counter.total_in} | OUT={counter.total_out}")
        
        # Stop streams
        stream.stop()
        if not args.headless:
            cv2.destroyAllWindows()
        logger.info("Cleanup completed. System shutdown.")

if __name__ == "__main__":
    main()
