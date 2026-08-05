"""
重排序（Rerank）演示
提升检索精度
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from rag_minimal import encode_texts, chunks, chunk_embeddings, search


def rerank(query, results, top_k=5):
    """
    对检索结果进行重排序
    使用更精细的相似度计算
    """
    query_emb = encode_texts([query])

    # 计算更精细的相似度
    scores = []
    for r in results:
        # 这里可以用更复杂的模型，演示用简单方法
        chunk_emb = encode_texts([r["content"]])
        score = cosine_similarity(query_emb, chunk_emb)[0][0]
        scores.append(score)

    # 重新排序
    sorted_indices = np.argsort(scores)[::-1]
    reranked = []
    for idx in sorted_indices[:top_k]:
        results[idx]["rerank_score"] = float(scores[idx])
        reranked.append(results[idx])

    return reranked


def search_with_rerank(query, top_k=5):
    """带重排序的检索"""
    # 先检索更多
    results = search(query, top_k=10)
    # 重排序
    reranked = rerank(query, results, top_k=top_k)
    return reranked


# 测试对比
print("=" * 60)
print("🔄 检索 vs 重排序 对比")
print("=" * 60)

test_query = "什么是深度学习？"

print(f"\n📌 问题: {test_query}\n")

print("【普通检索 top-3】")
results = search(test_query, top_k=3)
for i, r in enumerate(results):
    print(f"  [{i + 1}] {r['content'][:40]}... (score: {r['score']:.3f})")

print("\n【重排序 top-3】")
reranked = search_with_rerank(test_query, top_k=3)
for i, r in enumerate(reranked):
    print(f"  [{i + 1}] {r['content'][:40]}... (rerank: {r.get('rerank_score', 0):.3f})")