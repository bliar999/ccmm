from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")

messages = [
    {"role": "system", "content": "你是我的学习教练，每次回答后主动追问一个相关问题"}
]

print("开始对话（输入exit退出）：")
while True:
    user_input = input("你: ")
    if user_input.lower() == "exit":
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.7
    )

    reply = response.choices[0].message.content
    print(f"AI: {reply}")
    messages.append({"role": "assistant", "content": reply})

    # 打印当前对话轮次（方便观察记忆长度）
    print(f"【当前历史消息数：{len(messages)}条】")