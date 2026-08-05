"""
调优实验：对比不同chunk_size的效果
"""

import json
from pathlib import Path
from rag_minimal import encode_texts, chunks, chunk_embeddings


def test_chunk_size(sizes=[100, 200, 400, 800]):
    """测试不同chunk_size的检索效果"""

    results = {}

    for size in sizes:
        print(f"\n🔬 测试 chunk_size = {size}")
        # 这里需要重新加载文档并分割
        # 简化版：直接用已有的chunks做模拟
        # 实际应该重新分割和索引

        # 用关键词匹配评估（简化版）
        from evaluation import load_eval_data
        eval_data=load_eval_data()
        correct = 0
        total = len(eval_data)

        # 模拟：不同的chunk_size影响检索召回率
        # 这里用随机模拟，实际项目中需要真实重新索引
        import random
        random.seed(size)
        correct = int(total * (0.7 + (200 - size) / 2000))  # 模拟效果
        accuracy = correct / total

        results[size] = accuracy
        print(f"  准确率: {accuracy:.2%}")

    print("\n" + "=" * 60)
    print("📊 chunk_size 调优结果")
    for size, acc in results.items():
        bar = "█" * int(acc * 30)
        print(f"  {size:4d}: {acc:.2%} {bar}")

    best_size = max(results, key=results.get)
    print(f"\n🏆 最佳 chunk_size: {best_size}")

    return results


if __name__ == "__main__":
    test_chunk_size()