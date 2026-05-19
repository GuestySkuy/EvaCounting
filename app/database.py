import sqlite3
import os
import logging
from datetime import datetime
from app.config import DB_PATH

logger = logging.getLogger("Database")

class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """Returns a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        # Enable dictionary-like access to rows
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the database, creating tables if they do not exist."""
        logger.info(f"Initializing SQLite database at: {self.db_path}")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Table for individual crossing events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crossing_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id INTEGER NOT NULL,
                    direction TEXT CHECK(direction IN ('IN', 'OUT')) NOT NULL,
                    confidence REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table for periodic occupancy snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS occupancy_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_in INTEGER NOT NULL,
                    total_out INTEGER NOT NULL,
                    current_occupancy INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        logger.info("Database tables initialized successfully.")

    def log_crossing(self, track_id, direction, confidence=1.0):
        """Logs a single crossing event to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO crossing_events (track_id, direction, confidence, timestamp) VALUES (?, ?, ?, ?)",
                    (track_id, direction, confidence, datetime.now().isoformat())
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging crossing: {e}")

    def save_snapshot(self, total_in, total_out, current_occupancy):
        """Saves a snapshot of current counter stats."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO occupancy_snapshots (total_in, total_out, current_occupancy, timestamp) VALUES (?, ?, ?, ?)",
                    (total_in, total_out, current_occupancy, datetime.now().isoformat())
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving snapshot: {e}")

    def get_current_stats(self):
        """
        Fetches the latest counts.
        Falls back to 0s if no records are found.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Get the latest snapshot
                cursor.execute("SELECT total_in, total_out, current_occupancy FROM occupancy_snapshots ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    return {
                        "total_in": row["total_in"],
                        "total_out": row["total_out"],
                        "current_occupancy": row["current_occupancy"]
                    }
                else:
                    # If no snapshot, sum up events
                    cursor.execute("SELECT COUNT(*) as count FROM crossing_events WHERE direction = 'IN'")
                    ins = cursor.fetchone()["count"]
                    cursor.execute("SELECT COUNT(*) as count FROM crossing_events WHERE direction = 'OUT'")
                    outs = cursor.fetchone()["count"]
                    return {
                        "total_in": ins,
                        "total_out": outs,
                        "current_occupancy": max(0, ins - outs)
                    }
        except sqlite3.Error as e:
            logger.error(f"Error fetching current stats: {e}")
            return {"total_in": 0, "total_out": 0, "current_occupancy": 0}

    def get_recent_events(self, limit=10):
        """Retrieves the most recent crossing events."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT track_id, direction, confidence, timestamp FROM crossing_events ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error fetching recent events: {e}")
            return []

    def get_hourly_summary(self):
        """
        Aggregates IN/OUT events grouped by hour for the current day.
        Returns:
            list of dicts: [{'hour': str, 'in': int, 'out': int}]
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # We group by hour for today's date
                cursor.execute("""
                    SELECT 
                        strftime('%H:00', timestamp) as hour,
                        SUM(CASE WHEN direction = 'IN' THEN 1 ELSE 0 END) as ins,
                        SUM(CASE WHEN direction = 'OUT' THEN 1 ELSE 0 END) as outs
                    FROM crossing_events
                    WHERE date(timestamp) = date('now', 'localtime')
                    GROUP BY hour
                    ORDER BY hour ASC
                """)
                rows = cursor.fetchall()
                return [{"hour": row["hour"], "in": row["ins"], "out": row["outs"]} for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error fetching hourly summary: {e}")
            return []

    def clear_data(self):
        """Resets the database by clearing all tables."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM crossing_events")
                cursor.execute("DELETE FROM occupancy_snapshots")
                conn.commit()
            logger.info("Database cleared.")
        except sqlite3.Error as e:
            logger.error(f"Error clearing database: {e}")
