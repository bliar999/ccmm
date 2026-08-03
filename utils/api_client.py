from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

# 本地开发用.env
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


class DeepSeekClient:
    def __init__(self, api_key=None, base_url="https://api.deepseek.com/v1"):
        self.api_key = api_key

        # 如果没手动传入，尝试从环境变量读取（本地）
        if not self.api_key:
            self.api_key = os.getenv("DEEPSEEK_API_KEY")

        # 如果还没读到，尝试从Streamlit Secrets读取（云端）
        if not self.api_key:
            try:
                import streamlit as st
                # 重点：在函数内部导入st，避免启动时的初始化顺序问题
                secrets_key = st.secrets.get("DEEPSEEK_API_KEY")
                if secrets_key:
                    self.api_key = secrets_key
            except Exception:
                # 如果st.secrets不可用，静默跳过
                pass

        # 最后兜底
        if not self.api_key:
            raise ValueError("未找到API Key，请检查.env文件或者Streamlit Secrets")

        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

    def chat(self, prompt, system="你是一个乐于助人的助手",
             temperature=0.7, max_tokens=4096, stream=False):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        if stream:
            return response
        return response.choices[0].message.content

    def chat_with_history(self, messages, temperature=0.7):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content