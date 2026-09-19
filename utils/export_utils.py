"""
对话导出工具 - 支持 Markdown / TXT / HTML 格式
"""

from datetime import datetime
from typing import List, Dict


def export_to_markdown(messages: List[Dict], title: str = "莉莉对话记录") -> str:
    """
    导出对话为 Markdown 格式

    参数：
        messages: 对话消息列表 [{"role": "user/assistant", "content": "..."}]
        title: 对话标题

    返回：
        Markdown 格式的字符串
    """
    lines = []
    lines.append(f"# 🌸 {title}")
    lines.append("")
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


def export_to_txt(messages: List[Dict], title: str = "莉莉对话记录") -> str:
    """
    导出对话为 TXT 格式
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"🌸 {title}")
    lines.append(f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"消息数量：{len(messages)} 条")
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


def export_to_html(messages: List[Dict], title: str = "莉莉对话记录") -> str:
    """
    导出对话为 HTML 格式（适合打印/分享）
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background: #faf0f5;
            color: #1a1a2e;
        }}
        .header {{
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid #ec407a;
            margin-bottom: 30px;
        }}
        .header h1 {{ color: #4a148c; font-size: 2rem; margin: 0; }}
        .header .meta {{ color: #888; font-size: 0.9rem; margin-top: 8px; }}
        .message {{
            padding: 12px 18px;
            margin: 12px 0;
            border-radius: 12px;
            max-width: 80%;
        }}
        .message.user {{
            background: linear-gradient(135deg, #7c4dff, #536dfe);
            color: white;
            margin-left: auto;
            text-align: right;
        }}
        .message.assistant {{
            background: white;
            border: 1px solid rgba(236,64,122,0.1);
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }}
        .message .role {{
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 4px;
            opacity: 0.7;
        }}
        .message.user .role {{ color: rgba(255,255,255,0.7); }}
        .message.assistant .role {{ color: #ec407a; }}
        .footer {{
            text-align: center;
            padding: 20px 0;
            margin-top: 30px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 0.8rem;
        }}
        @media print {{
            body {{ margin: 0; padding: 20px; }}
            .message {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌸 {title}</h1>
        <div class="meta">导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ 共 {len(messages)} 条消息</div>
    </div>
"""

    for msg in messages:
        if msg["role"] == "user":
            html += f"""
    <div class="message user">
        <div class="role">👤 用户</div>
        <div>{msg['content']}</div>
    </div>
"""
        elif msg["role"] == "assistant":
            html += f"""
    <div class="message assistant">
        <div class="role">🌸 莉莉</div>
        <div>{msg['content']}</div>
    </div>
"""

    html += f"""
    <div class="footer">
        由莉莉助手自动导出 · 使用 ❤️ 和 🤖 打造
    </div>
</body>
</html>
"""
    return html