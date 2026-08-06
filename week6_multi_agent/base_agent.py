"""
Agent基类 - 所有智能体的模板
"""

import sys
from pathlib import Path

# 把项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


class BaseAgent:
    """所有Agent的基类"""

    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.history = []

        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )

    def think(self, user_input: str, context: str = "") -> str:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        if context:
            messages.append({
                "role": "user",
                "content": f"【参考信息】\n{context}\n\n【当前任务】\n{user_input}"
            })
        else:
            messages.append({"role": "user", "content": user_input})

        for msg in self.history[-6:]:
            messages.append(msg)

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7
        )

        reply = response.choices[0].message.content
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": reply})

        return reply

    def clear_history(self):
        self.history = []