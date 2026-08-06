"""
监督者Agent - 任务分配和协调
"""

from .base_agent import BaseAgent
from .researcher_agent import ResearcherAgent
from .critic_agent import CriticAgent


class SupervisorAgent(BaseAgent):
    """监督者：负责分配任务、协调团队"""

    def __init__(self):
        system_prompt = """
你是莉莉团队的【监督者】。

你的职责：
1. 接收用户的任务
2. 将任务拆解成子任务
3. 分配给合适的团队成员（研究员、批评家等）
4. 汇总各成员的输出，形成最终回答

你的团队成员：
- 研究员：负责信息收集和分析
- 批评家：负责质疑和完善

工作流程：
1. 分析任务 → 决定需要哪些成员参与
2. 分配任务 → 给每个成员明确的指令
3. 汇总结果 → 整合成完整的回答
"""
        super().__init__(
            name="监督者",
            role="任务分配与协调",
            system_prompt=system_prompt
        )

    def orchestrate(self, question: str) -> dict:
        """
        编排团队工作

        返回:
            包含各成员输出的字典
        """
        print(f"\n👔 监督者收到任务: {question}")
        print("-" * 40)

        # 1. 分析任务，决定分配策略
        analysis = self.think(
            f"请分析这个任务，告诉我需要哪些团队成员参与：\n{question}"
        )
        print(f"📋 任务分析: {analysis}\n")

        # 2. 分配任务给研究员
        print("🔬 分配任务给研究员...")
        researcher = ResearcherAgent()
        research_result = researcher.think(question)
        print(f"✅ 研究员完成\n")

        # 3. 分配任务给批评家
        print("🔍 分配任务给批评家...")
        critic = CriticAgent()
        critique = critic.think(
            f"请评阅以下研究结果：\n{research_result}"
        )
        print(f"✅ 批评家完成\n")

        # 4. 汇总结果
        print("📊 监督者汇总中...")
        summary = self.think(
            f"""
请基于以下信息，生成一个完整的回答：

【研究员的发现】
{research_result}

【批评家的建议】
{critique}

【用户原始问题】
{question}

请整合以上信息，给出一个全面、平衡的回答。
"""
        )

        return {
            "analysis": analysis,
            "research": research_result,
            "critique": critique,
            "final_answer": summary
        }


# ==================== 测试 ====================
if __name__ == "__main__":
    supervisor = SupervisorAgent()

    result = supervisor.orchestrate(
        "远程办公会不会影响团队协作效率？"
    )

    print("\n" + "=" * 60)
    print("📌 最终回答")
    print("=" * 60)
    print(result["final_answer"])