"""
待办事项管理器
"""

import sqlite3
from pathlib import Path
from typing import List, Dict


class TodoManager:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db_path = Path(__file__).parent.parent / "todos.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS todos
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           task
                           TEXT
                           NOT
                           NULL,
                           priority
                           TEXT
                           DEFAULT
                           'medium',
                           due_date
                           TEXT,
                           status
                           TEXT
                           DEFAULT
                           'pending',
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           completed_at
                           TIMESTAMP
                       )
                       """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_user ON todos(user_id)")
        conn.commit()
        conn.close()

    def add(self, task: str, priority: str = "medium", due_date: str = None) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (user_id, task, priority, due_date) VALUES (?, ?, ?, ?)",
            (self.user_id, task, priority, due_date)
        )
        conn.commit()
        todo_id = cursor.lastrowid
        conn.close()
        return {"id": todo_id, "task": task, "priority": priority, "status": "pending"}

    def list_todos(self, status: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT id, task, priority, due_date, status, created_at FROM todos WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                (self.user_id, status)
            )
        else:
            cursor.execute(
                "SELECT id, task, priority, due_date, status, created_at FROM todos WHERE user_id = ? ORDER BY created_at DESC",
                (self.user_id,)
            )
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "task": r[1], "priority": r[2], "due_date": r[3], "status": r[4], "created_at": r[5]} for r
                in rows]

    def complete(self, todo_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE todos SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (todo_id, self.user_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def delete(self, todo_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, self.user_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM todos WHERE user_id = ? AND status = 'pending'",
            (self.user_id,)
        )
        pending = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM todos WHERE user_id = ? AND status = 'completed'",
            (self.user_id,)
        )
        completed = cursor.fetchone()[0]
        conn.close()
        return {"pending": pending, "completed": completed, "total": pending + completed}