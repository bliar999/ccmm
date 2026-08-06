import streamlit as st
import sys
from pathlib import Path

# 把项目根目录加入 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import ChatHistoryDB

st.set_page_config(page_title="🧪 莉莉 - Agent 测试版", page_icon="🧪")
# 导入 Agent（第五周）
try:
    from week5_agent.react_agent import react_agent
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    st.error(f"❌ Agent 模块未找到: {e}")
    st.code("请确认 week5_agent/react_agent.py 存在")


# ========== 初始化数据库 ==========
@st.cache_resource
def get_db():
    return ChatHistoryDB()


db = get_db()

# ========== 初始化对话 ==========
if "current_conv_id" not in st.session_state:
    convs = db.list_conversations(1)
    if convs:
        st.session_state.current_conv_id = convs[0]["id"]
    else:
        st.session_state.current_conv_id = db.create_conversation("Agent测试")

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
    st.header("⚙️ 测试设置")

    # ===== Agent 开关 =====
    use_agent = st.toggle("🤖 启用 Agent 模式", value=True)

    if use_agent:
        st.success("✅ Agent 已启用（工具调用）")
        if AGENT_AVAILABLE:
            st.caption("莉莉可以：查时间 | 算数 | 网络搜索")
        else:
            st.error("❌ Agent 不可用")
    else:
        st.info("💬 普通聊天模式")

    # Agent 参数
    if use_agent and AGENT_AVAILABLE:
        max_steps = st.slider("最大推理步数", 1, 5, 3)

    st.divider()

    # ===== 对话历史 =====
    st.header("📜 对话历史")

    if st.button("➕ 新建对话", use_container_width=True):
        new_id = db.create_conversation("Agent测试")
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

    if st.button("🗑️ 清空当前对话", use_container_width=True):
        db.delete_conversation(st.session_state.current_conv_id)
        new_id = db.create_conversation("Agent测试")
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

# 显示当前状态
current_title = db.get_conversation_title(st.session_state.current_conv_id)
st.caption(
    f"📌 {current_title} ｜ {len(st.session_state.messages)} 条消息 ｜ {'🤖 Agent模式' if use_agent and AGENT_AVAILABLE else '💬 普通模式'}")

# ========== 用户输入 ==========
user_input = st.chat_input("输入问题，测试 Agent 能力...")

if user_input:
    # 保存用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    # 自动命名对话
    if db.get_conversation_title(st.session_state.current_conv_id) == "Agent测试":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    # ===== 生成回复 =====
    with st.chat_message("assistant"):
        with st.spinner("莉莉正在思考..."):
            try:
                if use_agent and AGENT_AVAILABLE:
                    # ==========================================
                    # 核心：调用单 Agent（第五周核心代码）
                    # ==========================================
                    response = react_agent(user_input, max_steps=max_steps)
                else:
                    # 普通模式：直接调用大模型
                    from utils.api_client import DeepSeekClient

                    client = DeepSeekClient()
                    history = st.session_state.messages[-10:] if len(
                        st.session_state.messages) > 10 else st.session_state.messages
                    response = client.chat_with_history(history, temperature=0.7)

                st.write(response)

                # 保存助手回复
                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"⚠️ 出错了：{e}")

st.caption("💡 试试问：现在几点？ ｜ 1024*768等于多少？ ｜ 搜一下AI新闻")