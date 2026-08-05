"""
RAG系统评估脚本
加载评估集，批量测试，计算准确率
"""

import json
from pathlib import Path
from rag_minimal import rag_ask  # 使用第三周最简版


def load_eval_data():
    """加载评估集"""
    eval_path = Path(__file__).parent / "eval_data.json"
    with open(eval_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate():
    """运行评估"""
    eval_data = load_eval_data()

    print("=" * 60)
    print("📊 RAG系统评估")
    print(f"评估集大小: {len(eval_data)} 条")
    print("=" * 60)

    results = []
    correct = 0

    for i, item in enumerate(eval_data, 1):
        question = item["question"]
        expected = item["answer"]

        print(f"\n[{i}/{len(eval_data)}] 问题: {question}")

        # 调用RAG
        try:
            actual = rag_ask(question)
        except Exception as e:
            print(f"  ❌ 出错: {e}")
            actual = ""

        # 简单判断：如果回答包含期望答案的关键词（简化版）
        # 更准确的方法是用LLM判断，但这里用关键词匹配做演示
        keywords = expected[:20]  # 取期望答案的前20个字作为关键词
        is_correct = keywords in actual if actual else False

        if is_correct:
            correct += 1
            print(f"  ✅ 正确")
        else:
            print(f"  ❌ 错误")
            print(f"  期望: {expected[:50]}...")
            print(f"  实际: {actual[:50]}...")

        results.append({
            "question": question,
            "expected": expected,
            "actual": actual,
            "correct": is_correct
        })

    # 统计结果
    accuracy = correct / len(eval_data) if eval_data else 0

    print("\n" + "=" * 60)
    print("📊 评估结果")
    print(f"  正确数: {correct}/{len(eval_data)}")
    print(f"  准确率: {accuracy:.2%}")
    print("=" * 60)

    # 保存详细结果
    result_path = Path(__file__).parent / "eval_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": accuracy,
            "details": results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n📁 详细结果已保存: {result_path}")

    return accuracy, results


if __name__ == "__main__":
    evaluate()