import streamlit as st

st.set_page_config(page_title="侧边栏测试", page_icon="🧪")

st.title("🧪 侧边栏测试页面")

# ===== 侧边栏 =====
with st.sidebar:
    st.header("📌 这是侧边栏")
    st.write("如果你能看到这个，说明侧边栏正常工作！")

    st.divider()

    st.subheader("功能菜单")
    if st.button("按钮1"):
        st.success("点击了按钮1")
    if st.button("按钮2"):
        st.success("点击了按钮2")

    st.divider()

    st.caption("✅ 侧边栏测试完成")

# ===== 主界面 =====
st.write("### 主界面内容")
st.write("侧边栏应该显示在左侧")

# 显示当前状态
st.info("💡 如果左侧没有侧边栏，请检查：\n1. 浏览器宽度是否足够\n2. 是否点击了侧边栏的折叠按钮")