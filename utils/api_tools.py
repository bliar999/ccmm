"""
第三方API工具模块
统一管理：天气查询、网络搜索等
"""

import requests
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()


# ==================== 高德地图天气API ====================

def get_weather_amap(city: str) -> dict:
    """
    使用高德地图API查询天气

    参数:
        city: 城市名称，如"深圳"

    返回:
        天气信息字典
    """
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("AMAP_API_KEY")
        except:
            pass

    if not api_key:
        return {"error": "未配置高德API Key，请在.env或Secrets中设置 AMAP_API_KEY"}

    try:
        # 1. 根据城市名获取adcode
        geo_url = "https://restapi.amap.com/v3/geocode/geo"
        params = {"key": api_key, "address": city}
        resp = requests.get(geo_url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "1":
            return {"error": f"城市 '{city}' 不存在，请检查输入"}

        adcode = data["geocodes"][0]["adcode"]

        # 2. 查询天气
        weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {"key": api_key, "city": adcode, "extensions": "all"}
        resp = requests.get(weather_url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "1":
            return {"error": "天气查询失败，请稍后重试"}

        forecast = data["forecasts"][0]
        casts = forecast.get("casts", [])

        if not casts:
            return {"error": "暂无天气数据"}

        today = casts[0]
        tomorrow = casts[1] if len(casts) > 1 else None

        return {
            "city": forecast["city"],
            "adcode": adcode,
            "today": {
                "date": today.get("date", ""),
                "weather": today.get("dayweather", ""),
                "temperature": f"{today.get('nighttemp', '')}°C ~ {today.get('daytemp', '')}°C",
                "wind": today.get("daywind", ""),
                "daytemp": today.get("daytemp", ""),
                "nighttemp": today.get("nighttemp", ""),
                "dayweather": today.get("dayweather", ""),
                "nightweather": today.get("nightweather", "")
            },
            "tomorrow": {
                "date": tomorrow.get("date", ""),
                "weather": tomorrow.get("dayweather", ""),
                "temperature": f"{tomorrow.get('nighttemp', '')}°C ~ {tomorrow.get('daytemp', '')}°C",
                "wind": tomorrow.get("daywind", "")
            } if tomorrow else None,
            "forecast": casts
        }

    except requests.exceptions.Timeout:
        return {"error": "请求超时，请稍后重试"}
    except Exception as e:
        return {"error": f"查询失败：{str(e)}"}


# ==================== Tavily搜索API（稳定可靠） ====================

def search_tavily(query: str, max_results: int = 5) -> dict:
    """
    使用Tavily API进行稳定搜索

    参数:
        query: 搜索关键词
        max_results: 返回结果数量

    返回:
        搜索结果字典
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("TAVILY_API_KEY")
        except:
            pass

    if not api_key:
        # 降级到DuckDuckGo
        return search_duckduckgo(query, max_results)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results)

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "source": item.get("url", "")
            })

        return {
            "query": query,
            "results": results,
            "count": len(results),
            "source": "Tavily"
        }

    except ImportError:
        # tavily未安装，降级到DuckDuckGo
        return search_duckduckgo(query, max_results)
    except Exception as e:
        # 出错时降级到DuckDuckGo
        return search_duckduckgo(query, max_results)


# ==================== DuckDuckGo搜索API（备用/免费） ====================

def search_duckduckgo(query: str, max_results: int = 3) -> dict:
    """
    使用DuckDuckGo API搜索（免费备用）
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        results = []

        # 提取摘要
        if data.get("Abstract"):
            results.append({
                "title": "摘要",
                "content": data["Abstract"][:500],
                "source": data.get("AbstractURL", "")
            })

        # 提取相关主题
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:50],
                    "content": topic.get("Text", ""),
                    "source": topic.get("FirstURL", "")
                })

        if not results:
            results = [{
                "title": f"关于 '{query}' 的搜索结果",
                "content": f"搜索 '{query}' 的相关信息（来自DuckDuckGo）",
                "source": ""
            }]

        return {
            "query": query,
            "results": results[:max_results],
            "count": len(results),
            "source": "DuckDuckGo"
        }

    except Exception as e:
        return {
            "query": query,
            "error": f"搜索失败：{str(e)}",
            "results": [],
            "count": 0,
            "source": "Error"
        }


# ==================== 统一接口 ====================

def get_weather(city: str) -> dict:
    """统一天气查询接口"""
    return get_weather_amap(city)


def search(query: str, max_results: int = 5) -> dict:
    """统一搜索接口（优先Tavily，降级DuckDuckGo）"""
    return search_tavily(query, max_results)


# ==================== 工具描述（供Agent使用） ====================

def get_weather_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气和天气预报",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如：北京、上海、深圳"
                    }
                },
                "required": ["city"]
            }
        }
    }


def get_search_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "search",
            "description": "搜索网络上的最新信息，获取实时新闻、知识等",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认5",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }