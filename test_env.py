from pathlib import Path
from dotenv import load_dotenv
import os

# PyCharm专用：强制从当前脚本目录加载.env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("DEEPSEEK_API_KEY")
if api_key:
    print(f"✅ 成功读到Key: {api_key[:8]}...")
else:
    print("❌ 没读到Key，请检查.env文件位置")