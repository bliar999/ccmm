import streamlit as st

st.set_page_config(page_title="我的第一个AI应用", page_icon="🤖")

st.title("🤖 欢迎来到AI聊天室")
st.write("这是用Streamlit搭建的网页应用")

# 输入框
user_input = st.text_input("请输入你的问题：", placeholder="你好，AI！")

# 按钮
if st.button("发送"):
    if user_input:
        st.write(f"你问的是：{user_input}")
        st.write("AI回复：这是一个测试回复，Day 11会接入真实API")
    else:
        st.warning("请输入内容再发送")