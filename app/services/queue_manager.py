import sqlite3
import os
import time
from pathlib import Path
from app.core import config

DB_PATH = config.EXEC_DIR / "messages.sqlite"

class QueueManager:
    def __init__(self):
        self.init_db()

    def init_db(self):
        global DB_PATH
        import sys
        import tempfile

        # Candidate paths
        paths_to_try = [
            DB_PATH, # Original (Exe folder)
            Path(os.getenv('APPDATA')) / "ControlWHA" / "messages.sqlite", # Roaming
            Path(os.getenv('LOCALAPPDATA')) / "ControlWHA" / "messages.sqlite", # Local
            Path(tempfile.gettempdir()) / "ControlWHA" / "messages.sqlite" # Temp
        ]

        for path_candidate in paths_to_try:
            try:
                msg_path = str(path_candidate)
                print(f"📁 Attempting Database Path: {msg_path}")
                
                # Ensure directory exists
                directory = os.path.dirname(msg_path)
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)

                # Try connecting
                conn = sqlite3.connect(msg_path)
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS message_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone TEXT NOT NULL,
                        message TEXT NOT NULL,
                        image_path TEXT,
                        status TEXT DEFAULT 'PENDING', -- PENDING, PROCESSING, SENT, ERROR
                        created_at REAL,
                        processed_at REAL,
                        error_msg TEXT
                    )
                ''')
                conn.commit()
                conn.close()
                
                # If success, update the global DB_PATH with the working one
                DB_PATH = path_candidate
                print(f"✅ Database initialized successfully at: {DB_PATH}")
                return # Exit success

            except Exception as e:
                print(f"⚠️ Failed to init DB at {path_candidate}: {e}")
                continue # Try next path

        # If all fail
        raise Exception("CRITICAL: Could not write database to ANY location (Exe, AppData, Temp). Check Permissions.")

    def add_message(self, phone, message, image_path=None):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute('''
            INSERT INTO message_queue (phone, message, image_path, status, created_at)
            VALUES (?, ?, ?, 'PENDING', ?)
        ''', (phone, message, image_path, time.time()))
        conn.commit()
        conn.close()
        print(f"📥 Cola: Mensaje guardado para {phone}")

    def get_next_pending(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Fetch one pending message, prioritizing oldest
        c.execute("SELECT * FROM message_queue WHERE status='PENDING' ORDER BY created_at ASC LIMIT 1")
        row = c.fetchone()
        
        data = None
        if row:
            data = dict(row)
            # Mark as processing immediately to avoid race conditions if multiple workers existed (though we have 1)
            c.execute("UPDATE message_queue SET status='PROCESSING' WHERE id=?", (data['id'],))
            conn.commit()
            
        conn.close()
        return data

    def mark_completed(self, msg_id, status='SENT', error=None):
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute('''
            UPDATE message_queue 
            SET status=?, processed_at=?, error_msg=?
            WHERE id=?
        ''', (status, time.time(), error, msg_id))
        conn.commit()
        conn.commit()
        conn.close()

    def check_duplicate(self, phone, current_message, exclude_id, threshold=0.9):
        """
        Check if a similar message was sent to this phone recently.
        Returns: (bool, reason)
        """
        try:
            import time
            
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # SIMPLIFIED RULE: Exact match + Same Phone + Less than 1 Minute ago
            # CRITICAL: Exclude the current message ID (because it's already in DB as PROCESSING)
            cutoff_time = time.time() - 60 
            
            c.execute('''
                SELECT message, created_at FROM message_queue 
                WHERE phone=? 
                AND id != ? 
                AND status IN ('SENT', 'PROCESSING')
                AND created_at > ?
                ORDER BY created_at DESC 
                LIMIT 5
            ''', (phone, exclude_id, cutoff_time))
            
            rows = c.fetchall()
            conn.close()

            # We don't use threshold anymore, just EXACT string equality
            for row in rows:
                prev_msg = row['message']
                time_ago = int(time.time() - row['created_at'])
                
                # EXACT MATCH CHECK
                if current_message.strip() == prev_msg.strip():
                    print(f" 🛑 DUPLICADO EXACTO detectado (Hace {time_ago}s)")
                    return True, f"Duplicado exacto hace {time_ago}s"

                print(f"   ✅ Mensaje diferente (Hace {time_ago}s)")
            
            return False, None
        except Exception as e:
            print(f"Error checking duplicate: {e}")
            return False, None

queue_manager = QueueManager()
