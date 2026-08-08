"""
对话历史数据库管理 - 支持多用户隔离
"""

import sqlite3
from pathlib import Path
from typing import List, Dict


class ChatHistoryDB:
    def __init__(self, user_id: int = None):
        """
        初始化数据库

        参数:
            user_id: 用户ID，用于数据隔离（None表示使用默认）
        """
        self.db_path = Path(__file__).parent.parent / "chat_history.db"
        self.user_id = user_id
        self._init_db()

    def _init_db(self):
        """初始化数据库表（增加 user_id 字段）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 对话会话表 - 增加 user_id
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS conversations
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
                           title
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           updated_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           message_count
                           INTEGER
                           DEFAULT
                           0
                       )
                       """)

        # 消息表
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS messages
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           conversation_id
                           INTEGER
                           NOT
                           NULL,
                           role
                           TEXT
                           NOT
                           NULL,
                           content
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           conversation_id
                       ) REFERENCES conversations
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")

        # 检查是否需要迁移旧数据（增加 user_id 列）
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in cursor.fetchall()]
        if "user_id" not in columns:
            # 添加 user_id 列，默认值为 1
            cursor.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER DEFAULT 1")
            # 更新已有数据
            cursor.execute("UPDATE conversations SET user_id = 1 WHERE user_id IS NULL")

        conn.commit()
        conn.close()

    def create_conversation(self, title: str = "新对话") -> int:
        """创建新对话（关联当前用户）"""
        if self.user_id is None:
            raise ValueError("未设置 user_id，无法创建对话")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (self.user_id, title)
        )
        conv_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return conv_id

    def save_message(self, conversation_id: int, role: str, content: str):
        """保存消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        cursor.execute(
            "UPDATE conversations SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        conn.commit()
        conn.close()

    def get_conversation(self, conversation_id: int) -> List[Dict]:
        """获取某个对话的所有消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1], "created_at": row[2]} for row in rows]

    def get_conversation_title(self, conversation_id: int) -> str:
        """获取对话标题"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "未命名对话"

    def update_conversation_title(self, conversation_id: int, title: str):
        """更新对话标题"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        conn.commit()
        conn.close()

    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """获取当前用户的所有对话列表（按更新时间倒序）"""
        if self.user_id is None:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, created_at, updated_at, message_count
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (self.user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "message_count": row[4]
            }
            for row in rows
        ]

    def delete_conversation(self, conversation_id: int):
        """删除对话（级联删除消息）"""
        # 先验证该对话属于当前用户
        if self.user_id is not None:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row and row[0] != self.user_id:
                raise PermissionError("无权删除其他用户的对话")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        conn.close()

    def get_user_id(self) -> int:
        """获取当前用户ID"""
        return self.user_id