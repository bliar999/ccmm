import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_client import DeepSeekClient

st.set_page_config(page_title="完整版AI对话", page_icon="🎛️")

st.title("🎛️ 完整版AI对话机器人")

# 侧边栏：配置参数
with st.sidebar:
    st.header("⚙️ 参数设置")
    temperature = st.slider("Temperature（随机性）", 0.0, 2.0, 0.7, 0.1)
    max_tokens = st.slider("最大输出长度", 128, 4096, 2048, 128)
    system_preset = st.selectbox(
        "系统提示词预设",
        ["你是一个乐于助人的助手",
         "你是一个专业的程序员，擅长解决技术问题",
         "你是一个幽默的AI，喜欢讲冷笑话",
         "你是一个严谨的学者，回答问题要有理有据"]
    )
    custom_system = st.text_area("自定义系统提示词（覆盖预设）",
                                 placeholder="输入你自己的系统提示词")

    st.divider()
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = [{"role": "system", "content": system_preset}]
        st.rerun()


# 初始化客户端
@st.cache_resource
def get_client():
    return DeepSeekClient()


client = get_client()

# 初始化历史
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": system_preset}]

# 显示历史
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# 用户输入
user_input = st.chat_input("请输入你的问题...")

if user_input:
    # 使用选中的系统提示词
    system_content = custom_system if custom_system else system_preset
    # 更新系统提示词（如果变化）
    if st.session_state.messages[0]["content"] != system_content:
        st.session_state.messages[0] = {"role": "system", "content": system_content}

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                # 注意：这里只传完整历史，temperature从界面获取
                response = client.chat_with_history(
                    st.session_state.messages,
                    temperature=temperature
                )
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"调用失败：{e}")

# 显示Token消耗（保守估计，仅供参考）
st.caption(f"当前对话轮次：{(len(st.session_state.messages) - 1) // 2} 轮")