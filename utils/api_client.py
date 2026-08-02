from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

# 加载环境变量（向上两级到项目根目录）
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


class APIClient:
    """DeepSeek API的通用客户端封装"""

    def __init__(self, api_key=None, base_url="https://api.deepseek.com/v1"):
        if api_key:
            self.api_key = api_key
        else:
            try:
                import streamlit as st
                self.api_key = st.secrets["DEEPSEEK_API_KEY"]
            except Exception:
                self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("API 缺少: 请填写密钥，或配置.env文件/Streamlit Secrets")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

    def chat(self, prompt, system="你是一个乐于助人的助手",
             temperature=0.7, max_tokens=4096, stream=False):
        """
        通用的对话方法

        参数:
            prompt: 用户输入
            system: 系统提示词
            temperature: 随机性 (0-2)
            max_tokens: 最大输出长度
            stream: 是否流式输出
        """
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
            return response  # 返回生成器对象
        return response.choices[0].message.content

    def chat_with_history(self, messages, temperature=0.7):
        """
        支持多轮对话历史

        参数:
            messages: 完整消息列表 [{"role": "user/assistant/system", "content": "..."}]
        """
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content