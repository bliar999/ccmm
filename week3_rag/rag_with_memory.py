"""
对话式RAG - 使用关键词匹配
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from openai import OpenAI
from dotenv import load_dotenv
from week3_rag.rag_minimal import search, chunks

load_dotenv(dotenv_path=project_root / ".env")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)


class DialogueRAG:
    def __init__(self):
        self.history = []

    def ask(self, question):
        if not chunks:
            return "知识库为空，请先上传文档"

        results = search(question, top_k=3)
        context = "\n\n".join([r["content"] for r in results])

        history_text = ""
        if self.history:
            history_text = "\n".join([
                f"{'用户' if h['role'] == 'user' else '助手'}: {h['content']}"
                for h in self.history[-6:]
            ])

        prompt = f"""
你是一个基于文档的问答助手。请根据【参考内容】回答用户的问题。

【参考内容】
{context}

【对话历史】
{history_text}

【当前问题】
{question}

【回答】
"""

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            answer = response.choices[0].message.content
            self.history.append({"role": "user", "content": question})
            self.history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            return f"调用大模型失败：{e}"

    def clear(self):
        self.history = []