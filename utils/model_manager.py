"""
多模型管理器 - 简化版（仅 DeepSeek）
"""

import os
import streamlit as st
from openai import OpenAI
from typing import List, Dict, Optional


class ModelManager:
    """模型管理器 - 当前仅 DeepSeek"""

    MODELS = {
        "deepseek-chat": {
            "name": "DeepSeek Chat",
            "provider": "deepseek",
            "icon": "🔵",
            "description": "性价比高，中文能力强",
            "api_type": "openai",
            "base_url": "https://api.deepseek.com/v1",
            "env_key": "DEEPSEEK_API_KEY"
        }
    }

    @classmethod
    def get_available_models(cls) -> List[str]:
        available = []
        for model_id, config in cls.MODELS.items():
            key_name = config["env_key"]
            api_key = os.getenv(key_name)
            if not api_key and hasattr(st, 'secrets'):
                try:
                    api_key = st.secrets.get(key_name)
                except:
                    pass
            if api_key:
                available.append(model_id)
        return available

    @classmethod
    def get_model_info(cls, model_id: str) -> Optional[Dict]:
        return cls.MODELS.get(model_id)

    @classmethod
    def get_client(cls, model_id: str) -> Optional[OpenAI]:
        config = cls.MODELS.get(model_id)
        if not config:
            return None

        key_name = config["env_key"]
        api_key = os.getenv(key_name)
        if not api_key and hasattr(st, 'secrets'):
            try:
                api_key = st.secrets.get(key_name)
            except:
                pass

        if not api_key:
            return None

        return OpenAI(api_key=api_key, base_url=config["base_url"])

    @classmethod
    def chat(cls, model_id: str, messages: List[Dict], temperature: float = 0.7) -> Dict:
        config = cls.MODELS.get(model_id)
        if not config:
            return {"success": False, "error": f"未知模型: {model_id}"}

        client = cls.get_client(model_id)
        if not client:
            return {
                "success": False,
                "error": f"❌ {config['name']} 未配置 API Key"
            }

        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature
            )
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {"success": False, "error": f"⚠️ 调用失败：{str(e)}"}