"""
莉莉 - 稳定版（强制侧边栏修复）
"""

import streamlit as st
import sys
from pathlib import Path
import json
import re
import math
from datetime import datetime
import requests
import os
import random
import hashlib
import secrets
import sqlite3

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import ChatHistoryDB
from utils.api_client import DeepSeekClient
from utils.api_tools import get_weather, search, get_weather_tool_desc, get_search_tool_desc
from utils.cost_monitor import CostMonitor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# ==================== 用户认证系统 ====================

class AuthSystem:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "users.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           username
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           password_hash
                           TEXT
                           NOT
                           NULL,
                           salt
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           last_login
                           TIMESTAMP
                       )
                       """)
        conn.commit()
        conn.close()

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return hash_obj.hexdigest(), salt

    def register(self, username: str, password: str) -> tuple:
        try:
            password_hash, salt = self._hash_password(password)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, password_hash, salt)
            )
            conn.commit()
            conn.close()
            return True, "注册成功，请登录"
        except sqlite3.IntegrityError:
            return False, "用户名已存在"
        except Exception as e:
            return False, f"注册失败：{str(e)}"

    def login(self, username: str, password: str) -> tuple:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return False, "用户名不存在"
        password_hash, salt = row
        input_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        if input_hash == password_hash:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            conn.commit()
            conn.close()
            return True, "登录成功"
        return False, "密码错误"

    def get_user_id(self, username: str) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None


# ==================== 工具函数 ====================

def calculate(expression: str) -> dict:
    allowed_chars = r'[\d+\-*/().% ]'
    if not re.match(f'^{allowed_chars}+$', expression):
        return {"expression": expression, "error": "表达式包含非法字符", "result": None}
    try:
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return {"expression": expression, "result": result, "error": None}
    except Exception as e:
        return {"expression": expression, "result": None, "error": str(e)}


def get_calc_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如 '2 + 3 * 4'"}
                },
                "required": ["expression"]
            }
        }
    }


# ==================== 单Agent 核心 ====================

TOOLS = {
    "get_weather": {"function": get_weather, "description": get_weather_tool_desc()},
    "calculate": {"function": calculate, "description": get_calc_tool_desc()},
    "search": {"function": search, "description": get_search_tool_desc()}
}


def get_tools_schema():
    return [TOOLS[name]["description"] for name in TOOLS]


def execute_tool(tool_name: str, arguments: dict):
    if tool_name not in TOOLS:
        return {"error": f"未知工具: {tool_name}"}
    try:
        result = TOOLS[tool_name]["function"](**arguments)
        return result
    except Exception as e:
        return {"error": f"工具执行失败: {str(e)}"}


def react_agent(question: str, max_steps: int = 3, cost_monitor=None):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("DEEPSEEK_API_KEY")
        except:
            pass
    if not api_key:
        return "❌ API Key未设置"

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    messages = [
        {"role": "system", "content": """你是莉莉，一个智能助手。你能调用工具来帮助回答问题。

