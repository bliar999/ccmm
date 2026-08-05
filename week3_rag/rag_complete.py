from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters   import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from openai import OpenAI
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# 1. 初始化OpenAI客户端（DeepSeek）
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# 2. 初始化向量库
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# 如果向量库存在，直接加载；否则先构建
db_path = "./chroma_db"
if Path(db_path).exists():
    print("加载已有向量库...")
    vector_store = Chroma(persist_directory=db_path, embedding_function=embeddings)
else:
    print("构建新的向量库...")
    # 这里需要先加载和分割文档
    txt_path = "docs/sample.txt"
    loader = TextLoader(txt_path, encoding="utf-8")
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=40)
    chunks = splitter.split_documents(documents)
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_path
    )
    print(f"构建完成，含 {len(chunks)} 个片段")


# 3. RAG问答函数
def rag_ask(question):
    # 检索相关片段
    docs = vector_store.similarity_search(question, k=3)
    context = "\n\n".join([doc.page_content for doc in docs])

    # 构建提示词
    prompt = f"""
请根据以下参考内容回答用户的问题。如果参考内容中没有相关信息，请如实说"根据现有文档无法回答该问题"。

【参考内容】
{context}

【用户问题】
{question}

【回答】
"""

    # 调用大模型
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content


# 4. 测试
if __name__ == "__main__":
    questions = [
        "什么是人工智能？",
        "RAG技术有什么作用？",
        "深度学习和大语言模型有什么关系？",
        "今天天气怎么样？"  # 这个应该答"无法回答"
    ]

    for q in questions:
        print(f"\n{'=' * 50}")
        print(f"问题: {q}")
        print(f"{'=' * 50}")
        answer = rag_ask(q)
        print(f"回答:\n{answer}")