# feedback_manager.py

import sqlite3
from datetime import datetime

class FeedbackManager:
    def __init__(self, db_name="feedback_history.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_name TEXT,
                    rating INTEGER,
                    category TEXT,
                    comment TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def save_feedback(self, user_name, rating, category, comment):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO feedback (timestamp, user_name, rating, category, comment)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, user_name, rating, category, comment))
            conn.commit()
        finally:
            conn.close()