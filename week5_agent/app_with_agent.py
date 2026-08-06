"""
莉莉 - 带Agent能力的AI助手
支持：时间查询、计算、网络搜索
"""

import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import ChatHistoryDB
from week5_agent.react_agent import react_agent

st.set_page_config(page_title="🌸 莉莉 - AI智能助手", page_icon="🌸")

st.title("🌸 莉莉")
st.caption("我能计算、查时间、搜索信息，还能记住我们的对话 💕")


# ========== 初始化 ==========
@st.cache_resource
def get_db():
    return ChatHistoryDB()


db = get_db()

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

    st.header("🔧 莉莉的能力")
    st.success("✅ 时间查询")
    st.success("✅ 数学计算")
    st.success("✅ 网络搜索")

    st.divider()

    st.header("⚙️ 参数设置")
    max_steps = st.slider("最大推理步数", 1, 5, 3)

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
user_input = st.chat_input("和莉莉说说你的问题吧 💬")

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
                # 使用Agent模式
                response = react_agent(user_input, max_steps=max_steps)
                st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"莉莉遇到了一点小问题：{e}")

st.caption(
    f"📌 当前对话: {db.get_conversation_title(st.session_state.current_conv_id)} ｜ {len(st.session_state.messages)} 条消息")