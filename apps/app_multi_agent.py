"""
莉莉 - 多智能体协作版
整合：普通模式 + 单Agent + 多Agent
"""

import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import ChatHistoryDB
from utils.api_client import DeepSeekClient

# ========== 导入各模式 ==========
# 单Agent（第五周）
try:
    from week5_agent.react_agent import react_agent

    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    react_agent = None

# 多Agent（第六周）
try:
    from week6_multi_agent.supervisor_agent import SupervisorAgent

    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False
    SupervisorAgent = None

st.set_page_config(page_title="🌸 莉莉 - 智能团队", page_icon="🌸")

st.title("🌸 莉莉")
st.caption("💬 普通聊天 ｜ 🤖 工具调用 ｜ 🧑‍🤝‍🧑 团队协作")


# ========== 初始化 ==========
@st.cache_resource
def get_db():
    return ChatHistoryDB()


@st.cache_resource
def get_client():
    return DeepSeekClient()


db = get_db()
client = get_client()

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
    st.header("🎯 模式选择")

    # 模式切换
    mode = st.radio(
        "选择工作模式",
        [
            "💬 普通模式",
            "🤖 单Agent模式",
            "🧑‍🤝‍🧑 多Agent模式"
        ],
        help="💬 普通聊天 | 🤖 工具调用(时间/计算/搜索) | 🧑‍🤝‍🧑 团队协作分析"
    )

    # 模式状态显示
    if mode == "🤖 单Agent模式":
        if AGENT_AVAILABLE:
            st.success("✅ Agent已就绪")
            st.caption("能力：时间查询 | 数学计算 | 网络搜索")
        else:
            st.warning("⚠️ Agent模块未加载")
    elif mode == "🧑‍🤝‍🧑 多Agent模式":
        if MULTI_AGENT_AVAILABLE:
            st.success("✅ 多Agent团队已就绪")
            st.caption("成员：研究员 + 批评家 + 监督者")
        else:
            st.warning("⚠️ 多Agent模块未加载")
    else:
        st.info("💬 普通聊天模式")

    st.divider()

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

    st.header("⚙️ 参数")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)

    if mode == "🤖 单Agent模式" and AGENT_AVAILABLE:
        max_steps = st.slider("Agent推理步数", 1, 5, 3)

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

# 状态栏
mode_labels = {
    "💬 普通模式": "💬",
    "🤖 单Agent模式": "🤖",
    "🧑‍🤝‍🧑 多Agent模式": "🧑‍🤝‍🧑"
}
st.caption(f"{mode_labels.get(mode, '💬')} {mode} ｜ {len(st.session_state.messages)} 条消息")

# ========== 用户输入 ==========
user_input = st.chat_input("和莉莉聊聊吧 💬")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    with st.chat_message("assistant"):
        with st.spinner("莉莉正在思考..."):
            try:
                response = ""

                # ===== 根据模式执行 =====
                if mode == "💬 普通模式":
                    # 普通聊天
                    history = st.session_state.messages[-10:] if len(
                        st.session_state.messages) > 10 else st.session_state.messages
                    if not history or history[0]["role"] != "system":
                        history = [{"role": "system", "content": "你是莉莉，一个温柔体贴的AI助手"}] + history
                    response = client.chat_with_history(history, temperature=temperature)

                elif mode == "🤖 单Agent模式":
                    if AGENT_AVAILABLE and react_agent:
                        response = react_agent(user_input, max_steps=max_steps)
                    else:
                        response = "⚠️ Agent模块不可用，请检查 week5_agent 文件夹"

                elif mode == "🧑‍🤝‍🧑 多Agent模式":
                    if MULTI_AGENT_AVAILABLE and SupervisorAgent:
                        supervisor = SupervisorAgent()
                        response = supervisor.orchestrate(user_input)
                    else:
                        response = "⚠️ 多Agent模块不可用，请检查 week6_multi_agent 文件夹"

                st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"莉莉遇到问题：{e}")

st.caption("💡 提示：不同模式有不同能力，试试切换模式问同样的问题！")