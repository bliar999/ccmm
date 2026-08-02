from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")

# 模拟你的工作记录（可以替换成真实内容）
raw_notes = """
上午：修复了登录页面的验证码bug，重构了用户session管理逻辑
下午：参加了需求评审会，讨论了支付模块的接口变更方案
晚上：写了技术文档《Session管理最佳实践》的前三章
"""

prompt = f"""
你是一个项目助理，请将以下零散的工作记录整理成标准日报。
要求：
1. 按"时间段、工作内容、产出物、备注"四列输出Markdown表格
2. 如果某项工作耗时超过2小时，在备注里标⭐
3. 最后总结今日进度百分比（假设今天计划了3项任务）

原始记录：
{raw_notes}
"""

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3  # 低温度保证格式稳定
)

print(response.choices[0].message.content)