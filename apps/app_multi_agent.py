"""
莉莉 - 动态卡通人物版
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
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import ChatHistoryDB
from utils.api_client import DeepSeekClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==================== 动态配置 ====================

# 莉莉的心情状态
LILI_MOODS = [
    {"emoji": "💕", "text": "今天心情超好！", "color": "#ec407a"},
    {"emoji": "🌸", "text": "春暖花开～", "color": "#ab47bc"},
    {"emoji": "✨", "text": "元气满满！", "color": "#7c4dff"},
    {"emoji": "🌙", "text": "有点困了 zzz", "color": "#5c6bc0"},
    {"emoji": "🎀", "text": "今天超可爱！", "color": "#ef5350"},
    {"emoji": "🌟", "text": "等你很久啦！", "color": "#ffa726"}
]

# 思考时的动态文案
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

MODE_CONFIG = {
    "💬 普通模式": {"icon": "💬", "color": "#6C63FF", "bg": "#EEECFF"},
    "🤖 单Agent模式": {"icon": "🤖", "color": "#FF6B6B", "bg": "#FFEEEE"},
    "🧑‍🤝‍🧑 多Agent模式": {"icon": "🧑‍🤝‍🧑", "color": "#4ECDC4", "bg": "#EEFFFD"}
}


# ==================== 单Agent 工具函数 ====================

def get_current_time(timezone: str = "Asia/Shanghai", format_type: str = "full") -> dict:
    try:
        import pytz
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        formats = {
            "full": now.strftime("%Y年%m月%d日 %H:%M:%S %Z"),
            "date": now.strftime("%Y年%m月%d日"),
            "time": now.strftime("%H:%M:%S")
        }
        return {
            "timezone": timezone,
            "formatted": formats.get(format_type, formats["full"]),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "weekday": ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
        }
    except:
        return {"formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def get_time_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "时区，默认 Asia/Shanghai"},
                    "format_type": {"type": "string", "enum": ["full", "date", "time"], "default": "full"}
                }
            }
        }
    }


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


def web_search(query: str, max_results: int = 3) -> dict:
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        results = []
        if data.get("Abstract"):
            results.append({"title": "摘要", "content": data["Abstract"][:500], "source": data.get("AbstractURL", "")})
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if "Text" in topic:
                results.append({"title": topic.get("Text", "")[:50], "content": topic.get("Text", ""),
                                "source": topic.get("FirstURL", "")})
        if not results:
            results = [{"title": f"关于 '{query}' 的搜索结果", "content": f"搜索 '{query}' 的相关信息", "source": ""}]
        return {"query": query, "results": results[:max_results], "count": len(results)}
    except Exception as e:
        return {"query": query, "error": f"搜索失败：{str(e)}", "results": []}


def get_search_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索网络上的最新信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "max_results": {"type": "integer", "description": "返回结果数量，默认3", "default": 3}
                },
                "required": ["query"]
            }
        }
    }


# ==================== 单Agent 核心 ====================

TOOLS = {
    "get_current_time": {"function": get_current_time, "description": get_time_tool_desc()},
    "calculate": {"function": calculate, "description": get_calc_tool_desc()},
    "web_search": {"function": web_search, "description": get_search_tool_desc()}
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


def react_agent(question: str, max_steps: int = 3):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("DEEPSEEK_API_KEY")
        except:
            pass
    if not api_key:
        return "❌ API Key未设置，请检查环境变量"

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    messages = [
        {"role": "system",
         "content": "你是莉莉，一个智能助手。你能调用工具来帮助回答问题。当用户需要实时信息、计算、或搜索时，使用相应的工具。"},
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

    return "抱歉，我思考太久了，请换个问题试试。"


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
        system_prompt = "你是莉莉团队中的【研究员】。你的职责是深入研究问题，收集信息，用结构化方式呈现发现。"
        super().__init__(name="研究员", role="信息收集与分析", system_prompt=system_prompt)


class CriticAgent(BaseAgent):
    def __init__(self):
        system_prompt = "你是莉莉团队中的【批评家】。你的职责是对研究结果提出质疑，找出漏洞，提出改进建议。"
        super().__init__(name="批评家", role="质疑与完善", system_prompt=system_prompt)


class SupervisorAgent(BaseAgent):
    def __init__(self):
        system_prompt = "你是莉莉团队的【监督者】，负责分配任务、协调团队、汇总结果。"
        super().__init__(name="监督者", role="任务分配与协调", system_prompt=system_prompt)

    def orchestrate(self, question: str) -> str:
        researcher = ResearcherAgent()
        research_result = researcher.think(question)
        critic = CriticAgent()
        critique = critic.think(f"请评阅以下研究结果：\n{research_result}")
        summary = self.think(f"""
