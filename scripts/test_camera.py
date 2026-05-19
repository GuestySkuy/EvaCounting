import sys
import os
import time
import cv2
import argparse
import numpy as np
from pathlib import Path

# Add project root to path so we can import from app
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import CAMERA_SOURCE, CAMERA_WIDTH, CAMERA_HEIGHT, CONFIDENCE_THRESHOLD, LINE_START, LINE_END
from app.camera import VideoStream
from app.tracker import ObjectTracker
from app.detector import ObjectDetector
from app.counter import LineCounter

def main():
    parser = argparse.ArgumentParser(description="People Counting System - Camera, Detection, Tracking & Counting Test")
    parser.add_argument("--mode", choices=["detect", "track", "count"], default="detect", 
                        help="Run in detect, track, or count mode (default: detect)")
    parser.add_argument("--source", type=str, default=str(CAMERA_SOURCE),
                        help=f"Camera source index or video file path (default: {CAMERA_SOURCE})")
    args = parser.parse_args()

    # Parse camera source
    source = args.source
    if source.isdigit():
        source = int(source)

    print("=== People Counting System - Test Utility ===")
    print(f"Mode: {args.mode.upper()}")
    print(f"Camera Source: {source}")
    print(f"Resolution: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print(f"Confidence Threshold: {CONFIDENCE_THRESHOLD}")
    print("---------------------------------------------")

    # Initialize Video Stream
    stream = VideoStream(
        source=source, 
        width=CAMERA_WIDTH, 
        height=CAMERA_HEIGHT
    )
    
    try:
        stream.start()
    except Exception as e:
        print(f"Error starting video stream: {e}")
        return

    # Check if we can read frames
    time.sleep(1.0)  # Wait for camera to warm up
    grabbed, frame = stream.read()
    if not grabbed or frame is None:
        print("ERROR: Cannot read frames from camera. Check connections or camera source index.")
        stream.stop()
        return

    # Initialize requested module
    detector = None
    tracker = None
    counter = None
    
    if args.mode == "detect":
        detector = ObjectDetector(conf_threshold=CONFIDENCE_THRESHOLD)
    elif args.mode == "track":
        tracker = ObjectTracker(conf_threshold=CONFIDENCE_THRESHOLD)
    elif args.mode == "count":
        tracker = ObjectTracker(conf_threshold=CONFIDENCE_THRESHOLD)
        counter = LineCounter(line_start=LINE_START, line_end=LINE_END, buffer_pixels=15)

    prev_time = time.time()
    fps = 0

    print("Running. Press 'q' to quit.")
    
    # We check if GUI is available
    headless = False
    try:
        cv2.namedWindow("Test Window", cv2.WINDOW_NORMAL)
    except Exception:
        print("Headless environment detected. Outputting results to console instead of window.")
        headless = True

    try:
        while True:
            grabbed, frame = stream.read()
            if not grabbed or frame is None:
                print("Failed to get frame.")
                time.sleep(0.1)
                continue

            # Run Inference
            results = []
            if args.mode == "detect":
                results = detector.detect(frame)
            else:
                results = tracker.track(frame)

            # If counting mode, update counter
            if args.mode == "count":
                counter.update(results)

            # Calculate FPS
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time)
            prev_time = curr_time

            # Console output
            if args.mode == "count":
                print(f"FPS: {fps:.2f} | IN: {counter.total_in} | OUT: {counter.total_out} | CURRENT: {counter.current_occupancy}")
            else:
                print(f"FPS: {fps:.2f} | Count: {len(results)}")

            if not headless:
                # Draw visual line and buffer zone boundaries if counting mode
                if args.mode == "count":
                    # Draw Line
                    cv2.line(frame, LINE_START, LINE_END, (0, 0, 255), 3) # Red Line
                    
                    # Draw Buffer boundaries (optional but good for testing)
                    # For simplicity, if line is horizontal, buffer boundaries are y +- buffer
                    p1 = np.array(LINE_START)
                    p2 = np.array(LINE_END)
                    line_vec = p2 - p1
                    line_len = np.linalg.norm(line_vec)
                    if line_len > 0:
                        # Normal vector to the line
                        normal_vec = np.array([-line_vec[1], line_vec[0]]) / line_len
                        offset = normal_vec * 15 # buffer size
                        
                        # Draw parallel lines
                        cv2.line(frame, tuple((p1 + offset).astype(int)), tuple((p2 + offset).astype(int)), (255, 0, 0), 1)
                        cv2.line(frame, tuple((p1 - offset).astype(int)), tuple((p2 - offset).astype(int)), (255, 0, 0), 1)

                # Draw on frame for visual display
                for res in results:
                    x1, y1, x2, y2 = res['box']
                    conf = res['confidence']
                    
                    # Draw Bounding Box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw Centroid
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
                    
                    # Draw Label
                    if args.mode in ["track", "count"]:
                        track_id = res['track_id']
                        label = f"ID: {track_id} ({conf:.2f})"
                    else:
                        label = f"Person: {conf:.2f}"
                        
                    cv2.putText(frame, label, (x1, max(y1 - 10, 15)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Draw Stats Overlay
                if args.mode == "count":
                    # Semi-transparent background for stats
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (10, 10), (220, 120), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                    
                    cv2.putText(frame, f"IN: {counter.total_in}", (20, 35), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"OUT: {counter.total_out}", (20, 65), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(frame, f"CURRENT: {counter.current_occupancy}", (20, 95), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 112), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                else:
                    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # Show frame
                cv2.imshow("Test Window", frame)
                
                # Check for 'q' key to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Add a sleep to prevent console flooding in headless mode
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nExiting program...")
    finally:
        stream.stop()
        if not headless:
            cv2.destroyAllWindows()
        print("Cleanup completed.")

if __name__ == "__main__":
    main()
