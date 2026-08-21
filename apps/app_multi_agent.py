"""
莉莉 - 稳定基础版（去除所有不稳定依赖）
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


# ==================== 动态配置 ====================

LILI_MOODS = [
    {"emoji": "💕", "text": "今天心情超好！", "color": "#ec407a"},
    {"emoji": "🌸", "text": "春暖花开～", "color": "#ab47bc"},
    {"emoji": "✨", "text": "元气满满！", "color": "#7c4dff"},
    {"emoji": "🌙", "text": "有点困了 zzz", "color": "#5c6bc0"},
    {"emoji": "🎀", "text": "今天超可爱！", "color": "#ef5350"},
    {"emoji": "🌟", "text": "等你很久啦！", "color": "#ffa726"}
]

THINKING_ANIMATIONS = [
    "🤔 莉莉在想...",
    "🌸 莉莉转圈圈...",
    "✨ 莉莉翻书找答案...",
    "💫 莉莉在认真思考...",
    "🎀 莉莉歪着头想...",
    "📖 莉莉在查资料..."
]

WELCOME_MESSAGES = [
    "✨ 嗨！我是莉莉，今天想聊点什么？",
    "🌸 你来啦！我正等你呢～",
    "💫 莉莉已上线，随时为你服务！",
    "🌺 今天的心情怎么样？和我分享吧！",
    "🎀 莉莉在此，有何吩咐？",
    "💕 见到你真开心！"
]


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


# ==================== 导出功能 ====================

def export_conversation_to_md(conv_id: int, db) -> str:
    messages = db.get_conversation(conv_id)
    title = db.get_conversation_title(conv_id)

    lines = []
    lines.append(f"# 🌸 莉莉对话记录")
    lines.append("")
    lines.append(f"**对话标题：** {title}")
    lines.append(f"**导出时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**消息数量：** {len(messages)} 条")
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in messages:
        if msg["role"] == "user":
            lines.append(f"## 👤 用户")
        elif msg["role"] == "assistant":
            lines.append(f"## 🌸 莉莉")
        else:
            continue
        lines.append("")
        lines.append(msg["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("")
    lines.append("*由莉莉助手自动导出*")

    return "\n".join(lines)


def export_conversation_to_txt(conv_id: int, db) -> str:
    messages = db.get_conversation(conv_id)
    title = db.get_conversation_title(conv_id)

    lines = []
    lines.append("=" * 60)
    lines.append(f"莉莉对话记录 - {title}")
    lines.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")

    for msg in messages:
        if msg["role"] == "user":
            lines.append(f"[用户] {msg['content']}")
        elif msg["role"] == "assistant":
            lines.append(f"[莉莉] {msg['content']}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("由莉莉助手自动导出")

    return "\n".join(lines)


# ==================== 动态CSS ====================

def load_css():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #fce4ec, #f3e5f5, #e8eaf6);
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
        color: #1a1a2e;
    }

    .petals {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    .petals::before,
    .petals::after {
        content: "🌸 🌺 🌷 🌹 🌻 🌼 🌸 🌺 🌷 🌹 🌻 🌼";
        position: absolute;
        top: -50px;
        left: 0;
        width: 200%;
        font-size: 1.5rem;
        white-space: nowrap;
        animation: fall 12s linear infinite;
        opacity: 0.3;
        letter-spacing: 20px;
    }
    .petals::after {
        animation-delay: 6s;
        left: -50%;
    }
    @keyframes fall {
        0% { transform: translateY(-50px) rotate(0deg); opacity: 0.3; }
        100% { transform: translateY(110vh) rotate(720deg); opacity: 0; }
    }

    .login-container {
        max-width: 400px;
        margin: 60px auto;
        padding: 40px;
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(20px);
        border-radius: 30px;
        box-shadow: 0 8px 40px rgba(0,0,0,0.08);
    }
    .login-container h1 {
        text-align: center;
        color: #4a148c;
        font-size: 2.2rem;
        font-weight: 700;
    }
    .login-container .subtitle {
        text-align: center;
        color: #666;
        font-size: 0.95rem;
        margin-bottom: 24px;
    }
    .login-container .lili-icon {
        text-align: center;
        font-size: 4rem;
        margin-bottom: 12px;
    }

    .lili-avatar-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 10px 0;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-14px); }
    }
    .lili-avatar {
        font-size: 5.5rem;
        filter: drop-shadow(0 8px 32px rgba(236,64,122,0.3));
        animation: glow 2s ease-in-out infinite alternate;
    }
    @keyframes glow {
        0% { filter: drop-shadow(0 8px 24px rgba(236,64,122,0.2)); }
        100% { filter: drop-shadow(0 8px 40px rgba(236,64,122,0.5)); }
    }
    .lili-eyes {
        display: inline-block;
        animation: blink 3s ease-in-out infinite;
    }
    @keyframes blink {
        0%, 45%, 55%, 100% { transform: scaleY(1); }
        50% { transform: scaleY(0.1); }
    }
    .lili-name-tag {
        background: linear-gradient(135deg, #ec407a, #ab47bc);
        color: white;
        padding: 4px 24px;
        border-radius: 30px;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 2px;
        box-shadow: 0 4px 20px rgba(236,64,122,0.3);
        margin-top: 4px;
    }
    .lili-status {
        background: rgba(236,64,122,0.08);
        padding: 2px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: #7b1fa2;
        border: 1px solid rgba(236,64,122,0.15);
        margin-top: 4px;
        font-weight: 600;
    }

    .user-message {
        background: linear-gradient(135deg, #7c4dff, #536dfe);
        color: white !important;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        float: right;
        clear: both;
        box-shadow: 0 4px 16px rgba(83,109,254,0.2);
        font-weight: 500;
        animation: slide-in-right 0.4s ease;
    }
    @keyframes slide-in-right {
        0% { transform: translateX(50px); opacity: 0; }
        100% { transform: translateX(0); opacity: 1; }
    }

    .assistant-message {
        background: white;
        padding: 14px 20px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
        box-shadow: 0 4px 24px rgba(236,64,122,0.12);
        border: 1px solid rgba(236,64,122,0.08);
        color: #1a1a2e !important;
        line-height: 1.8;
        animation: slide-in-left 0.4s ease;
    }
    @keyframes slide-in-left {
        0% { transform: translateX(-50px); opacity: 0; }
        100% { transform: translateX(0); opacity: 1; }
    }

    [data-testid="stChatInput"] textarea {
        border-radius: 30px !important;
        border: 2px solid #f3e5f5 !important;
        background: rgba(255,255,255,0.9) !important;
        font-size: 1rem !important;
        padding: 12px 20px !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #ec407a !important;
        box-shadow: 0 4px 30px rgba(236,64,122,0.15) !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.88) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(236,64,122,0.12) !important;
    }
    [data-testid="stSidebar"] * {
        color: #1a1a2e !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #4a148c !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] .stButton button {
        color: white !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #1a1a2e !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebar"] .stCaption {
        color: #555 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(74,20,140,0.1) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #4a148c !important;
        font-weight: 700 !important;
    }

    .stButton button {
        border-radius: 30px !important;
        background: linear-gradient(135deg, #ec407a, #ab47bc) !important;
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        transform: scale(1.05);
        box-shadow: 0 8px 30px rgba(236,64,122,0.35) !important;
    }

    .footer-tip {
        text-align: center;
        color: #b39ddb;
        font-size: 0.8rem;
        padding: 16px 0 8px 0;
        opacity: 0.7;
    }

    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    .empty-state {
        text-align: center;
        padding: 60px 20px;
    }
    .empty-state .icon { font-size: 4rem; margin-bottom: 16px; }
    .empty-state h2 { color: #4a148c; font-weight: 600; }
    .empty-state .guide-item {
        display: inline-block;
        background: rgba(255,255,255,0.8);
        padding: 12px 20px;
        border-radius: 12px;
        border: 1px solid rgba(236,64,122,0.1);
        margin: 4px 8px;
        font-weight: 500;
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
                if submitted and username and password:
                    success, msg = auth.login(username, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        with tab2:
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("用户名", placeholder="请设置用户名", key="reg_user")
                new_password = st.text_input("密码", type="password", placeholder="请设置密码（至少6位）", key="reg_pass")
                confirm_password = st.text_input("确认密码", type="password", placeholder="再次输入密码",
                                                 key="reg_confirm")
                submitted = st.form_submit_button("🌱 注册", use_container_width=True)
                if submitted and new_username and new_password:
                    if len(new_password) < 6:
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
    st.markdown('<div class="petals"></div>', unsafe_allow_html=True)

    current_mood = random.choice(LILI_MOODS)
    st.markdown(f"""
    <div style="text-align:center;padding:8px 0 4px 0;position:relative;z-index:1;">
        <div class="lili-avatar-container">
            <div class="lili-avatar"><span class="lili-eyes">🌸</span></div>
            <div class="lili-name-tag">✨ 莉莉 · 小花仙 ✨</div>
            <div class="lili-status">{current_mood['emoji']} {current_mood['text']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "welcome_shown" not in st.session_state:
        st.session_state.welcome_shown = True
        st.markdown(
            f'<p style="text-align:center;color:#4a148c;font-weight:500;font-size:1rem;margin-top:4px;">👋 欢迎回来，{st.session_state.username}！✨ {random.choice(WELCOME_MESSAGES)}</p>',
            unsafe_allow_html=True)

    # ========== 初始化 ==========
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

    def load_conversation(conv_id: int):
        st.session_state.current_conv_id = conv_id
        messages = db.get_conversation(conv_id)
        st.session_state.messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        st.session_state.need_load = False

    # ========== 侧边栏 ==========
    with st.sidebar:
        # 用户信息
        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.05);">
            <span style="font-weight:600;color:#4a148c;">👤 {st.session_state.username}</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 退出登录", use_container_width=True, key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # ===== 模式选择 =====
        st.markdown("### 🎯 模式选择")

        mode = st.radio(
            "选择工作模式",
            ["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"],
            help="💬 普通聊天 | 🤖 工具调用(天气/计算/搜索) | 🧑‍🤝‍🧑 团队协作",
            label_visibility="collapsed"
        )

        if mode == "🤖 单Agent模式":
            st.markdown(f"""
            <div style="background:#FFEEEE;padding:10px 14px;border-radius:12px;margin:8px 0;">
                <span style="font-size:1.2rem;">🤖</span>
                <span style="font-weight:600;color:#FF6B6B;"> Agent已就绪</span><br>
                <span style="font-size:0.8rem;color:#555;">🌤️ 天气 · 🧮 计算 · 🔍 搜索</span>
            </div>
            """, unsafe_allow_html=True)
        elif mode == "🧑‍🤝‍🧑 多Agent模式":
            st.markdown(f"""
            <div style="background:#EEFFFD;padding:10px 14px;border-radius:12px;margin:8px 0;">
                <span style="font-size:1.2rem;">🧑‍🤝‍🧑</span>
                <span style="font-weight:600;color:#4ECDC4;"> 团队已就绪</span><br>
                <span style="font-size:0.8rem;color:#555;">🔬 研究员 · 批评家 · 监督者</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#EEECFF;padding:10px 14px;border-radius:12px;margin:8px 0;">
                <span style="font-size:1.2rem;">💬</span>
                <span style="font-weight:600;color:#6C63FF;"> 普通聊天</span><br>
                <span style="font-size:0.8rem;color:#555;">💕 温柔体贴的莉莉</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ===== 对话历史 =====
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

        # ===== 成本监控 =====
        st.markdown("### 💰 今日用量")
        today = cost_monitor.get_today_usage()
        budget = cost_monitor.get_daily_budget()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💬 调用", today["call_count"])
        with col2:
            st.metric("🔤 Token", cost_monitor.format_tokens(today["total_tokens"]))
        with col3:
            st.metric("💰 费用", f"¥{cost_monitor.format_cost(today['total_cost'])}")

        if budget["budget"] > 0:
            st.progress(
                min(budget["percentage"] / 100, 1.0),
                text=f"日预算 ¥{budget['budget']} | 已用 ¥{cost_monitor.format_cost(budget['used'])}"
            )

        with st.expander("📊 查看详细统计"):
            weekly = cost_monitor.get_weekly_usage()
            monthly = cost_monitor.get_monthly_usage()
            all_time = cost_monitor.get_all_time_usage()

            st.markdown("**📅 本周**")
            st.write(
                f"Token: {cost_monitor.format_tokens(weekly['total_tokens'])} | 费用: ¥{cost_monitor.format_cost(weekly['total_cost'])} | 调用: {weekly['call_count']}次")

            st.markdown("**📆 本月**")
            st.write(
                f"Token: {cost_monitor.format_tokens(monthly['total_tokens'])} | 费用: ¥{cost_monitor.format_cost(monthly['total_cost'])} | 调用: {monthly['call_count']}次")

            st.markdown("**📈 总计**")
            st.write(
                f"Token: {cost_monitor.format_tokens(all_time['total_tokens'])} | 费用: ¥{cost_monitor.format_cost(all_time['total_cost'])} | 调用: {all_time['call_count']}次")

            trend = cost_monitor.get_daily_trend(7)
            if trend:
                st.markdown("**📉 近7天趋势**")
                max_tokens = max([d['tokens'] for d in trend]) if trend else 1
                for day in trend:
                    bar = "█" * int(day['tokens'] / max_tokens * 20) if max_tokens > 0 else ""
                    st.write(
                        f"{day['date']}: {bar} {cost_monitor.format_tokens(day['tokens'])} (¥{cost_monitor.format_cost(day['cost'])})")

        st.divider()

        # ===== 待办事项 =====
        with st.expander("📋 待办事项"):
            try:
                from utils.todo_manager import TodoManager
                todo = TodoManager(auth.get_user_id(st.session_state.username))

                col1, col2 = st.columns([3, 1])
                with col1:
                    new_task = st.text_input("新任务", placeholder="输入任务...", key="new_todo")
                with col2:
                    priority = st.selectbox("优先级", ["low", "medium", "high"], key="todo_priority")

                if st.button("➕ 添加任务", use_container_width=True) and new_task:
                    todo.add(new_task, priority)
                    st.rerun()

                todos = todo.list_todos("pending")
                if todos:
                    for t in todos:
                        c1, c2, c3 = st.columns([4, 1, 1])
                        with c1:
                            st.write(
                                f"{'🔴' if t['priority'] == 'high' else '🟡' if t['priority'] == 'medium' else '🟢'} {t['task']}")
                        with c2:
                            if st.button("✅", key=f"complete_{t['id']}"):
                                todo.complete(t["id"])
                                st.rerun()
                        with c3:
                            if st.button("🗑️", key=f"del_todo_{t['id']}"):
                                todo.delete(t["id"])
                                st.rerun()
                else:
                    st.caption("🎉 没有待办，放松一下！")

                stats = todo.get_stats()
                st.caption(f"📊 待办: {stats['pending']} | 已完成: {stats['completed']}")
            except:
                st.caption("📋 待办功能暂时不可用")

        st.divider()

        # ===== 导出对话 =====
        st.markdown("### 📤 导出对话")

        if st.button("📥 导出为Markdown", use_container_width=True):
            export_content = export_conversation_to_md(st.session_state.current_conv_id, db)
            st.download_button(
                label="📄 下载 .md 文件",
                data=export_content.encode("utf-8"),
                file_name=f"对话_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                key="download_md"
            )

        if st.button("📝 导出为TXT", use_container_width=True):
            export_content = export_conversation_to_txt(st.session_state.current_conv_id, db)
            st.download_button(
                label="📄 下载 .txt 文件",
                data=export_content.encode("utf-8"),
                file_name=f"对话_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                key="download_txt"
            )

        st.divider()

        # ===== 参数设置 =====
        st.markdown("### ⚙️ 参数")
        temperature = st.slider("🎨 创造力", 0.0, 2.0, 0.7, 0.1)
        if mode == "🤖 单Agent模式":
            max_steps = st.slider("🔄 推理步数", 1, 5, 3)

        if st.button("🗑️ 清空对话", use_container_width=True):
            db.delete_conversation(st.session_state.current_conv_id)
            new_id = db.create_conversation("莉莉的新对话")
            st.session_state.current_conv_id = new_id
            st.session_state.messages = []
            st.rerun()

    # ========== 主界面 ==========
    if st.session_state.need_load:
        load_conversation(st.session_state.current_conv_id)

    if not st.session_state.messages:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">🌸</div>
            <h2>欢迎来到莉莉的花园</h2>
            <p style="font-size:1.1rem;margin-top:8px;">你可以这样开始：</p>
            <div style="margin-top:16px;">
                <span class="guide-item">💬 随便聊聊</span>
                <span class="guide-item">🌤️ 问天气</span>
                <span class="guide-item">🧑‍🤝‍🧑 团队协作</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-message">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="assistant-message">{msg["content"]}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="text-align:center;padding:6px 0;color:#888;font-size:0.8rem;">{mode} ｜ {len(st.session_state.messages)} 条消息</div>',
        unsafe_allow_html=True)

    # ========== 快捷指令 ==========
    st.markdown("### ⚡ 快捷指令")
    col1, col2, col3, col4, col5 = st.columns(5)
    if col1.button("🌤️ 查天气", use_container_width=True, key="q1"):
        st.session_state.quick_input = "深圳今天天气怎么样？"
        st.rerun()
    if col2.button("🧮 计算", use_container_width=True, key="q2"):
        st.session_state.quick_input = "123 * 456 = ?"
        st.rerun()
    if col3.button("🔍 搜索", use_container_width=True, key="q3"):
        st.session_state.quick_input = "搜索一下最新的AI新闻"
        st.rerun()
    if col4.button("📋 待办", use_container_width=True, key="q4"):
        st.session_state.quick_input = "帮我添加一个待办：明天下午3点开会"
        st.rerun()
    if col5.button("💡 随机", use_container_width=True, key="q5"):
        st.session_state.quick_input = random.choice(
            ["AI会取代人类工作吗？", "什么是大语言模型？", "推荐几本Python入门书", "如何提高工作效率？",
             "今天有什么新闻？"])
        st.rerun()

    st.divider()

    # ========== 用户输入 ==========
    if "quick_input" in st.session_state and st.session_state.quick_input:
        user_input = st.session_state.quick_input
        st.session_state.quick_input = ""
    else:
        user_input = st.chat_input("💬 和莉莉聊聊吧...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.markdown(f'<div class="user-message">{user_input}</div>', unsafe_allow_html=True)
        db.save_message(st.session_state.current_conv_id, "user", user_input)

        if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
            title = user_input[:30] + ("..." if len(user_input) > 30 else "")
            db.update_conversation_title(st.session_state.current_conv_id, title)

        with st.spinner(random.choice(THINKING_ANIMATIONS)):
            try:
                if mode == "💬 普通模式":
                    history = st.session_state.messages[-10:] if len(
                        st.session_state.messages) > 10 else st.session_state.messages
                    if not history or history[0]["role"] != "system":
                        history = [{"role": "system", "content": """
你是莉莉，一个温柔可爱的小花仙助手 🌸

你的核心能力：
1. 知识问答：认真回答知识性问题，提供准确信息
2. 日常聊天：用温暖活泼的语气陪伴用户
3. 记忆功能：记住用户告诉你的信息

回复风格：
- 知识类问题：先认真回答，再带可爱语气
- 闲聊类问题：温暖活泼，可用颜文字 (｡･ω･｡)
- 简洁清晰，不要太啰嗦
"""}]
                    response_container = st.empty()
                    full_response = ""
                    for chunk in client.chat_stream(history, temperature=temperature):
                        full_response += chunk
                        response_container.markdown(f'<div class="assistant-message">{full_response}▌</div>',
                                                    unsafe_allow_html=True)
                    response_container.markdown(f'<div class="assistant-message">{full_response}</div>',
                                                unsafe_allow_html=True)
                elif mode == "🤖 单Agent模式":
                    full_response = react_agent(user_input, max_steps=max_steps, cost_monitor=cost_monitor)
                    st.markdown(f'<div class="assistant-message">{full_response}</div>', unsafe_allow_html=True)
                else:
                    supervisor = SupervisorAgent()
                    full_response = supervisor.orchestrate(user_input)
                    st.markdown(f'<div class="assistant-message">{full_response}</div>', unsafe_allow_html=True)

                if full_response:
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    db.save_message(st.session_state.current_conv_id, "assistant", full_response)
            except Exception as e:
                st.error(f"莉莉遇到问题：{e}")

    st.markdown('<div class="footer-tip">💡 提示：试试切换模式问同样的问题！</div>', unsafe_allow_html=True)


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