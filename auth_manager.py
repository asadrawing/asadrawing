# auth_manager.py

import sqlite3
import hashlib

class AuthManager:
    def __init__(self, db_name="users_db.db"):
        self.db_name = db_name
        self._init_db()

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            ''')
            cursor.execute('SELECT COUNT(*) FROM users')
            if cursor.fetchone()[0] == 0:
                default_users = [
                    ("admin", self._hash_password("admin123"), "Ahmad Almasmoum", "Admin"),
                    ("inkop", self._hash_password("inkop123"), "Inköpsansvarig", "Inköp"),
                    ("beredare", self._hash_password("bered123"), "CNC Beredare", "Beredare"),
                    ("qc_chef", self._hash_password("qc123"), "Kvalitetschef", "Kvalitetschef")
                ]
                cursor.executemany('INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)', default_users)
                conn.commit()
        finally:
            conn.close()

    def authenticate(self, username, password):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            pwd_hash = self._hash_password(password)
            cursor.execute('SELECT username, full_name, role FROM users WHERE username = ? AND password_hash = ?', (username, pwd_hash))
            user = cursor.fetchone()
            if user:
                return {"username": user[0], "full_name": user[1], "role": user[2]}
            return None
        finally:
            conn.close()

    def update_password(self, username, new_password):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            new_pwd_hash = self._hash_password(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (new_pwd_hash, username))
            conn.commit()
        finally:
            conn.close()