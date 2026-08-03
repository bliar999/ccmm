import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_client import DeepSeekClient
from db_manager import ChatHistoryDB

st.set_page_config(page_title="📚 有历史的AI对话", page_icon="📚")

st.title("📚 AI对话 - 带历史记录")


# ========== 初始化 ==========
@st.cache_resource
def get_client():
    return DeepSeekClient()


@st.cache_resource
def get_db():
    return ChatHistoryDB()


client = get_client()
db = get_db()

# 初始化session状态
if "current_conv_id" not in st.session_state:
    # 如果有历史记录，加载最新；否则创建新对话
    convs = db.list_conversations(1)
    if convs:
        st.session_state.current_conv_id = convs[0]["id"]
    else:
        st.session_state.current_conv_id = db.create_conversation("新对话")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "need_load" not in st.session_state:
    st.session_state.need_load = True


# ========== 加载对话 ==========
def load_conversation(conv_id: int):
    """加载指定对话到session"""
    st.session_state.current_conv_id = conv_id
    messages = db.get_conversation(conv_id)
    # 转换为Streamlit格式
    st.session_state.messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
    ]
    st.session_state.need_load = False


# ========== 侧边栏：历史列表 ==========
with st.sidebar:
    st.header("📜 对话历史")

    # 新建对话按钮
    if st.button("➕ 新建对话", use_container_width=True):
        new_id = db.create_conversation("新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        st.session_state.need_load = False
        st.rerun()

    st.divider()

    # 获取所有历史对话
    conversations = db.list_conversations(50)

    if not conversations:
        st.caption("暂无历史记录")
    else:
        for conv in conversations:
            # 显示每条历史记录
            col1, col2 = st.columns([4, 1])
            with col1:
                # 截断标题
                title = conv["title"]
                if len(title) > 20:
                    title = title[:20] + "..."

                # 高亮当前对话
                is_current = conv["id"] == st.session_state.current_conv_id
                label = f"🟢 {title}" if is_current else f"📄 {title}"

                # 点击加载历史
                if st.button(
                        label,
                        key=f"load_{conv['id']}",
                        use_container_width=True,
                        type="primary" if is_current else "secondary"
                ):
                    load_conversation(conv["id"])
                    st.rerun()

                # 显示消息数和时间
                st.caption(f"{conv['message_count']} 条消息 • {conv['updated_at'][:16]}")

            with col2:
                # 删除按钮
                if st.button("🗑️", key=f"del_{conv['id']}", help="删除此对话"):
                    db.delete_conversation(conv["id"])
                    if conv["id"] == st.session_state.current_conv_id:
                        # 如果删除的是当前对话，切换到最新
                        remaining = db.list_conversations(1)
                        if remaining:
                            load_conversation(remaining[0]["id"])
                        else:
                            new_id = db.create_conversation("新对话")
                            st.session_state.current_conv_id = new_id
                            st.session_state.messages = []
                    st.rerun()

    st.divider()

    # ===== 导出功能 =====
    if st.session_state.messages:
        with st.expander("📤 导出当前对话"):
            if st.button("导出为Markdown"):
                content = db.get_all_messages_for_export(st.session_state.current_conv_id)
                st.download_button(
                    label="📥 下载",
                    data=content,
                    file_name=f"对话_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown"
                )

    # ===== 参数设置 =====
    st.divider()
    st.header("⚙️ 参数设置")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)

    system_preset = st.text_area(
        "系统提示词",
        value="你是一个乐于助人的AI助手",
        height=80
    )

    # 清空当前对话（仅清空界面，数据库保留）
    if st.button("🗑️ 清空当前对话", use_container_width=True):
        st.session_state.messages = []
        # 同时清空数据库中的消息
        # 简单起见，删除重建
        db.delete_conversation(st.session_state.current_conv_id)
        new_id = db.create_conversation("新对话")
        st.session_state.current_conv_id = new_id
        st.rerun()

# ========== 正文：显示对话 ==========
# 首次加载或切换对话时，从数据库读取
if st.session_state.need_load:
    if st.session_state.current_conv_id:
        load_conversation(st.session_state.current_conv_id)

# 显示所有消息
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# 显示当前对话信息
conv_title = db.get_conversation_title(st.session_state.current_conv_id)
st.caption(f"当前对话：{conv_title} ｜ 共 {len(st.session_state.messages)} 条消息")

# ========== 用户输入 ==========
user_input = st.chat_input("请输入你的问题...")

if user_input:
    # 1. 添加用户消息到界面
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 2. 保存到数据库
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    # 3. 如果对话只有一条消息，用首句作为标题
    if len(st.session_state.messages) == 1:
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    # 4. 调用AI
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                # 构建消息历史（只取最近10轮，避免token过长）
                history = st.session_state.messages[-20:] if len(
                    st.session_state.messages) > 20 else st.session_state.messages
                # 确保第一条是系统提示词
                if not history or history[0]["role"] != "system":
                    history = [{"role": "system", "content": system_preset}] + history
                else:
                    history[0]["content"] = system_preset

                response = client.chat_with_history(history, temperature=temperature)
                st.write(response)

                # 5. 保存AI回复
                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"调用失败：{e}")

    # 刷新界面
    st.rerun()