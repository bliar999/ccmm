from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是个诗人"},
        {"role": "user", "content": "请用一句诗形容今天的天气"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)