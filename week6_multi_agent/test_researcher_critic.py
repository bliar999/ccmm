"""
测试研究员 + 批评家协作
"""

from researcher_agent import ResearcherAgent
from critic_agent import CriticAgent


def research_with_critique(question: str):
    """研究员研究 → 批评家评阅"""

    print("=" * 60)
    print(f"📌 问题: {question}")
    print("=" * 60)

    # 研究员分析
    researcher = ResearcherAgent()
    print("\n🔬 研究员分析中...")
    research_result = researcher.think(question)
    print(f"\n{research_result}")

    # 批评家评阅
    critic = CriticAgent()
    print("\n🔍 批评家评阅中...")
    critique = critic.think(
        f"请对以下研究结果进行评阅：\n{research_result}",
        context="这是研究员对用户问题的分析"
    )
    print(f"\n{critique}")

    return {
        "research": research_result,
        "critique": critique
    }


if __name__ == "__main__":
    result = research_with_critique("AI会取代人类工作吗？")