请基于以下信息生成完整回答：
【研究员的发现】{research_result}
【批评家的建议】{critique}
【用户问题】{question}
请整合以上信息，给出全面平衡的回答。
""")
        return summary


# ==================== 动态CSS ====================

def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #fce4ec 0%, #f3e5f5 40%, #e8eaf6 100%);
        font-family: 'Quicksand', 'PingFang SC', sans-serif;
        overflow-x: hidden;
    }

    /* ===== 花瓣飘落动画 ===== */
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
    .petal {
        position: absolute;
        top: -20px;
        font-size: 1.5rem;
        animation: fall linear infinite;
        opacity: 0.6;
    }
    @keyframes fall {
        0% { transform: translateY(-20px) rotate(0deg) translateX(0); opacity: 0.6; }
        100% { transform: translateY(110vh) rotate(720deg) translateX(100px); opacity: 0; }
    }

    /* ===== 莉莉头像呼吸浮动 ===== */
    .lili-avatar-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 10px 0;
        animation: lili-float 3s ease-in-out infinite;
        position: relative;
        z-index: 1;
    }
    @keyframes lili-float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-14px) rotate(-2deg); }
    }

    .lili-avatar {
        font-size: 5.5rem;
        line-height: 1.2;
        filter: drop-shadow(0 8px 32px rgba(236, 64, 122, 0.3));
        transition: all 0.3s ease;
        animation: lili-glow 2s ease-in-out infinite alternate;
    }
    @keyframes lili-glow {
        0% { filter: drop-shadow(0 8px 24px rgba(236, 64, 122, 0.2)); }
        100% { filter: drop-shadow(0 8px 40px rgba(236, 64, 122, 0.5)); }
    }
    .lili-avatar:hover {
        transform: scale(1.15) rotate(-8deg);
    }

    /* ===== 眨眼动画 ===== */
    .lili-eyes {
        display: inline-block;
        animation: blink 3s ease-in-out infinite;
    }
    @keyframes blink {
        0%, 45%, 55%, 100% { transform: scaleY(1); }
        50% { transform: scaleY(0.1); }
    }

    /* ===== 思考旋转动画 ===== */
    .thinking-spin {
        display: inline-block;
        animation: spin 1.5s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* ===== 名字标签 ===== */
    .lili-name-tag {
        background: linear-gradient(135deg, #ec407a, #ab47bc);
        color: white;
        padding: 4px 24px;
        border-radius: 30px;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 2px;
        box-shadow: 0 4px 20px rgba(236, 64, 122, 0.3);
        margin-top: 4px;
        animation: tag-pulse 2s ease-in-out infinite;
    }
    @keyframes tag-pulse {
        0%, 100% { box-shadow: 0 4px 20px rgba(236, 64, 122, 0.3); }
        50% { box-shadow: 0 4px 40px rgba(236, 64, 122, 0.5); }
    }

    /* ===== 状态标签 ===== */
    .lili-status {
        background: rgba(236, 64, 122, 0.08);
        padding: 2px 16px;
        border-radius: 20px;
        font-size: 0.75rem;
        color: #ec407a;
        border: 1px solid rgba(236, 64, 122, 0.15);
        margin-top: 4px;
        animation: status-pulse 2s ease-in-out infinite;
        font-weight: 600;
    }
    @keyframes status-pulse {
        0%, 100% { opacity: 0.7; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.03); }
    }

    /* ===== 消息弹出动画 ===== */
    .user-message {
        background: linear-gradient(135deg, #7c4dff, #536dfe);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        float: right;
        clear: both;
        box-shadow: 0 4px 16px rgba(83, 109, 254, 0.2);
        font-weight: 500;
        animation: slide-in-right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
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
        box-shadow: 0 4px 24px rgba(236, 64, 122, 0.12);
        border: 1px solid rgba(236, 64, 122, 0.08);
        color: #1a1a2e;
        line-height: 1.7;
        animation: slide-in-left 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    @keyframes slide-in-left {
        0% { transform: translateX(-50px); opacity: 0; }
        100% { transform: translateX(0); opacity: 1; }
    }

    /* ===== 打字机光标 ===== */
    .typing-cursor {
        display: inline-block;
        width: 2px;
        height: 1.2em;
        background: #ec407a;
        margin-left: 2px;
        animation: cursor-blink 0.8s step-end infinite;
    }
    @keyframes cursor-blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }

    /* ===== 输入框发光 ===== */
    [data-testid="stChatInput"] textarea {
        border-radius: 30px !important;
        border: 2px solid #f3e5f5 !important;
        background: rgba(255,255,255,0.85) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04) !important;
        font-size: 1rem !important;
        padding: 12px 20px !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #ec407a !important;
        box-shadow: 0 4px 30px rgba(236, 64, 122, 0.15) !important;
        animation: input-glow 1s ease-in-out infinite alternate;
    }
    @keyframes input-glow {
        0% { box-shadow: 0 4px 30px rgba(236, 64, 122, 0.1); }
        100% { box-shadow: 0 4px 50px rgba(236, 64, 122, 0.25); }
    }

    /* ===== 侧边栏 ===== */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.6) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255,255,255,0.3) !important;
    }

    /* ===== 按钮 ===== */
    .stButton button {
        border-radius: 30px !important;
        background: linear-gradient(135deg, #ec407a, #ab47bc) !important;
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 16px rgba(236, 64, 122, 0.25) !important;
    }
    .stButton button:hover {
        transform: scale(1.05) translateY(-2px);
        box-shadow: 0 8px 30px rgba(236, 64, 122, 0.35) !important;
    }
    .stButton button:active {
        transform: scale(0.95);
    }

    /* ===== 页脚 ===== */
    .footer-tip {
        text-align: center;
        color: #b39ddb;
        font-size: 0.75rem;
        padding: 16px 0 8px 0;
        opacity: 0.7;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)


# ==================== 花瓣飘落 HTML ====================

def render_petals():
    petals = ["🌸", "🌺", "🌷", "🌹", "🌻", "🌼"]
    petal_html = '<div class="petals">'
    for i in range(12):
        petal = random.choice(petals)
        delay = random.uniform(0, 8)
        duration = random.uniform(6, 12)
        left = random.uniform(0, 95)
        size = random.uniform(1, 2.5)
        petal_html += f'''
        <div class="petal" style="
            left: {left}%;
            font-size: {size}rem;
            animation-delay: {delay}s;
            animation-duration: {duration}s;
        ">{petal}</div>
        '''
    petal_html += '</div>'
    return petal_html


# ==================== Streamlit UI ====================

load_css()

# 花瓣飘落
st.markdown(render_petals(), unsafe_allow_html=True)

# ========== 莉莉动态头像 ==========
# 随机心情
current_mood = random.choice(LILI_MOODS)

st.markdown(f"""
<div style="text-align:center;padding:8px 0 4px 0;position:relative;z-index:1;">
    <div class="lili-avatar-container">
        <div class="lili-avatar">
            <span class="lili-eyes">🌸</span>
        </div>
        <div class="lili-name-tag">✨ 莉莉 · 小花仙 ✨</div>
        <div class="lili-status">{current_mood['emoji']} {current_mood['text']}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 随机欢迎语
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = True
    st.markdown(
        f'<p style="text-align:center;color:#7b1fa2;font-weight:500;font-size:1rem;margin-top:4px;position:relative;z-index:1;">✨ {random.choice(WELCOME_MESSAGES)}</p>',
        unsafe_allow_html=True)


