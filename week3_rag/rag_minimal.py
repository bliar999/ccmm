"""
RAG最简版 - 绕过sentence_transformers版本冲突
使用transformers库直接加载模型
"""

from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import time

# ==================== 第一步：加载Embedding模型 ====================
print("🚀 加载Embedding模型...")
start = time.time()

# 使用国产模型，国内直连
model_name = "BAAI/bge-small-zh-v1.5"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

print(f"✅ 模型加载完成，耗时 {time.time() - start:.1f} 秒\n")


# ==================== 第二步：定义Embedding函数 ====================
def encode_texts(texts):
    """将文本列表转换为向量"""
    # 分词
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )

    # 推理
    with torch.no_grad():
        outputs = model(**inputs)

    # 取平均池化作为句子向量
    embeddings = outputs.last_hidden_state.mean(dim=1).numpy()

    # 归一化
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms

    return embeddings


# ==================== 第三步：准备示例文档 ====================
docs_dir = Path("docs")
docs_dir.mkdir(exist_ok=True)

sample_file = docs_dir / "sample.txt"
if not sample_file.exists():
    print("📝 生成示例文档...")
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
"""
    sample_file.write_text(sample_content, encoding="utf-8")
    print(f"✅ 已生成: {sample_file}\n")

# ==================== 第四步：加载并分割文档 ====================
print("📄 加载文档...")
content = sample_file.read_text(encoding="utf-8")

# 简单分割：按空行分段
chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
print(f"✅ 分割成 {len(chunks)} 个片段\n")

# ==================== 第五步：向量化并建立索引 ====================
print("🔢 向量化文档...")
chunk_embeddings = encode_texts(chunks)
print(f"✅ 向量维度: {chunk_embeddings.shape}\n")


# ==================== 第六步：检索函数 ====================
def search(query, top_k=3):
    """检索最相关的文档片段"""
    query_embedding = encode_texts([query])
    similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append({
            "content": chunks[idx],
            "score": float(similarities[idx])
        })
    return results


# ==================== 第七步：RAG问答 ====================
def rag_ask(question):
    """基于检索结果回答问题"""
    # 1. 检索相关片段
    results = search(question, top_k=3)
    context = "\n\n".join([r["content"] for r in results])

    # 2. 调用DeepSeek
    from openai import OpenAI
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1"
    )

    prompt = f"""
请根据以下参考内容回答用户的问题。如果参考内容中没有相关信息，请直接说"根据现有文档无法回答该问题"。

【参考内容】
{context}

【用户问题】
{question}

【回答】
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content


# ==================== 运行测试 ====================
print("=" * 60)
print("🔍 检索测试")
print("=" * 60)

test_questions = [
    "什么是人工智能？",
    "RAG是什么技术？",
]

for q in test_questions:
    print(f"\n📌 问题: {q}")
    results = search(q, top_k=2)
    for i, r in enumerate(results):
        print(f"  [{i + 1}] (相似度: {r['score']:.3f}) {r['content'][:50]}...")

print("\n" + "=" * 60)
print("💬 RAG问答测试")
print("=" * 60)

questions = [
    "什么是人工智能？",
    "RAG技术有什么作用？",
    "今天天气怎么样？"
]

for q in questions:
    print(f"\n📌 问题: {q}")
    print("-" * 40)
    answer = rag_ask(q)
    print(f"🤖 {answer}")

print("\n✅ 完成！")