可用工具：
1. get_weather - 查询城市天气
2. calculate - 执行数学计算
3. search - 搜索网络信息
"""},
        {"role": "user", "content": question}
    ]

    step = 0
    while step < max_steps:
        step += 1
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=get_tools_schema(),
                tool_choice="auto",
                temperature=0.3
            )

            if cost_monitor and hasattr(response, 'usage'):
                cost_monitor.log_usage(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    model="deepseek-chat"
                )

        except Exception as e:
            return f"调用API失败：{str(e)}"

        assistant_message = response.choices[0].message

        if assistant_message.tool_calls:
            messages.append(assistant_message)
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except:
                    arguments = {}
                result = execute_tool(tool_name, arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
        else:
            return assistant_message.content

    return "抱歉，我思考太久了"


# ==================== 多Agent 类 ====================

class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.history = []
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            try:
                api_key = st.secrets.get("DEEPSEEK_API_KEY")
            except:
                pass
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1") if api_key else None

    def think(self, user_input: str, context: str = "") -> str:
        if not self.client:
            return "❌ API Key未设置"
        messages = [{"role": "system", "content": self.system_prompt}]
        if context:
            messages.append({"role": "user", "content": f"【参考信息】\n{context}\n\n【当前任务】\n{user_input}"})
        else:
            messages.append({"role": "user", "content": user_input})
        for msg in self.history[-6:]:
            messages.append(msg)
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"调用失败：{str(e)}"

    def clear_history(self):
        self.history = []


class ResearcherAgent(BaseAgent):
    def __init__(self):
        system_prompt = "你是莉莉团队中的【研究员】。深入研究问题，收集信息。"
        super().__init__(name="研究员", role="信息收集与分析", system_prompt=system_prompt)


class CriticAgent(BaseAgent):
    def __init__(self):
        system_prompt = "你是莉莉团队中的【批评家】。对研究结果提出质疑，找出漏洞。"
        super().__init__(name="批评家", role="质疑与完善", system_prompt=system_prompt)


class SupervisorAgent(BaseAgent):
    def __init__(self):
        system_prompt = "你是莉莉团队的【监督者】，负责分配任务、协调团队、汇总结果。"
        super().__init__(name="监督者", role="任务分配与协调", system_prompt=system_prompt)

    def orchestrate(self, question: str) -> str:
        researcher = ResearcherAgent()
        research_result = researcher.think(question)
        critic = CriticAgent()
        critique = critic.think(f"请评阅：\n{research_result}")
        summary = self.think(f"""
