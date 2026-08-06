"""
莉莉 - 多智能体协作版
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_manager import ChatHistoryDB
from week6_multi_agent.supervisor_agent import SupervisorAgent
from week6_multi_agent.workflow_orchestrator import WorkflowOrchestrator
from week6_multi_agent.researcher_agent import ResearcherAgent
from week6_multi_agent.critic_agent import CriticAgent

st.set_page_config(page_title="🌸 莉莉 - 多智能体团队", page_icon="🌸")

st.title("🌸 莉莉（团队版）")
st.caption("我身后有一个团队：研究员 + 批评家 + 监督者 🤝")


# ========== 初始化 ==========
@st.cache_resource
def get_db():
    return ChatHistoryDB()


@st.cache_resource
def get_supervisor():
    return SupervisorAgent()


db = get_db()
supervisor = get_supervisor()

# 初始化对话
if "current_conv_id" not in st.session_state:
    convs = db.list_conversations(1)
    st.session_state.current_conv_id = convs[0]["id"] if convs else db.create_conversation("莉莉的新对话")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "need_load" not in st.session_state:
    st.session_state.need_load = True


# ========== 加载对话 ==========
def load_conversation(conv_id: int):
    st.session_state.current_conv_id = conv_id
    messages = db.get_conversation(conv_id)
    st.session_state.messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
    ]
    st.session_state.need_load = False


# ========== 侧边栏 ==========
with st.sidebar:
    st.header("📜 对话历史")

    if st.button("➕ 新建对话", use_container_width=True):
        new_id = db.create_conversation("莉莉的新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        st.session_state.need_load = False
        st.rerun()

    st.divider()

    conversations = db.list_conversations(20)
    for conv in conversations:
        col1, col2 = st.columns([4, 1])
        with col1:
            is_current = conv["id"] == st.session_state.current_conv_id
            title = conv["title"][:18] + "..." if len(conv["title"]) > 18 else conv["title"]
            label = f"🟢 {title}" if is_current else f"📄 {title}"

            if st.button(label, key=f"load_{conv['id']}", use_container_width=True):
                load_conversation(conv["id"])
                st.rerun()
            st.caption(f"{conv['message_count']}条消息")

        with col2:
            if st.button("🗑️", key=f"del_{conv['id']}"):
                db.delete_conversation(conv["id"])
                st.rerun()

    st.divider()

    st.header("🧑‍🤝‍🧑 团队模式")
    mode = st.radio(
        "选择协作模式",
        ["🧠 监督者模式", "🔬 研究员+批评家", "⚡ 工作流编排"],
        help="监督者：分配任务给团队；研究员+批评家：研究和评阅；工作流：顺序执行"
    )

    st.divider()

    st.header("👥 团队成员")
    st.success("✅ 监督者")
    st.success("✅ 研究员")
    st.success("✅ 批评家")

    st.divider()

    if st.button("🗑️ 清空当前对话", use_container_width=True):
        db.delete_conversation(st.session_state.current_conv_id)
        new_id = db.create_conversation("莉莉的新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        st.rerun()

# ========== 主界面 ==========
if st.session_state.need_load:
    load_conversation(st.session_state.current_conv_id)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# ========== 用户输入 ==========
user_input = st.chat_input("和莉莉团队聊聊吧 💬")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    with st.chat_message("assistant"):
        with st.spinner("莉莉团队正在协作..."):
            try:
                if mode == "🧠 监督者模式":
                    result = supervisor.orchestrate(user_input)
                    response = result["final_answer"]
                elif mode == "🔬 研究员+批评家":
                    from week6_multi_agent.researcher_agent import ResearcherAgent
                    from week6_multi_agent.critic_agent import CriticAgent

                    r = ResearcherAgent()
                    c = CriticAgent()
                    research = r.think(user_input)
                    critique = c.think(f"评阅：{research}")
                    response = f"【研究】\n{research}\n\n【评阅】\n{critique}"
                else:
                    # 工作流模式
                    workflow = WorkflowOrchestrator()
                    workflow.add_step(ResearcherAgent(), user_input)
                    workflow.add_step(CriticAgent(), f"评阅研究结果", depends_on=["step_0"])
                    result = workflow.run(user_input)
                    response = result["summary"]

                st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"莉莉团队遇到问题：{e}")

st.caption(f"📌 {db.get_conversation_title(st.session_state.current_conv_id)} ｜ {len(st.session_state.messages)} 条消息")