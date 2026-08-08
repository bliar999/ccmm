"""
缓存管理模块 - 减少重复API调用，提升响应速度
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any


class CacheManager:
    """本地缓存管理（使用SQLite，无需额外安装Redis）"""

    def __init__(self, cache_days: int = 7):
        self.db_path = Path(__file__).parent.parent / "cache.db"
        self.cache_days = cache_days
        self._init_db()

    def _init_db(self):
        """初始化缓存数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS cache
                       (
                           key
                           TEXT
                           PRIMARY
                           KEY,
                           value
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           expires_at
                           TIMESTAMP
                       )
                       """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
        conn.commit()
        conn.close()

    def _get_key(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        """生成缓存键"""
        text = f"{system}|{prompt}|{temperature}"
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, prompt: str, system: str = "", temperature: float = 0.7) -> Optional[str]:
        """获取缓存"""
        key = self._get_key(prompt, system, temperature)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM cache WHERE key = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
            (key,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
        return None

    def set(self, prompt: str, system: str = "", temperature: float = 0.7, value: str = "") -> None:
        """设置缓存"""
        key = self._get_key(prompt, system, temperature)
        expires_at = datetime.now() + timedelta(days=self.cache_days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, value, expires_at.isoformat())
        )
        conn.commit()
        conn.close()

    def clear(self) -> None:
        """清空所有缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache")
        conn.commit()
        conn.close()

    def clear_expired(self) -> None:
        """清除过期缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache WHERE expires_at < CURRENT_TIMESTAMP")
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cache WHERE expires_at < CURRENT_TIMESTAMP")
        expired = cursor.fetchone()[0]
        conn.close()

        return {
            "total": total,
            "expired": expired,
            "valid": total - expired
        }