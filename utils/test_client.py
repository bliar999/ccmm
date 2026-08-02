from utils.api_client import DeepSeekClient

client = DeepSeekClient()
response = client.chat("请用一句话介绍你自己", system="你是个感性的AI")
print(response)