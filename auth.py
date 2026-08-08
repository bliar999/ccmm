# auth.py - 用户认证模块
import hashlib
import secrets
from pathlib import Path
import sqlite3
import streamlit as st


class AuthSystem:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "users.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           username
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           password_hash
                           TEXT
                           NOT
                           NULL,
                           salt
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           last_login
                           TIMESTAMP
                       )
                       """)
        conn.commit()
        conn.close()

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return hash_obj.hexdigest(), salt

    def register(self, username: str, password: str) -> bool:
        try:
            password_hash, salt = self._hash_password(password)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, password_hash, salt)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username: str, password: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return False
        password_hash, salt = row
        input_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        if input_hash == password_hash:
            # 更新最后登录时间
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            conn.commit()
            conn.close()
            return True
        return False

    def user_exists(self, username: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def get_user_id(self, username: str) -> int:
        """根据用户名获取用户ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None