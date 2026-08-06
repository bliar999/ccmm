import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class ChatHistoryDB:
    """对话历史数据库管理"""

    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "chat_history.db"
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 对话会话表
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS conversations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
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

        # 消息表（每条消息单独存储）
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
                           NULL, -- user / assistant / system
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

        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")

        conn.commit()
        conn.close()

    def create_conversation(self, title: str = "新对话") -> int:
        """创建新对话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title,)
        )
        conv_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return conv_id

    def save_message(self, conversation_id: int, role: str, content: str):
        """保存一条消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        # 更新对话的消息数量和更新时间
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
        cursor.execute(
            "SELECT title FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "未命名对话"

    def update_conversation_title(self, conversation_id: int, title: str):
        """更新对话标题（可用AI自动生成）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        conn.commit()
        conn.close()

    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """获取所有对话列表（按更新时间倒序）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, created_at, updated_at, message_count
            FROM conversations
            ORDER BY updated_at DESC LIMIT ?
            """,
            (limit,)
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        conn.close()

    def get_all_messages_for_export(self, conversation_id: int) -> str:
        """导出对话为文本格式"""
        messages = self.get_conversation(conversation_id)
        lines = []
        for msg in messages:
            role_label = "👤 用户" if msg["role"] == "user" else "🤖 AI"
            lines.append(f"{role_label} ({msg['created_at']}):")
            lines.append(msg["content"])
            lines.append("")
        return "\n".join(lines)