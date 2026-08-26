"""
莉莉 - 完整版（已接入高德地图API真实天气）
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

# ==================== 导入 ====================
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


# ==================== 对话数据库 ====================

class ChatHistoryDB:
    def __init__(self, user_id: int = None):
        self.db_path = Path(__file__).parent.parent / "chat_history.db"
        self.user_id = user_id
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS conversations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           title
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           updated_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           message_count
                           INTEGER
                           DEFAULT
                           0
                       )
                       """)
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS messages
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           conversation_id
                           INTEGER
                           NOT
                           NULL,
                           role
                           TEXT
                           NOT
                           NULL,
                           content
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       """)
        conn.commit()
        conn.close()

    def create_conversation(self, title: str = "新对话") -> int:
        if self.user_id is None:
            raise ValueError("未设置 user_id")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (self.user_id, title)
        )
        conv_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return conv_id

    def save_message(self, conversation_id: int, role: str, content: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        cursor.execute(
            "UPDATE conversations SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        conn.commit()
        conn.close()

    def get_conversation(self, conversation_id: int) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in rows]

    def get_conversation_title(self, conversation_id: int) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "未命名对话"

    def update_conversation_title(self, conversation_id: int, title: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        conn.commit()
        conn.close()

    def list_conversations(self, limit: int = 50) -> list:
        if self.user_id is None:
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, message_count FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (self.user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "title": row[1], "message_count": row[2]} for row in rows]

    def delete_conversation(self, conversation_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        conn.close()


# ==================== DeepSeek API 调用 ====================

class DeepSeekClient:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            try:
                self.api_key = st.secrets.get("DEEPSEEK_API_KEY")
            except:
                pass

    def chat_with_history(self, messages, temperature=0.7) -> str:
        if not self.api_key:
            return "⚠️ API Key 未设置，请在 .env 或 Secrets 中配置 DEEPSEEK_API_KEY"

        client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com/v1")
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ 调用失败：{str(e)}"


# ==================== 高德地图API（真实天气） ====================

def get_weather_amap(city: str) -> dict:
    """使用高德地图API查询真实天气"""
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("AMAP_API_KEY")
        except:
            pass

    if not api_key:
        return {"error": "❌ 高德API Key未配置，请在.env或Secrets中设置 AMAP_API_KEY"}

    try:
        # 1. 地理编码：获取城市adcode
        geo_url = "https://restapi.amap.com/v3/geocode/geo"
        geo_params = {"key": api_key, "address": city}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_data = geo_resp.json()

        if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
            return {"error": f"未找到城市：{city}"}

        adcode = geo_data["geocodes"][0]["adcode"]

        # 2. 查询天气
        weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        weather_params = {"key": api_key, "city": adcode, "extensions": "all"}
        weather_resp = requests.get(weather_url, params=weather_params, timeout=10)
        weather_data = weather_resp.json()

        if weather_data.get("status") != "1":
            return {"error": "天气查询失败，请稍后重试"}

        forecast = weather_data["forecasts"][0]
        casts = forecast.get("casts", [])

        if not casts:
            return {"error": "暂无天气数据"}

        today = casts[0]
        tomorrow = casts[1] if len(casts) > 1 else None

        return {
            "city": forecast["city"],
            "today": {
                "date": today.get("date", ""),
                "weather": today.get("dayweather", ""),
                "temperature": f"{today.get('nighttemp', '')}°C ~ {today.get('daytemp', '')}°C",
                "wind": today.get("daywind", ""),
                "daytemp": today.get("daytemp", ""),
                "nighttemp": today.get("nighttemp", ""),
                "dayweather": today.get("dayweather", ""),
                "nightweather": today.get("nightweather", "")
            },
            "tomorrow": {
                "date": tomorrow.get("date", ""),
                "weather": tomorrow.get("dayweather", ""),
                "temperature": f"{tomorrow.get('nighttemp', '')}°C ~ {tomorrow.get('daytemp', '')}°C"
            } if tomorrow else None
        }

    except requests.exceptions.Timeout:
        return {"error": "请求超时，请稍后重试"}
    except Exception as e:
        return {"error": f"查询失败：{str(e)}"}


# ==================== 工具函数（数学计算 + 搜索） ====================

def calculate(expression: str) -> dict:
    """数学计算"""
    allowed_chars = r'[\d+\-*/().% ]'
    if not re.match(f'^{allowed_chars}+$', expression):
        return {"expression": expression, "error": "表达式包含非法字符", "result": None}
    try:
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return {"expression": expression, "result": result, "error": None}
    except Exception as e:
        return {"expression": expression, "result": None, "error": str(e)}


def web_search(query: str) -> dict:
    """模拟网络搜索"""
    return {
        "query": query,
        "results": [
            {"title": f"关于 '{query}' 的搜索结果 1", "content": "这是模拟搜索结果的内容"},
            {"title": f"关于 '{query}' 的搜索结果 2", "content": "这是模拟搜索结果的内容"}
        ]
    }


def get_weather_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气，支持中国城市",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如：北京、上海、深圳"}
                },
                "required": ["city"]
            }
        }
    }


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


def get_search_tool_desc():
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索网络信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        }
    }


# ==================== 单Agent 核心 ====================

TOOLS = {
    "get_weather": {"function": get_weather_amap, "description": get_weather_tool_desc()},
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
    """单Agent主函数"""
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
1. get_weather - 查询城市天气（支持中国城市）
2. calculate - 执行数学计算
3. web_search - 搜索网络信息
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
        <div style="max-width:400px;margin:0 auto;padding:40px;background:rgba(255,255,255,0.85);border-radius:30px;box-shadow:0 8px 40px rgba(0,0,0,0.08);">
            <div style="text-align:center;font-size:4rem;margin-bottom:12px;">🌸</div>
            <h1 style="text-align:center;color:#4a148c;font-size:2.2rem;">莉莉的花园</h1>
            <p style="text-align:center;color:#888;margin-bottom:24px;">登录进入你的专属AI花园</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🌺 登录", "🌱 注册"])

        with tab1:
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("用户名", placeholder="请输入用户名")
                password = st.text_input("密码", type="password", placeholder="请输入密码")
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
                new_username = st.text_input("用户名", placeholder="请设置用户名")
                new_password = st.text_input("密码", type="password", placeholder="请设置密码（至少6位）")
                confirm_password = st.text_input("确认密码", type="password", placeholder="再次输入密码")
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
    # ========== 初始化数据库 ==========
    user_id = auth.get_user_id(st.session_state.username)
    db = ChatHistoryDB(user_id=user_id)
    client = DeepSeekClient()

    # ========== 初始化对话状态 ==========
    if "current_conv_id" not in st.session_state:
        convs = db.list_conversations(1)
        if convs:
            st.session_state.current_conv_id = convs[0]["id"]
        else:
            st.session_state.current_conv_id = db.create_conversation("新对话")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "need_load" not in st.session_state:
        st.session_state.need_load = True

    if st.session_state.need_load:
        st.session_state.messages = db.get_conversation(st.session_state.current_conv_id)
        st.session_state.need_load = False

    # =============================================
    # ========== 侧边栏（完整版） ==========
    # =============================================
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")

        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

        st.divider()

        st.markdown("### 🎯 模式选择")
        mode = st.radio(
            "选择模式",
            ["💬 普通模式", "🤖 单Agent模式", "🧑‍🤝‍🧑 多Agent模式"],
            label_visibility="collapsed"
        )

        if mode == "🤖 单Agent模式":
            st.info("🌤️ 天气 · 🧮 计算 · 🔍 搜索")
        elif mode == "🧑‍🤝‍🧑 多Agent模式":
            st.info("🔬 研究员 · 批评家 · 监督者")
        else:
            st.info("💕 温柔体贴的莉莉")

        st.divider()

        st.markdown("### 📜 对话历史")

        if st.button("➕ 新建对话", use_container_width=True):
            new_id = db.create_conversation("新对话")
            st.session_state.current_conv_id = new_id
            st.session_state.messages = []
            st.session_state.need_load = False
            st.rerun()

        conversations = db.list_conversations(20)
        for conv in conversations:
            col1, col2 = st.columns([4, 1])
            with col1:
                is_current = conv["id"] == st.session_state.current_conv_id
                title = conv["title"][:15] + "..." if len(conv["title"]) > 15 else conv["title"]
                label = f"🟢 {title}" if is_current else f"📄 {title}"
                if st.button(label, key=f"load_{conv['id']}", use_container_width=True):
                    st.session_state.current_conv_id = conv["id"]
                    st.session_state.messages = db.get_conversation(conv["id"])
                    st.session_state.need_load = False
                    st.rerun()
                st.caption(f"{conv['message_count']}条")
            with col2:
                if st.button("🗑️", key=f"del_{conv['id']}"):
                    db.delete_conversation(conv["id"])
                    st.rerun()

        st.divider()

        st.markdown("### ⚙️ 参数")
        temperature = st.slider("🎨 创造力", 0.0, 2.0, 0.7, 0.1)

        st.divider()
        st.caption("🌸 莉莉 v2.0 | 已接入高德天气")

    # =============================================
    # ========== 主界面 ==========
    # =============================================

    st.title("🌸 莉莉")
    st.caption("🌤️ 已接入高德地图真实天气 · 你的专属AI小助手")

    # ---- 显示消息 ----
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # ---- 快捷指令 ----
    cols = st.columns(4)
    with cols[0]:
        if st.button("🌤️ 查天气", use_container_width=True):
            st.session_state.quick_input = "深圳今天天气怎么样？"
            st.rerun()
    with cols[1]:
        if st.button("🧮 计算", use_container_width=True):
            st.session_state.quick_input = "123 * 456 = ?"
            st.rerun()
    with cols[2]:
        if st.button("🔍 搜索", use_container_width=True):
            st.session_state.quick_input = "搜索一下最新的AI新闻"
            st.rerun()
    with cols[3]:
        if st.button("💡 随机", use_container_width=True):
            questions = ["什么是大语言模型？", "AI会取代人类工作吗？", "推荐几本Python入门书"]
            st.session_state.quick_input = random.choice(questions)
            st.rerun()

    # ---- 输入框 ----
    if "quick_input" in st.session_state and st.session_state.quick_input:
        user_input = st.session_state.quick_input
        st.session_state.quick_input = ""
    else:
        user_input = st.chat_input("💬 和莉莉聊聊吧...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        db.save_message(st.session_state.current_conv_id, "user", user_input)

        if db.get_conversation_title(st.session_state.current_conv_id) == "新对话":
            title = user_input[:20] + "..." if len(user_input) > 20 else user_input
            db.update_conversation_title(st.session_state.current_conv_id, title)

        with st.spinner("莉莉正在思考..."):
            try:
                if mode == "💬 普通模式":
                    history = [{"role": "system", "content": "你是莉莉，一个温柔可爱的AI助手。回答要简洁清晰、有帮助。"}]
                    for msg in st.session_state.messages[-10:]:
                        history.append(msg)
                    response = client.chat_with_history(history, temperature=temperature)

                elif mode == "🤖 单Agent模式":
                    response = react_agent(user_input, max_steps=3)

                else:
                    # 多Agent模式（简化版）
                    response = f"🧑‍🤝‍🧑 多Agent团队正在分析你的问题...\n\n{react_agent(user_input, max_steps=2)}"

                st.chat_message("assistant").write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                db.save_message(st.session_state.current_conv_id, "assistant", response)

            except Exception as e:
                st.error(f"莉莉遇到问题：{e}")

    st.caption("💡 提示：在单Agent模式下输入城市名称可查真实天气")


# ==================== 主入口 ====================

auth = AuthSystem()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

st.set_page_config(page_title="🌸 莉莉", page_icon="🌸", layout="wide")

if not st.session_state.logged_in:
    show_login_page()
else:
    main_app()