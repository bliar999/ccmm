"""
工作流编排 - 顺序执行多个Agent任务
"""

from base_agent import BaseAgent
from researcher_agent import ResearcherAgent
from critic_agent import CriticAgent


class WorkflowOrchestrator:
    """
    工作流编排器

    支持：顺序执行、条件分支、结果汇总
    """

    def __init__(self):
        self.steps = []
        self.results = {}

    def add_step(self, agent, task: str, depends_on: list = None):
        """
        添加工作流步骤

        参数:
            agent: Agent实例
            task: 任务描述
            depends_on: 依赖的前置步骤名称列表
        """
        step_name = f"step_{len(self.steps)}"
        self.steps.append({
            "name": step_name,
            "agent": agent,
            "task": task,
            "depends_on": depends_on or [],
            "result": None
        })
        return step_name

    def run(self, initial_input: str) -> dict:
        """
        执行工作流
        """
        print("=" * 60)
        print("🚀 工作流执行开始")
        print(f"📌 输入: {initial_input}")
        print("=" * 60)

        # 按顺序执行
        for step in self.steps:
            print(f"\n▶️ 执行步骤: {step['name']}")
            print(f"   Agent: {step['agent'].name}")
            print(f"   任务: {step['task']}")

            # 收集依赖的输出
            context = ""
            for dep in step["depends_on"]:
                if dep in self.results:
                    context += f"\n[{dep}的结果]\n{self.results[dep]}\n"

            # 执行
            result = step["agent"].think(
                step["task"],
                context=context
            )

            step["result"] = result
            self.results[step["name"]] = result

            print(f"   ✅ 完成")

        # 汇总所有结果
        summary = self._generate_summary(initial_input)

        return {
            "steps": self.steps,
            "results": self.results,
            "summary": summary
        }

    def _generate_summary(self, initial_input: str) -> str:
        """生成最终汇总"""
        summary_prompt = f"""
请基于以下工作流执行结果，生成一个完整的回答。

【原始问题】
{initial_input}

【各步骤结果】
{chr(10).join([f"- {step['name']}: {step['result'][:100]}..." for step in self.steps])}

请整合以上信息，给用户一个完整、清晰的回答。
"""
        summary_agent = BaseAgent(
            name="汇总员",
            role="工作流结果汇总",
            system_prompt="你是一个善于整合信息的汇总员。"
        )
        return summary_agent.think(summary_prompt)


# ==================== 测试 ====================
if __name__ == "__main__":
    # 创建工作流
    workflow = WorkflowOrchestrator()

    # 添加步骤
    researcher = ResearcherAgent()
    critic = CriticAgent()

    workflow.add_step(
        researcher,
        "请深入研究这个问题：远程办公对团队协作的影响"
    )

    workflow.add_step(
        critic,
        "请评阅研究员的结果，指出漏洞和不足",
        depends_on=["step_0"]
    )

    # 执行
    result = workflow.run("远程办公会影响团队协作效率吗？")

    print("\n" + "=" * 60)
    print("📊 最终结果")
    print("=" * 60)
    print(result["summary"])