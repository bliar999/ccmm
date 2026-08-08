"""
成本监控模块 - 记录Token消耗和费用
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional


class CostMonitor:
    """Token消耗和成本监控"""

    # DeepSeek 价格（每百万tokens）
    PRICES = {
        "input": 1.0,  # 输入 ￥1/百万tokens
        "output": 2.0,  # 输出 ￥2/百万tokens
    }

    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.db_path = Path(__file__).parent.parent / "cost_logs.db"
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS usage_logs
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER,
                           session_id
                           TEXT,
                           model
                           TEXT,
                           input_tokens
                           INTEGER,
                           output_tokens
                           INTEGER,
                           total_tokens
                           INTEGER,
                           input_cost
                           REAL,
                           output_cost
                           REAL,
                           total_cost
                           REAL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       """)
        cursor.execute("""
                       CREATE INDEX IF NOT EXISTS idx_usage_user_date
                           ON usage_logs(user_id, created_at)
                       """)
        conn.commit()
        conn.close()

    def log_usage(
            self,
            input_tokens: int,
            output_tokens: int,
            model: str = "deepseek-chat",
            session_id: str = None
    ) -> None:
        """记录一次使用"""
        input_cost = (input_tokens / 1_000_000) * self.PRICES["input"]
        output_cost = (output_tokens / 1_000_000) * self.PRICES["output"]
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO usage_logs
                       (user_id, session_id, model, input_tokens, output_tokens, total_tokens,
                        input_cost, output_cost, total_cost)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       """, (
                           self.user_id,
                           session_id or "default",
                           model,
                           input_tokens,
                           output_tokens,
                           total_tokens,
                           input_cost,
                           output_cost,
                           total_cost
                       ))
        conn.commit()
        conn.close()

    def get_today_usage(self) -> Dict:
        """获取今日用量统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT COALESCE(SUM(input_tokens), 0),
                              COALESCE(SUM(output_tokens), 0),
                              COALESCE(SUM(total_tokens), 0),
                              COALESCE(SUM(input_cost), 0),
                              COALESCE(SUM(output_cost), 0),
                              COALESCE(SUM(total_cost), 0),
                              COUNT(*)
                       FROM usage_logs
                       WHERE user_id = ? AND DATE (created_at) = DATE ('now')
                       """, (self.user_id,))
        row = cursor.fetchone()
        conn.close()

        return {
            "input_tokens": int(row[0]),
            "output_tokens": int(row[1]),
            "total_tokens": int(row[2]),
            "input_cost": round(row[3], 4),
            "output_cost": round(row[4], 4),
            "total_cost": round(row[5], 4),
            "call_count": row[6]
        }

    def get_weekly_usage(self) -> Dict:
        """获取本周用量统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT COALESCE(SUM(input_tokens), 0),
                              COALESCE(SUM(output_tokens), 0),
                              COALESCE(SUM(total_tokens), 0),
                              COALESCE(SUM(total_cost), 0),
                              COUNT(*)
                       FROM usage_logs
                       WHERE user_id = ?
                         AND created_at >= DATE ('now'
                           , '-7 days')
                       """, (self.user_id,))
        row = cursor.fetchone()
        conn.close()

        return {
            "input_tokens": int(row[0]),
            "output_tokens": int(row[1]),
            "total_tokens": int(row[2]),
            "total_cost": round(row[3], 4),
            "call_count": row[4]
        }

    def get_monthly_usage(self) -> Dict:
        """获取本月用量统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT COALESCE(SUM(input_tokens), 0),
                              COALESCE(SUM(output_tokens), 0),
                              COALESCE(SUM(total_tokens), 0),
                              COALESCE(SUM(total_cost), 0),
                              COUNT(*)
                       FROM usage_logs
                       WHERE user_id = ?
                         AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                       """, (self.user_id,))
        row = cursor.fetchone()
        conn.close()

        return {
            "input_tokens": int(row[0]),
            "output_tokens": int(row[1]),
            "total_tokens": int(row[2]),
            "total_cost": round(row[3], 4),
            "call_count": row[4]
        }

    def get_all_time_usage(self) -> Dict:
        """获取总用量统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT COALESCE(SUM(input_tokens), 0),
                              COALESCE(SUM(output_tokens), 0),
                              COALESCE(SUM(total_tokens), 0),
                              COALESCE(SUM(total_cost), 0),
                              COUNT(*)
                       FROM usage_logs
                       WHERE user_id = ?
                       """, (self.user_id,))
        row = cursor.fetchone()
        conn.close()

        return {
            "input_tokens": int(row[0]),
            "output_tokens": int(row[1]),
            "total_tokens": int(row[2]),
            "total_cost": round(row[3], 4),
            "call_count": row[4]
        }

    def get_daily_trend(self, days: int = 7) -> List[Dict]:
        """获取最近N天的每日趋势"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT
                           DATE (created_at) as date, COALESCE (SUM (total_tokens), 0) as tokens, COALESCE (SUM (total_cost), 0) as cost, COUNT (*) as calls
                       FROM usage_logs
                       WHERE user_id = ? AND created_at >= DATE ('now', ?)
                       GROUP BY DATE (created_at)
                       ORDER BY date DESC
                       """, (self.user_id, f'-{days} days'))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "date": row[0],
                "tokens": int(row[1]),
                "cost": round(row[2], 4),
                "calls": row[3]
            }
            for row in rows
        ]

    def format_cost(self, cost: float) -> str:
        """格式化费用显示"""
        if cost < 0.01:
            return "< 0.01"
        return f"{cost:.4f}"

    def format_tokens(self, tokens: int) -> str:
        """格式化Token数量"""
        if tokens < 1000:
            return f"{tokens}"
        elif tokens < 1000000:
            return f"{tokens / 1000:.1f}K"
        else:
            return f"{tokens / 1000000:.2f}M"

    def get_daily_budget(self) -> Dict:
        """获取每日预算状态（默认日预算¥0.1）"""
        today = self.get_today_usage()
        daily_budget = 0.1  # 每日预算 0.1 元

        return {
            "budget": daily_budget,
            "used": today["total_cost"],
            "remaining": max(0, daily_budget - today["total_cost"]),
            "percentage": min(100, (today["total_cost"] / daily_budget) * 100)
        }