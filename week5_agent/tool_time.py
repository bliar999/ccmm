"""
工具2：获取当前时间
"""

from datetime import datetime
import pytz


# ==================== 工具函数 ====================
def get_current_time(timezone: str = "Asia/Shanghai", format_type: str = "full") -> dict:
    """
    获取当前时间

    参数:
        timezone: 时区，如 Asia/Shanghai, America/New_York
        format_type: 格式类型，full(完整)/date(日期)/time(时间)

    返回:
        时间信息字典
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    formats = {
        "full": now.strftime("%Y年%m月%d日 %H:%M:%S %Z"),
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M:%S")
    }

    return {
        "timezone": timezone,
        "timestamp": now.isoformat(),
        "formatted": formats.get(format_type, formats["full"]),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "weekday": ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    }


# ==================== 工具描述 ====================
def get_tool_description():
    return {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间，支持不同时区和格式",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区，默认 Asia/Shanghai",
                        "default": "Asia/Shanghai"
                    },
                    "format_type": {
                        "type": "string",
                        "description": "输出格式：full(完整)/date(日期)/time(时间)",
                        "enum": ["full", "date", "time"],
                        "default": "full"
                    }
                }
            }
        }
    }


# ==================== 测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🕐 时间工具测试")
    print("=" * 50)

    result = get_current_time()
    print(f"当前时间：{result['formatted']}")
    print(f"星期：{result['weekday']}")