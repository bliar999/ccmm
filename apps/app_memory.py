import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_client import DeepSeekClient

st.set_page_config(page_title="带记忆的对话机器人", page_icon="🧠")

st.title("🧠 带记忆的对话机器人")
st.caption("能记住你之前说了什么")


# 初始化客户端
@st.cache_resource
def get_client():
    return DeepSeekClient()


client = get_client()

# 初始化对话历史（存储在session_state中）
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是一个乐于助人的助手"}
    ]

# 显示历史对话
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# 用户输入（使用chat_input组件更优雅）
user_input = st.chat_input("请输入你的问题...")

if user_input:
    # 添加到历史
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 调用API
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                response = client.chat_with_history(st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"调用失败：{e}")

# 清空对话按钮
if st.button("🗑️ 清空对话"):
    st.session_state.messages = [{"role": "system", "content": "你是一个乐于助人的助手"}]
    st.rerun()