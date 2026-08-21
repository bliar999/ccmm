"""
DeepSeek API 客户端封装（支持流式输出）
"""

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os
import streamlit as st

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


class DeepSeekClient:
    def __init__(self, api_key=None, base_url="https://api.deepseek.com/v1"):
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            if not self.api_key:
                try:
                    self.api_key = st.secrets.get("DEEPSEEK_API_KEY")
                except:
                    pass

        if not self.api_key:
            raise ValueError("未找到API Key，请检查.env文件或者Streamlit Secrets")

        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

    def chat(self, prompt, system="你是一个乐于助人的助手", temperature=0.7, max_tokens=4096):
        """单轮对话"""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def chat_with_history(self, messages, temperature=0.7):
        """多轮对话（带历史）"""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

    def chat_stream(self, messages, temperature=0.7):
        """
        流式输出 - 逐字返回，模拟打字效果

        使用方式：
            for chunk in client.chat_stream(messages):
                print(chunk, end="")
        """
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content