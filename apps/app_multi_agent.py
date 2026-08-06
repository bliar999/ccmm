"""
莉莉 - 趣味界面版
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

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import ChatHistoryDB
from utils.api_client import DeepSeekClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==================== 趣味配置 ====================

# 莉莉的趣味欢迎语
WELCOME_MESSAGES = [
    "✨ 嗨！我是莉莉，今天想聊点什么？",
    "🌸 你来啦！我正等你呢～",
    "💫 莉莉已上线，随时为你服务！",
    "🌺 今天的心情怎么样？和我分享吧！",
    "🎀 莉莉在此，有何吩咐？",
    "💕 见到你真开心！"
]

# 莉莉的思考状态
THINKING_MESSAGES = [
    "莉莉正在思考... 🤔",
    "莉莉在翻小本本... 📖",
    "莉莉在认真听你说... 👂",
    "莉莉在组织语言... ✍️",
    "莉莉在回忆知识点... 🧠"
]

# 模式对应的图标和颜色
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


# ==================== 自定义CSS ====================

def load_css():
    st.markdown("""
    <style>
    /* 全局字体和背景 */
    .stApp {
        background: linear-gradient(135deg, #fdf2f8 0%, #fce4ec 50%, #f3e5f5 100%);
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }

    /* 标题区域 */
    .lili-header {
        text-align: center;
        padding: 20px 0 10px 0;
        background: linear-gradient(135deg, #ec407a, #ab47bc);
        border-radius: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(236, 64, 122, 0.3);
    }
    .lili-header h1 {
        font-size: 2.5rem;
        color: white;
        margin: 0;
        font-weight: 700;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .lili-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin: 5px 0 0 0;
    }

    /* 聊天消息 */
    .user-message {
        background: linear-gradient(135deg, #e8eaf6, #c5cae9);
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        float: right;
        clear: both;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        color: #1a1a2e;
    }
    .assistant-message {
        background: linear-gradient(135deg, #ffffff, #f5f5f5);
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
        box-shadow: 0 2px 12px rgba(236, 64, 122, 0.15);
        border: 1px solid rgba(236, 64, 122, 0.1);
        color: #1a1a2e;
    }

    /* 侧边栏美化 */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.7);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.3);
    }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #4a148c;
    }

    /* 模式选择卡片 */
    .mode-card {
        padding: 12px 16px;
        border-radius: 12px;
        margin: 6px 0;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    .mode-card:hover {
        transform: translateX(4px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }
    .mode-card-selected {
        border-color: #ec407a;
        background: rgba(236, 64, 122, 0.08);
        box-shadow: 0 4px 16px rgba(236, 64, 122, 0.15);
    }

    /* 输入框美化 */
    [data-testid="stChatInput"] textarea {
        border-radius: 25px !important;
        border: 2px solid #f3e5f5 !important;
        background: rgba(255,255,255,0.8) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #ec407a !important;
        box-shadow: 0 4px 30px rgba(236, 64, 122, 0.15) !important;
    }

    /* 按钮美化 */
    .stButton button {
        border-radius: 25px !important;
        background: linear-gradient(135deg, #ec407a, #ab47bc) !important;
        color: white !important;
        border: none !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 20px rgba(236, 64, 122, 0.4) !important;
    }

    /* 状态提示 */
    .status-bubble {
        display: inline-block;
        padding: 4px 16px;
        border-radius: 20px;
        background: rgba(236, 64, 122, 0.1);
        color: #ec407a;
        font-size: 0.9rem;
        font-weight: 500;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* 莉莉头像 */
    .lili-avatar {
        font-size: 4rem;
        text-align: center;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    /* 底部提示 */
    .footer-tip {
        text-align: center;
        color: #9e9e9e;
        font-size: 0.8rem;
        padding: 20px 0 10px 0;
        opacity: 0.7;
    }
    </style>
    """, unsafe_allow_html=True)


# ==================== Streamlit UI ====================

load_css()

# ========== 头部 ==========
st.markdown("""
<div class="lili-header">
    <div class="lili-avatar">🌸</div>
    <h1>莉莉</h1>
    <p>💬 普通聊天 ｜ 🤖 工具调用 ｜ 🧑‍🤝‍🧑 团队协作</p>
</div>
""", unsafe_allow_html=True)

# 随机欢迎语
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = True
    st.caption(random.choice(WELCOME_MESSAGES))


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

    # 模式状态显示
    mode_info = MODE_CONFIG.get(mode, {})
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

# 显示聊天消息
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-message">👤 {msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "assistant":
        st.markdown(f'<div class="assistant-message">🌸 {msg["content"]}</div>', unsafe_allow_html=True)

# 状态信息
st.markdown(
    f'<div style="text-align:center;padding:6px 0;color:#aaa;font-size:0.75rem;">{mode} ｜ {len(st.session_state.messages)} 条消息</div>',
    unsafe_allow_html=True)

# ========== 用户输入 ==========
user_input = st.chat_input("💬 和莉莉聊聊吧...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(f'<div class="user-message">👤 {user_input}</div>', unsafe_allow_html=True)
    db.save_message(st.session_state.current_conv_id, "user", user_input)

    if db.get_conversation_title(st.session_state.current_conv_id) == "莉莉的新对话":
        title = user_input[:30] + ("..." if len(user_input) > 30 else "")
        db.update_conversation_title(st.session_state.current_conv_id, title)

    with st.spinner(random.choice(THINKING_MESSAGES)):
        try:
            if mode == "💬 普通模式":
                history = st.session_state.messages[-10:] if len(
                    st.session_state.messages) > 10 else st.session_state.messages
                if not history or history[0]["role"] != "system":
                    history = [{"role": "system", "content": "你是莉莉，一个温柔体贴的AI助手"}] + history
                response = client.chat_with_history(history, temperature=temperature)
            elif mode == "🤖 单Agent模式":
                response = react_agent(user_input, max_steps=max_steps)
            else:
                supervisor = SupervisorAgent()
                response = supervisor.orchestrate(user_input)

            st.markdown(f'<div class="assistant-message">🌸 {response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": response})
            db.save_message(st.session_state.current_conv_id, "assistant", response)

        except Exception as e:
            st.error(f"莉莉遇到问题：{e}")

# ========== 底部 ==========
st.markdown(f'<div class="footer-tip">💡 提示：试试切换模式问同样的问题！</div>', unsafe_allow_html=True)