请基于以下信息生成完整回答：
【研究员的发现】{research_result}
【批评家的建议】{critique}
【用户问题】{question}
请整合以上信息，给出全面平衡的回答。
""")
        return summary


# ==================== 动态CSS (彻底修复) ====================

def load_css():
    st.markdown("""
    <style>
    /* 页面背景 */
    .stApp { background: linear-gradient(135deg, #fce4ec, #f3e5f5, #e8eaf6); }

    /* 聊天气泡：白底黑字 */
    .user-message {
        background: linear-gradient(135deg, #7c4dff, #536dfe);
        color: white !important; 
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        display: inline-block;
        clear: both;
        float: right;
    }
    .assistant-message {
        background: white;
        color: #333333 !important; /* 强制深色文字 */
        padding: 14px 20px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        display: inline-block;
        clear: both;
        float: left;
        box-shadow: 0 4px 24px rgba(0,0,0,0.05);
        border: 1px solid #f3e5f5;
    }

    /* 登录框样式 */
    .login-container {
        max-width: 400px;
        margin: 60px auto;
        padding: 40px;
        background: rgba(255,255,255,0.7);
        backdrop-filter: blur(20px);
        border-radius: 30px;
        box-shadow: 0 8px 40px rgba(0,0,0,0.08);
    }
    .login-container h1 { text-align: center; color: #4a148c; font-size: 2.2rem; }
    .login-container .subtitle { text-align: center; color: #888; font-size: 0.9rem; margin-bottom: 24px; }
    .login-container .lili-icon { text-align: center; font-size: 4rem; margin-bottom: 12px; }

    /* 按钮美化 */
    .stButton button {
        border-radius: 30px !important;
        background: linear-gradient(135deg, #ec407a, #ab47bc) !important;
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
    }

    /* 隐藏自带的菜单和页脚 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* 电脑大屏强制侧边栏显示 */
    @media (min-width: 769px) {
        [data-testid="stSidebar"] {
            display: block !important;
            flex: 0 0 21rem !important;
            width: 21rem !important;
        }
    }

    /* 手机小屏给悬浮按钮留位置 */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 100px !important; 
        }
        .stChatInput {
            bottom: 20px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ==================== 登录界面 ====================

def show_login_page():
    st.markdown("""
    <style>
    .stApp > header {display: none;}
    .stApp > .stAppViewContainer > .stAppViewBlockContainer {padding-top: 0;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:80vh;">
        <div class="login-container">
            <div class="lili-icon">🌸</div>
            <h1>莉莉的花园</h1>
            <div class="subtitle">登录进入你的专属AI花园</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🌺 登录", "🌱 注册"])

        with tab1:
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("用户名", placeholder="请输入用户名", key="login_user")
                password = st.text_input("密码", type="password", placeholder="请输入密码", key="login_pass")
                submitted = st.form_submit_button("🌸 登录", use_container_width=True)
                if submitted:
                    if username and password:
                        success, msg = auth.login(username, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.warning("请输入用户名和密码")

        with tab2:
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("用户名", placeholder="请设置用户名", key="reg_user")
                new_password = st.text_input("密码", type="password", placeholder="请设置密码（至少6位）", key="reg_pass")
                confirm_password = st.text_input("确认密码", type="password", placeholder="再次输入密码",
                                                 key="reg_confirm")
                submitted = st.form_submit_button("🌱 注册", use_container_width=True)
                if submitted:
                    if not new_username or not new_password:
                        st.warning("请填写完整信息")
                    elif len(new_password) < 6:
                        st.warning("密码至少6位")
                    elif new_password != confirm_password:
                        st.warning("两次密码不一致")
                    else:
                        success, msg = auth.register(new_username, new_password)
                        if success:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")


# ==================== 主应用 ====================

def main_app():
    st.markdown("🌸 欢迎回来，" + st.session_state.username + "！")

    # ===== 🆕 新增：手动添加的悬浮侧边栏打开按钮 (仅小屏显示) =====
    st.markdown("""
    <style>
    .sidebar-toggle-btn {
        position: fixed;
        top: 80px;
        left: 15px;
        z-index: 99999;
        background-color: #ab47bc;
        color: white;
        border: none;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        font-size: 22px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .sidebar-toggle-btn:hover {
        transform: scale(1.1);
        background-color: #8e24aa;
    }
    /* 在电脑上隐藏这个悬浮球 */
    @media (min-width: 769px) {
        .sidebar-toggle-btn {
            display: none !important;
        }
    }
    </style>

    <!-- JS 点击事件：强行滑出/收回侧边栏 -->
    <button class="sidebar-toggle-btn" onclick="
        var sidebar = window.parent.document.querySelector('[data-testid=stSidebar]');
        if(sidebar.style.transform === 'translateX(0px)' || sidebar.style.transform === '') {
            sidebar.style.transform = 'translateX(-100%)';
            sidebar.style.transition = 'transform 0.3s ease-in-out';
        } else {
            sidebar.style.transform = 'translateX(0px)';
            sidebar.style.transition = 'transform 0.3s ease-in-out';
        }
    ">☰</button>
    """, unsafe_allow_html=True)

    # ==============================================================

    @st.cache_resource
    def get_db():
        user_id = auth.get_user_id(st.session_state.username)
        return ChatHistoryDB(user_id=user_id)

    @st.cache_resource
    def get_client():
        return DeepSeekClient()

    @st.cache_resource
    def get_cost_monitor():
        user_id = auth.get_user_id(st.session_state.username)
        return CostMonitor(user_id=user_id)

    db = get_db()
    client = get_client()
    cost_monitor = get_cost_monitor()

    if "current_conv_id" not in st.session_state:
        convs = db.list_conversations(1)
        st.session_state.current_conv_id = convs[0]["id"] if convs else db.create_conversation("莉莉的新对话")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "need_load" not in st.session_state:
        st.session_state.need_load = True

    if "current_mode" not in st.session_state:
        st.session_state.current_mode = "💬 普通模式"

    def load_conversation(conv_id: int):
        st.session_state.current_conv_id = conv_id
        messages = db.get_conversation(conv_id)
        st.session_state.messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        st.session_state.need_load = False

    # ==================== 侧边栏 (电脑端) ====================
    with st.sidebar:
        st.markdown(f"👤 {st.session_state.username}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

        st.divider()

        mode = st.radio(
            "选择模式",
            ["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"],
            index=["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"].index(st.session_state.current_mode)
        )
        if mode != st.session_state.current_mode:
            st.session_state.current_mode = mode
            st.rerun()

        st.divider()

        st.markdown("### 📜 对话历史")
        if st.button("➕ 新建对话", use_container_width=True):
            new_id = db.create_conversation("莉莉的新对话")
            st.session_state.current_conv_id = new_id
            st.session_state.messages = []
            st.session_state.need_load = False
            st.rerun()

        conversations = db.list_conversations(20)
        for conv in conversations:
            col1, col2 = st.columns([4, 1])
            with col1:
                is_current = conv["id"] == st.session_state.current_conv_id
                title = conv["title"][:18]
                label = f"🟢 {title}" if is_current else f"📄 {title}"
                if st.button(label, key=f"load_{conv['id']}", use_container_width=True):
                    load_conversation(conv["id"])
                    st.rerun()
                st.caption(f"{conv['message_count']}条")
            with col2:
                if st.button("🗑️", key=f"del_{conv['id']}"):
                    db.delete_conversation(conv["id"])
                    st.rerun()

        st.divider()
        st.markdown("### 💰 今日用量")
        today = cost_monitor.get_today_usage()
        st.metric("调用", today["call_count"])
        st.metric("费用", f"¥{today['total_cost']:.4f}")

        st.divider()
        st.markdown("### ⚙️ 参数")
        temperature = st.slider("创造力", 0.0, 2.0, 0.7, 0.1)
        if mode == "🤖 单Agent模式":
            max_steps = st.slider("推理步数", 1, 5, 3)

    # ==================== 聊天主区域 ====================
    if st.session_state.need_load:
        load_conversation(st.session_state.current_conv_id)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-message">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="assistant-message">{msg["content"]}</div>', unsafe_allow_html=True)

    user_input = st.chat_input("💬 和莉莉聊聊吧...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.markdown(f'<div class="user-message">{user_input}</div>', unsafe_allow_html=True)
        db.save_message(st.session_state.current_conv_id, "user", user_input)

        if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
            title = user_input[:30]
            db.update_conversation_title(st.session_state.current_conv_id, title)

        with st.spinner("莉莉正在思考..."):
            try:
                if st.session_state.current_mode == "💬 普通模式":
                    history = st.session_state.messages[-10:]
                    if not history or history[0]["role"] != "system":
                        history = [{"role": "system", "content": "你是莉莉，一个温柔可爱的小花仙助手"}] + history
                    response = client.chat_with_history(history, temperature=temperature)
                elif st.session_state.current_mode == "🤖 单Agent模式":
                    response = react_agent(user_input, max_steps=max_steps, cost_monitor=cost_monitor)
                else:
                    supervisor = SupervisorAgent()
                    response = supervisor.orchestrate(user_input)

                st.markdown(f'<div class="assistant-message">{response}</div>', unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"莉莉遇到问题：{e}")

    # ==================== 手机端底部快捷栏 ====================
    st.markdown("---")
    c1, c2, c3, c4 = st.columns([1, 2.5, 2.5, 1])

    with c1:
        if st.button("➕", key="mobile_new_chat", help="新建对话"):
            new_id = db.create_conversation("莉莉的新对话")
            st.session_state.current_conv_id = new_id
            st.session_state.messages = []
            st.session_state.need_load = False
            st.rerun()

    with c2:
        mobile_mode = st.selectbox(
            "模式",
            ["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"],
            index=["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"].index(st.session_state.current_mode),
            label_visibility="collapsed",
            key="mobile_mode_selector"
        )
        if mobile_mode != st.session_state.current_mode:
            st.session_state.current_mode = mobile_mode
            st.session_state.messages = []
            st.rerun()

    with c4:
        if st.button("🚪", key="mobile_logout", help="退出"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()


# ==================== 主入口 ====================

auth = AuthSystem()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

load_css()

if not st.session_state.logged_in:
    show_login_page()
else:
    main_app()
