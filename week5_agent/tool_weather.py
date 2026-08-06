"""
工具1：模拟天气查询（演示Function Calling流程）
"""

import json
from datetime import datetime
import random


# ==================== 工具函数 ====================
def get_weather(city: str, date: str = "今天") -> dict:
    """
    模拟查询天气

    参数:
        city: 城市名称
        date: 日期（今天/明天/后天）

    返回:
        天气信息字典
    """
    # 模拟天气数据
    weather_types = ["晴天☀️", "多云⛅", "小雨🌧️", "大雪❄️", "雾霾😷"]
    temperatures = list(range(-5, 36))

    return {
        "city": city,
        "date": date,
        "weather": random.choice(weather_types),
        "temperature": random.choice(temperatures),
        "humidity": random.randint(30, 90),
        "wind": random.choice(["微风", "3-4级", "5-6级", "大风"]),
        "tips": "出门注意安全" if random.random() > 0.5 else "适合户外活动"
    }


# ==================== 工具描述（给大模型看的说明书） ====================
def get_tool_description():
    """返回工具的描述，用于Function Calling"""
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息，包括温度、湿度、风力等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如：北京、上海、深圳"
                    },
                    "date": {
                        "type": "string",
                        "description": "查询日期，可选值：今天、明天、后天，默认为今天",
                        "enum": ["今天", "明天", "后天"]
                    }
                },
                "required": ["city"]
            }
        }
    }


# ==================== 测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🌤️ 天气工具测试")
    print("=" * 50)

    result = get_weather("深圳", "今天")
    print(f"深圳今天天气：{result['weather']}，温度{result['temperature']}°C")