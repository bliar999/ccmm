"""
ReAct Agent - 推理 + 行动循环
"""

import json
import sys
from pathlib import Path

# 把项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from dotenv import load_dotenv
import os

# 导入工具（注意路径：同级目录直接用 from .xxx import）
from .tool_time import get_current_time, get_tool_description as time_desc
from .tool_calculator import calculate, get_tool_description as calc_desc
from .tool_search import web_search, get_tool_description as search_desc

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# ==================== 工具注册表 ====================
TOOLS = {
    "get_current_time": {
        "function": get_current_time,
        "description": time_desc()
    },
    "calculate": {
        "function": calculate,
        "description": calc_desc()
    },
    "web_search": {
        "function": web_search,
        "description": search_desc()
    }
}


def get_tools_schema():
    return [TOOLS[name]["description"] for name in TOOLS]


def execute_tool(tool_name: str, arguments: dict):
    if tool_name not in TOOLS:
        return {"error": f"未知工具: {tool_name}"}
    try:
        result = TOOLS[tool_name]["function"](**arguments)
        return result
    except Exception as e:
        return {"error": f"工具执行失败: {str(e)}"}


# ==================== 导出给外部使用 ====================
def react_agent(question: str, max_steps: int = 3):
    """
    单 Agent 主循环（供 apps 调用）
    """
    messages = [
        {"role": "system", "content": """
你是莉莉，一个智能助手。你能调用工具来帮助回答问题。
当用户需要实时信息、计算、或搜索时，使用相应的工具。
每次调用工具后，根据观察结果决定是继续调用工具还是给出最终答案。
回复时要友好、自然，像和朋友聊天一样。
"""},
        {"role": "user", "content": question}
    ]

    step = 0
    while step < max_steps:
        step += 1

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=get_tools_schema(),
            tool_choice="auto",
            temperature=0.3
        )

        assistant_message = response.choices[0].message

        # 检查是否有工具调用
        if assistant_message.tool_calls:
            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_name, arguments)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
        else:
            return assistant_message.content

    return "抱歉，我思考太久了，请换个问题试试。"


# ==================== 测试 ====================
if __name__ == "__main__":
    print(react_agent("现在几点了？"))