"""
工具4：网络搜索（使用免费DuckDuckGo API）
"""

import requests
from bs4 import BeautifulSoup
import time


# ==================== 工具函数 ====================
def web_search(query: str, max_results: int = 3) -> dict:
    """
    搜索网络信息

    参数:
        query: 搜索关键词
        max_results: 返回结果数量

    返回:
        搜索结果列表
    """
    try:
        # 使用DuckDuckGo的免费API
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
            # 如果没结果，返回模拟数据
            results = [{
                "title": f"关于 '{query}' 的搜索结果",
                "content": f"搜索 '{query}' 的相关信息。由于API限制，返回模拟结果。",
                "source": ""
            }]

        return {
            "query": query,
            "results": results[:max_results],
            "count": len(results)
        }

    except Exception as e:
        return {
            "query": query,
            "error": f"搜索失败：{str(e)}",
            "results": []
        }


# ==================== 工具描述 ====================
def get_tool_description():
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索网络上的最新信息，用于回答需要实时信息的问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认3",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    }


# ==================== 测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🔍 搜索工具测试")
    print("=" * 50)

    result = web_search("人工智能最新进展")
    print(f"搜索 '{result['query']}'")
    for r in result["results"]:
        print(f"- {r['title'][:50]}")