import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_client import DeepSeekClient
from memory_manager import MemoryManager
from utils.db_manager import ChatHistoryDB

st.set_page_config(page_title="莉莉 - 你的AI小助手", page_icon="🌸")

st.title("🌸 莉莉")
st.caption("你的专属AI小助手，很高兴认识你！")


# ========== 初始化 ==========
@st.cache_resource
def get_client():
    return DeepSeekClient()


@st.cache_resource
def get_db():
    return ChatHistoryDB()


client = get_client()
db = get_db()

# 初始化记忆
if "memory" not in st.session_state:
    st.session_state.memory = MemoryManager()

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "user_name": None,
        "user_profession": None,
        "user_interests": [],
        "user_goal": None,
    }

# 初始化对话ID和消息
if "current_conv_id" not in st.session_state:
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

    # 新建对话
    if st.button("➕ 新建对话", use_container_width=True):
        new_id = db.create_conversation("新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        st.session_state.need_load = False
        st.rerun()

    st.divider()

    # 列出所有历史对话
    conversations = db.list_conversations(20)
    if not conversations:
        st.caption("暂无历史记录")
    else:
        for conv in conversations:
            col1, col2 = st.columns([4, 1])
            with col1:
                is_current = conv["id"] == st.session_state.current_conv_id
                title = conv["title"]
                if len(title) > 18:
                    title = title[:18] + "..."
                label = f"🟢 {title}" if is_current else f"📄 {title}"

                if st.button(
                        label,
                        key=f"load_{conv['id']}",
                        use_container_width=True,
                        type="primary" if is_current else "secondary"
                ):
                    load_conversation(conv["id"])
                    st.rerun()
                st.caption(f"{conv['message_count']}条消息")

            with col2:
                if st.button("🗑️", key=f"del_{conv['id']}"):
                    db.delete_conversation(conv["id"])
                    if conv["id"] == st.session_state.current_conv_id:
                        remaining = db.list_conversations(1)
                        if remaining:
                            load_conversation(remaining[0]["id"])
                        else:
                            new_id = db.create_conversation("新对话")
                            st.session_state.current_conv_id = new_id
                            st.session_state.messages = []
                    st.rerun()

    st.divider()

    # ===== RAG知识库（预留） =====
    with st.expander("📄 知识库 (RAG)"):
        uploaded_file = st.file_uploader(
            "上传文档（PDF/TXT）",
            type=["pdf", "txt"]
        )
        if uploaded_file:
            st.success(f"✅ {uploaded_file.name}")
            st.caption("（即将支持文档问答）")

    st.divider()

    # ===== 参数设置 =====
    st.header("⚙️ 参数设置")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)

    system_preset = st.selectbox(
        "系统提示词预设",
        ["你是莉莉，一个温柔体贴的AI小助手。",
         "你是莉莉，一个专业的程序员导师",
         "你是莉莉，一个幽默的AI"]
    )

    if st.button("🗑️ 清空当前对话", use_container_width=True):
        db.delete_conversation(st.session_state.current_conv_id)
        new_id = db.create_conversation("新对话")
        st.session_state.current_conv_id = new_id
        st.session_state.messages = []
        st.rerun()

# ========== 主界面 ==========
# 首次加载或切换时从数据库读取
if st.session_state.need_load:
    if st.session_state.current_conv_id:
        load_conversation(st.session_state.current_conv_id)

# 显示消息
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# 当前对话信息
conv_title = db.get_conversation_title(st.session_state.current_conv_id)
st.caption(f"📌 {conv_title} ｜ {len(st.session_state.messages)} 条消息")


# ========== 构建系统提示词 ==========
def build_system_prompt():
    memory_context = st.session_state.memory.get_context_prompt(st.session_state.user_profile)
    base_prompt = system_preset
    if memory_context:
        return base_prompt + "\n\n" + memory_context
    return base_prompt


# ========== 用户输入 ==========
user_input = st.chat_input("请告诉我你的问题，也可以介绍你自己...")

if user_input:
    # 更新系统提示词
    system_content = build_system_prompt()
    if not st.session_state.messages or st.session_state.messages[0]["content"] != system_content:
        st.session_state.messages.insert(0, {"role": "system", "content": system_content})

    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    # 自动命名对话
    if db.get_conversation_title(st.session_state.current_conv_id) == "新对话":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    # 调用AI
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                history = st.session_state.messages[-20:] if len(
                    st.session_state.messages) > 20 else st.session_state.messages
                response = client.chat_with_history(history, temperature=temperature)
                st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

                # 提取记忆（后台运行，不在界面显示）
                extracted = st.session_state.memory.extract_info(user_input, response)
                if extracted:
                    st.session_state.user_profile = st.session_state.memory.update_profile(
                        st.session_state.user_profile,
                        extracted
                    )
                    st.rerun()

            except Exception as e:
                st.error(f"调用失败：{e}")