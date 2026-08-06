"""
RAG极简版 - 无需下载任何模型
使用关键词匹配代替向量检索
"""

import sys
import os
from pathlib import Path
import re

# 确保项目根目录在路径中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# ==================== 加载文档 ====================
docs_dir = project_root / "week3_rag" / "docs"
docs_dir.mkdir(parents=True, exist_ok=True)

sample_file = docs_dir / "sample.txt"

# 如果文档不存在，创建示例
if not sample_file.exists():
    sample_content = """
人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
这些任务包括视觉感知、语音识别、决策制定和语言翻译等。

机器学习是AI的一个子集，它使系统能够从数据中学习并改进，而无需明确编程。

深度学习是机器学习的一个子集，使用多层神经网络来模拟人脑的工作方式。

大语言模型（LLM）如GPT和DeepSeek，是基于深度学习的自然语言处理模型。
它们通过海量文本训练，能够理解和生成人类语言。

RAG（检索增强生成）是一种将检索系统与生成模型结合的技术。
它先从外部知识库检索相关信息，再让大模型基于这些信息生成回答，
可以显著提高回答的准确性和时效性。

向量数据库是RAG系统中的核心组件，用于存储和检索文本的向量表示。
Chroma是一个轻量级的向量数据库，适合本地开发使用。
"""
    sample_file.write_text(sample_content, encoding="utf-8")

# 加载并分割文档
content = sample_file.read_text(encoding="utf-8")
chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
print(f"📄 加载 {len(chunks)} 个文档片段")


# ==================== 关键词匹配检索（无需模型） ====================
def keyword_search(query, top_k=3):
    """
    基于关键词匹配的检索
    提取问题中的关键词，在文档中匹配
    """
    # 提取关键词（去掉停用词，保留有意义的词）
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到",
                 "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "它", "他", "她", "们"}

    # 分词（简单中英文分割）
    words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', query)
    keywords = [w for w in words if w not in stopwords and len(w) > 1]

    # 如果没有关键词，直接返回前几个片段
    if not keywords:
        return [{"content": chunks[i], "score": 1.0 - i * 0.1} for i in range(min(top_k, len(chunks)))]

    # 计算每个片段的关键词匹配分数
    scores = []
    for chunk in chunks:
        score = 0
        for kw in keywords:
            # 统计关键词在片段中出现的次数
            count = chunk.count(kw)
            if count > 0:
                score += count * 2
            # 也检查是否包含同义词或相关词
            if kw in chunk:
                score += 1
        scores.append(score)

    # 按分数排序
    scored_chunks = list(zip(chunks, scores))
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    # 返回top_k结果
    results = []
    for i, (chunk, score) in enumerate(scored_chunks[:top_k]):
        if score > 0:
            results.append({"content": chunk, "score": float(score) / 10 if score > 0 else 0})
        else:
            # 如果没有匹配，返回前几个片段（保底）
            if i < len(chunks):
                results.append({"content": chunks[i], "score": 0.1})

    return results if results else [{"content": chunks[i], "score": 0.1} for i in range(min(top_k, len(chunks)))]


def search(query, top_k=3):
    """检索接口 - 与向量检索保持一致"""
    return keyword_search(query, top_k)


# ==================== RAG问答函数 ====================
def rag_ask(question):
    """基于检索结果回答问题"""
    if not chunks:
        return "知识库为空，请先上传文档"

    results = search(question, top_k=3)
    context = "\n\n".join([r["content"] for r in results])

    prompt = f"""
请根据以下参考内容回答用户的问题。如果参考内容中没有相关信息，请直接说"根据现有文档无法回答该问题"。

【参考内容】
{context}

【用户问题】
{question}

【回答】
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"调用大模型失败：{e}"


# ==================== 导出供其他模块使用 ====================
encode_texts = None
chunk_embeddings = None