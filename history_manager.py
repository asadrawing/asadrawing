# history_manager.py (Optimerad Enterprise-version med SQLite)
import sqlite3
import json
from datetime import datetime

class DrawingHistoryManager:
    def __init__(self, db_name="inspection_history.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    drawing_name TEXT,
                    revision TEXT,
                    timestamp TEXT,
                    issues TEXT,
                    pdf_report TEXT,
                    compliance TEXT,
                    notes TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def save_inspection(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], dict):
            record = args[0]
            project_id = record.get("project_id", "PROJ-001")
            drawing_name = record.get("drawing_name", "drawing.pdf")
            revision = record.get("revision", "Rev.A")
            timestamp = record.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            issues = json.dumps(record.get("issues", []), ensure_ascii=False)
            pdf_report = record.get("pdf_report", "")
        else:
            project_id = args[0] if len(args) > 0 else kwargs.get("project_id", "PROJ-001")
            drawing_name = args[1] if len(args) > 1 else kwargs.get("drawing_name", "drawing.pdf")
            revision = args[2] if len(args) > 2 else kwargs.get("revision", "Rev.A")
            issues = json.dumps(args[3] if len(args) > 3 else kwargs.get("issues", []), ensure_ascii=False)
            pdf_report = args[4] if len(args) > 4 else kwargs.get("pdf_report", "")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO inspections (project_id, drawing_name, revision, timestamp, issues, pdf_report, compliance, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, drawing_name, revision, timestamp, issues, pdf_report, "", ""))
            conn.commit()
        finally:
            conn.close()

    def get_all_inspections(self):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, project_id, drawing_name, revision, timestamp, issues, pdf_report, compliance, notes FROM inspections ORDER BY id DESC')
            rows = cursor.fetchall()
            formatted_rows = []
            for r in rows:
                issues_data = r[5]
                if isinstance(issues_data, str):
                    try:
                        issues_data = json.loads(issues_data)
                    except:
                        issues_data = []
                formatted_rows.append((r[0], r[1], r[2], r[3], r[4], issues_data, r[6], r[7], r[8]))
            return formatted_rows
        finally:
            conn.close()