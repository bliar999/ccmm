"""
对话式RAG - 支持多轮对话和上下文记忆
"""

import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from rag_minimal import search, chunks

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)


class DialogueRAG:
    def __init__(self):
        self.history = []  # 对话历史
        self.context = ""  # 当前上下文

    def ask(self, question):
        """带上下文的问答"""
        # 1. 检索相关文档
        results = search(question, top_k=3)
        context = "\n\n".join([r["content"] for r in results])

        # 2. 构建提示词（包含历史对话）
        history_text = ""
        if self.history:
            history_text = "\n".join([
                f"{'用户' if h['role'] == 'user' else '助手'}: {h['content']}"
                for h in self.history[-6:]  # 最近3轮
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

        # 3. 调用大模型
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        answer = response.choices[0].message.content

        # 4. 记录历史
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})

        return answer

    def clear(self):
        """清空历史"""
        self.history = []


# 测试
if __name__ == "__main__":
    rag = DialogueRAG()

    print("=" * 60)
    print("💬 对话式RAG测试")
    print("=" * 60)

    # 多轮对话
    questions = [
        "什么是人工智能？",
        "它有哪些应用场景？",  # 这里的"它"指代上一轮的人工智能
        "那深度学习呢？"  # 这里的"那"指代上下文
    ]

    for q in questions:
        print(f"\n👤 用户: {q}")
        answer = rag.ask(q)
        print(f"🤖 助手: {answer}")

    print("\n" + "=" * 60)
    print("✅ 对话式RAG测试完成")
    print("=" * 60)