"""
辩论模式 - 两个Agent来回讨论
"""

from base_agent import BaseAgent


class ProAgent(BaseAgent):
    """正方：支持某个观点"""

    def __init__(self, topic: str):
        system_prompt = f"""
你是莉莉团队中的【正方辩手】。

你的立场是支持：{topic}

你的职责：
1. 用事实和逻辑支持你的立场
2. 反驳反方的质疑
3. 保持理性辩论，不人身攻击
"""
        super().__init__(
            name="正方",
            role=f"支持 {topic}",
            system_prompt=system_prompt
        )


class ConAgent(BaseAgent):
    """反方：反对某个观点"""

    def __init__(self, topic: str):
        system_prompt = f"""
你是莉莉团队中的【反方辩手】。

你的立场是反对：{topic}

你的职责：
1. 用事实和逻辑质疑正方立场
2. 提出反例和替代方案
3. 保持理性辩论，不人身攻击
"""
        super().__init__(
            name="反方",
            role=f"反对 {topic}",
            system_prompt=system_prompt
        )


def debate(topic: str, rounds: int = 3):
    """
    执行辩论

    参数:
        topic: 辩论主题
        rounds: 辩论回合数
    """
    print("=" * 60)
    print(f"🎯 辩论主题: {topic}")
    print("=" * 60)

    pro = ProAgent(topic)
    con = ConAgent(topic)

    # 辩论历史
    pro_history = []
    con_history = []

    # 开场陈词
    print("\n🔵 正方开场...")
    pro_opening = pro.think(f"请为你的立场陈述开场观点：{topic}")
    print(f"正方: {pro_opening[:200]}...")
    pro_history.append(pro_opening)

    print("\n🔴 反方开场...")
    con_opening = con.think(f"请为你的立场陈述开场观点：{topic}")
    print(f"反方: {con_opening[:200]}...")
    con_history.append(con_opening)

    # 多轮辩论
    for i in range(rounds):
        print(f"\n{'=' * 40}")
        print(f"⚡ 第 {i + 1} 轮辩论")
        print(f"{'=' * 40}")

        # 正方回应
        print("\n🔵 正方回应...")
        pro_response = pro.think(
            f"反方说了：{con_history[-1]}\n请回应并补充你的论点。"
        )
        print(f"正方: {pro_response[:200]}...")
        pro_history.append(pro_response)

        # 反方回应
        print("\n🔴 反方回应...")
        con_response = con.think(
            f"正方说了：{pro_history[-1]}\n请回应并补充你的论点。"
        )
        print(f"反方: {con_response[:200]}...")
        con_history.append(con_response)

    # 总结
    print("\n" + "=" * 60)
    print("📊 辩论总结")
    print("=" * 60)

    # 用监督者做总结
    from supervisor_agent import SupervisorAgent
    supervisor = SupervisorAgent()

    summary = supervisor.think(
        f"""
请总结以下辩论：

辩论主题：{topic}

正方观点汇总：
{chr(10).join(pro_history[:3])}

反方观点汇总：
{chr(10).join(con_history[:3])}

请给出一个中立、客观的总结，包括双方的主要论点和争议焦点。
"""
    )

    print(f"\n{summary}")

    return {
        "topic": topic,
        "pro_history": pro_history,
        "con_history": con_history,
        "summary": summary
    }


if __name__ == "__main__":
    result = debate("人工智能应该被严格监管吗？", rounds=2)