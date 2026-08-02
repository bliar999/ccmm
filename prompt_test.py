from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")

# 第一次：不加角色
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "请写一份程序员年终总结"}],
    temperature=0.7
)
print("【不加角色】\n", response.choices[0].message.content)

# 第二次：加角色
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一位技术总监，需要严格考核下属绩效"},
        {"role": "user", "content": "请写一份程序员年终总结"}
    ],
    temperature=0.7
)
print("\n【加角色：技术总监】\n", response.choices[0].message.content)