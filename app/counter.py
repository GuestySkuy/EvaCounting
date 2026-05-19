import numpy as np
import logging
from app.config import LINE_START, LINE_END

logger = logging.getLogger("Counter")

class LineCounter:
    def __init__(self, line_start=LINE_START, line_end=LINE_END, buffer_pixels=15):
        self.p1 = np.array(line_start, dtype=float)
        self.p2 = np.array(line_end, dtype=float)
        self.buffer = buffer_pixels
        
        # Line vector
        self.line_vec = self.p2 - self.p1
        self.line_len = np.linalg.norm(self.line_vec)
        
        # State tracking: track_id -> last known side (+1 for IN side, -1 for OUT side, 0 for buffer)
        self.track_states = {}
        
        # Overall stats
        self.total_in = 0
        self.total_out = 0
        
        logger.info(f"Line Counter initialized with line: {line_start} -> {line_end}")

    @property
    def current_occupancy(self):
        return max(0, self.total_in - self.total_out)

    def _get_side_and_distance(self, centroid):
        """
        Determines which side of the line the point is on and its distance.
        Side: +1 (IN side), -1 (OUT side), 0 (on the line)
        """
        c = np.array(centroid, dtype=float)
        
        # Cross product of line_vec and vector from p1 to centroid
        # cross = (p2.x - p1.x)*(c.y - p1.y) - (p2.y - p1.y)*(c.x - p1.x)
        cross = self.line_vec[0] * (c[1] - self.p1[1]) - self.line_vec[1] * (c[0] - self.p1[0])
        
        # Distance from point to line segment
        # dist = |cross| / line_len
        if self.line_len == 0:
            return 0, 0.0
            
        dist = abs(cross) / self.line_len
        side = 1 if cross > 0 else -1
        
        return side, dist

    def update(self, tracked_objects):
        """
        Updates the counter with the new tracking results for the current frame.
        tracked_objects: list of dicts from ObjectTracker
        Returns:
            list of dicts: list of crossing events in this frame [{'track_id': int, 'direction': str}]
        """
        events = []
        current_ids = set()

        for obj in tracked_objects:
            track_id = obj["track_id"]
            box = obj["box"]
            current_ids.add(track_id)
            
            # Calculate centroid of the bounding box
            centroid = [
                (box[0] + box[2]) / 2.0,
                (box[1] + box[3]) / 2.0
            ]
            
            side, dist = self._get_side_and_distance(centroid)
            
            # If the object is within the buffer zone, we don't change its state
            # but we initialize it if it's new and outside the buffer
            if track_id not in self.track_states:
                if dist > self.buffer:
                    self.track_states[track_id] = side
                else:
                    self.track_states[track_id] = 0  # In buffer
                continue
                
            prev_side = self.track_states[track_id]
            
            # We only transition state if we are firmly outside the buffer zone
            if dist > self.buffer:
                if prev_side == 0:
                    # Came out of the buffer, just initialize to the new side without counting
                    self.track_states[track_id] = side
                elif prev_side != side:
                    # Crossed!
                    direction = "IN" if side == 1 else "OUT"
                    if direction == "IN":
                        self.total_in += 1
                    else:
                        self.total_out += 1
                        
                    logger.info(f"Person #{track_id} crossed: {direction} (Total IN: {self.total_in}, OUT: {self.total_out})")
                    events.append({
                        "track_id": track_id,
                        "direction": direction,
                        "confidence": obj.get("confidence", 1.0)
                    })
                    self.track_states[track_id] = side

        # Clean up old track IDs that are no longer active to prevent memory growth
        # We keep them in states for a few frames to prevent re-detecting them with same ID,
        # but since tracker handles ID persistence, we can safely prune IDs not in the current frame.
        inactive_ids = set(self.track_states.keys()) - current_ids
        for inactive_id in inactive_ids:
            del self.track_states[inactive_id]

        return events
        
    def reset(self):
        self.total_in = 0
        self.total_out = 0
        self.track_states.clear()
        logger.info("Counter stats reset.")
