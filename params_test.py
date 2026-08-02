from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")

# 实验参数组合
experiments = [
    {"temp": 0, "top_p": 1, "label": "实验1: 完全确定"},
    {"temp": 1.5, "top_p": 1, "label": "实验2: 高随机性"},
    {"temp": 0.7, "top_p": 0.9, "label": "实验3: 默认推荐"},
    {"temp": 0.3, "top_p": 0.5, "label": "实验4: 保守集中"}
]

question = "请推荐3本适合程序员读的哲学书"

for exp in experiments:
    print(f"\n{'=' * 50}")
    print(f"【{exp['label']}】")
    print(f"Temperature={exp['temp']}, Top_p={exp['top_p']}")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": question}],
        temperature=exp["temp"],
        top_p=exp["top_p"]
    )

    print("输出结果：")
    print(response.choices[0].message.content)
    print("-" * 30)