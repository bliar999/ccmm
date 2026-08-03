import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_client import DeepSeekClient
from memory_manager import MemoryManager

st.set_page_config(page_title="🧠 有记忆的AI对话", page_icon="🧠")

st.title("🧠 AI助手 - 带记忆功能")
st.caption("我能记住你告诉我的信息哦！")


# ========== 初始化所有状态 ==========
# 初始化DeepSeek客户端
@st.cache_resource
def get_client():
    return DeepSeekClient()


client = get_client()

# 初始化记忆管理器
if "memory" not in st.session_state:
    st.session_state.memory = MemoryManager()

# 初始化用户画像（存储关键信息）
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "user_name": None,
        "user_profession": None,
        "user_interests": [],
        "user_goal": None,
        "last_topic": None,
        "user_preferences": {}
    }

# 初始化对话历史
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是一个乐于助人的AI助手。记住用户告诉你的个人信息，并在后续对话中自然引用。"}
    ]

# ========== 侧边栏配置 ==========
with st.sidebar:
    st.header("👤 用户画像（记忆面板）")

    # 显示当前记忆
    profile = st.session_state.user_profile
    if profile["user_name"]:
        st.success(f"姓名: {profile['user_name']}")
    if profile["user_profession"]:
        st.info(f"职业: {profile['user_profession']}")
    if profile["user_interests"]:
        st.info(f"兴趣: {', '.join(profile['user_interests'])}")
    if profile["user_goal"]:
        st.info(f"目标: {profile['user_goal']}")

    if not any(profile.values()):
        st.caption("还没有记住任何信息，聊聊天我会慢慢了解你")

    st.divider()

    # 手动编辑/清空记忆
    with st.expander("✏️ 手动编辑记忆"):
        new_name = st.text_input("修改姓名", value=profile["user_name"] or "")
        new_profession = st.text_input("修改职业", value=profile["user_profession"] or "")

        if st.button("更新记忆"):
            if new_name:
                st.session_state.user_profile["user_name"] = new_name
            if new_profession:
                st.session_state.user_profile["user_profession"] = new_profession
            st.rerun()

        if st.button("🗑️ 清空所有记忆", type="secondary"):
            st.session_state.user_profile = {
                "user_name": None,
                "user_profession": None,
                "user_interests": [],
                "user_goal": None,
                "last_topic": None,
                "user_preferences": {}
            }
            st.rerun()

    st.divider()
    st.header("⚙️ 参数设置")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)

    system_preset = st.selectbox(
        "系统提示词预设",
        ["你是一个乐于助人的AI助手。记住用户告诉你的个人信息，并在后续对话中自然引用。",
         "你是一个专业的程序员导师",
         "你是一个幽默的AI，喜欢讲冷笑话",
         "你是一个严谨的学者"]
    )

    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = [
            {"role": "system", "content": system_preset}
        ]
        st.rerun()


# ========== 构建系统提示词（注入用户画像） ==========
def build_system_prompt():
    """将用户画像注入系统提示词"""
    memory_context = st.session_state.memory.get_context_prompt(st.session_state.user_profile)
    base_prompt = system_preset
    if memory_context:
        return base_prompt + "\n\n" + memory_context
    return base_prompt


# ========== 显示对话历史 ==========
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# ========== 用户输入处理 ==========
user_input = st.chat_input("请告诉我你的问题，也可以介绍你自己...")

if user_input:
    # 1. 更新系统提示词（含用户画像）
    system_content = build_system_prompt()
    if st.session_state.messages[0]["content"] != system_content:
        st.session_state.messages[0] = {"role": "system", "content": system_content}

    # 2. 添加用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 3. 调用AI回复
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                response = client.chat_with_history(
                    st.session_state.messages,
                    temperature=temperature
                )
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

                # 4. 【核心记忆提取】从对话中提取用户信息
                extracted = st.session_state.memory.extract_info(user_input, response)
                if extracted:
                    st.session_state.user_profile = st.session_state.memory.update_profile(
                        st.session_state.user_profile,
                        extracted
                    )
                    # 如果提取到新信息，侧边栏会在下次渲染时自动更新

            except Exception as e:
                st.error(f"调用失败：{e}")