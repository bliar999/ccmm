import streamlit as st
import sys
from pathlib import Path

# 将项目根目录加入Python路径，方便导入utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_client import DeepSeekClient

st.set_page_config(page_title="AI对话机器人", page_icon="💬")

st.title("💬 AI对话机器人")
st.caption("基于DeepSeek API")

# 初始化客户端（使用缓存避免重复创建）
@st.cache_resource
def get_client():
    return DeepSeekClient()

client = get_client()

# 用户输入
user_input = st.text_input("请输入你的问题：", placeholder="你好，AI！", key="input")

# 系统提示词（本周六会用上）
system_prompt = st.text_input("系统提示词（可选）：",
                              placeholder="你是一个乐于助人的助手",
                              key="system")

if st.button("发送", type="primary"):
    if user_input:
        with st.spinner("AI正在思考..."):
            try:
                system = system_prompt if system_prompt else "你是一个乐于助人的助手"
                response = client.chat(user_input, system=system, temperature=0.7)
                st.success("✅ 回复成功！")
                st.markdown(response)
            except Exception as e:
                st.error(f"调用失败：{e}")
    else:
        st.warning("请输入内容再发送")