# ========== 初始化 ==========
@st.cache_resource
def get_db():
    return ChatHistoryDB()


@st.cache_resource
def get_client():
    return DeepSeekClient()


db = get_db()
client = get_client()

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
    st.markdown("### 🎯 模式选择")

    mode = st.radio(
        "选择工作模式",
        ["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"],
        help="💬 普通聊天 | 🤖 工具调用 | 🧑‍🤝‍🧑 团队协作",
        label_visibility="collapsed"
    )

    if mode == "🤖 单Agent模式":
        st.markdown(f"""
        <div style="background:#FFEEEE;padding:10px 14px;border-radius:12px;margin:8px 0;">
            <span style="font-size:1.2rem;">🤖</span>
            <span style="font-weight:600;color:#FF6B6B;"> Agent已就绪</span><br>
            <span style="font-size:0.8rem;color:#888;">⚡ 时间查询 · 计算 · 搜索</span>
        </div>
        """, unsafe_allow_html=True)
    elif mode == "🧑‍🤝‍🧑 多Agent模式":
        st.markdown(f"""
        <div style="background:#EEFFFD;padding:10px 14px;border-radius:12px;margin:8px 0;">
            <span style="font-size:1.2rem;">🧑‍🤝‍🧑</span>
            <span style="font-weight:600;color:#4ECDC4;"> 团队已就绪</span><br>
            <span style="font-size:0.8rem;color:#888;">🔬 研究员 · 批评家 · 监督者</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#EEECFF;padding:10px 14px;border-radius:12px;margin:8px 0;">
            <span style="font-size:1.2rem;">💬</span>
            <span style="font-weight:600;color:#6C63FF;"> 普通聊天</span><br>
            <span style="font-size:0.8rem;color:#888;">💕 温柔体贴的莉莉</span>
        </div>
        """, unsafe_allow_html=True)

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

