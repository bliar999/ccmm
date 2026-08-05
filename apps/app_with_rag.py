"""
莉莉 - 带RAG功能的AI助手
集成文档问答 + 对话历史
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import DeepSeekClient
from db_manager import ChatHistoryDB
from week3_rag.rag_minimal import search, chunks, encode_texts, chunk_embeddings
from week3_rag.rag_with_memory import DialogueRAG

st.set_page_config(page_title="🌸 莉莉 - AI小助手", page_icon="🌸")

st.title("🌸 莉莉")
st.caption("我能回答文档问题，也能记住我们的对话 💕")


# ========== 初始化 ==========
@st.cache_resource
def get_client():
    return DeepSeekClient()


@st.cache_resource
def get_db():
    return ChatHistoryDB()


@st.cache_resource
def get_rag():
    return DialogueRAG()


client = get_client()
db = get_db()
rag = get_rag()

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
    # 清空RAG历史
    rag.clear()


# ========== 侧边栏 ==========
with st.sidebar:
    st.header("📜 对话历史")

    if st.button("➕ 新建对话", use_container_width=True):
        new_id = db.create_conversation("莉莉的新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        st.session_state.need_load = False
        rag.clear()
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

    st.header("📄 知识库")
    st.caption(f"已加载 {len(chunks)} 个文档片段")

    # 显示文档片段预览
    with st.expander("查看文档片段"):
        for i, chunk in enumerate(chunks[:5]):
            st.text(f"[{i + 1}] {chunk[:60]}...")

    st.divider()

    st.header("⚙️ 参数设置")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    use_rag = st.toggle("📚 启用RAG文档问答", value=True)

    if st.button("🗑️ 清空当前对话", use_container_width=True):
        db.delete_conversation(st.session_state.current_conv_id)
        new_id = db.create_conversation("莉莉的新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        rag.clear()
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

    # 自动命名
    if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    with st.chat_message("assistant"):
        with st.spinner("莉莉正在思考..."):
            try:
                if use_rag:
                    # 使用RAG模式
                    response = rag.ask(user_input)
                else:
                    # 普通模式
                    history = st.session_state.messages[-10:] if len(
                        st.session_state.messages) > 10 else st.session_state.messages
                    response = client.chat_with_history(history, temperature=temperature)

                st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"莉莉遇到了一点小问题：{e}")

# 显示当前状态
st.caption(
    f"📌 当前对话: {db.get_conversation_title(st.session_state.current_conv_id)} ｜ {len(st.session_state.messages)} 条消息")