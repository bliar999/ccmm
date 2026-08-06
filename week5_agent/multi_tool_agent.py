"""
多工具协同 - Agent自主决定调用多个工具
"""

from react_agent import react_agent

# 复杂问题测试 - 需要多个工具协同
complex_questions = [
    "现在是几点？帮我算一下8小时后是几点？",
    "搜索一下今天的新闻，然后告诉我如果有关于AI的新闻就总结一下",
    "深圳现在的天气怎么样？适合出门吗？",
]

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 多工具协同测试")
    print("=" * 60)

    for q in complex_questions:
        print("\n" + "=" * 60)
        print(f"📌 问题: {q}")
        print("=" * 60)
        react_agent(q, max_steps=5)