# 显示消息
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-message">{msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "assistant":
        st.markdown(f'<div class="assistant-message">{msg["content"]}</div>', unsafe_allow_html=True)

st.markdown(
    f'<div style="text-align:center;padding:6px 0;color:#aaa;font-size:0.75rem;">{mode} ｜ {len(st.session_state.messages)} 条消息</div>',
    unsafe_allow_html=True)

# ========== 用户输入 ==========
user_input = st.chat_input("💬 和莉莉聊聊吧...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(f'<div class="user-message">{user_input}</div>', unsafe_allow_html=True)
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    # 动态思考提示
    thinking_text = random.choice(THINKING_ANIMATIONS)
    with st.spinner(thinking_text):
        try:
            if mode == "💬 普通模式":
                history = st.session_state.messages[-10:] if len(
                    st.session_state.messages) > 10 else st.session_state.messages
                if not history or history[0]["role"] != "system":
                    history = [{"role": "system", "content": """
你是莉莉，一个温柔可爱的小花仙助手 🌸

你的性格特点：
- 温柔、活泼、偶尔调皮
- 喜欢用颜文字，比如 (｡･ω･｡) 和 ✨
- 回答问题时会带一点可爱的语气词，如"呢～""哦～"
- 对用户很关心，会主动问"今天心情怎么样呀？"

你的回复风格：
- 开头可以用 "🌸 莉莉来啦～" 或 "✨ 莉莉知道！"
- 回答完问题后可以加一句关心的话
- 如果用户不开心，安慰一下

记住：你是莉莉，不是普通的AI助手，要展现出你独特的可爱个性！
"""}]
                response = client.chat_with_history(history, temperature=temperature)
            elif mode == "🤖 单Agent模式":
                response = react_agent(user_input, max_steps=max_steps)
            else:
                supervisor = SupervisorAgent()
                response = supervisor.orchestrate(user_input)

            st.markdown(f'<div class="assistant-message">{response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": response})
            db.save_message(st.session_state.current_conv_id, "assistant", response)

        except Exception as e:
            st.error(f"莉莉遇到问题：{e}")

st.markdown('<div class="footer-tip">💡 提示：试试切换模式问同样的问题！</div>', unsafe_allow_html=True)