from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. 加载已存的向量库
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

vector_store = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings
)

# 2. 测试检索
questions = [
    "什么是人工智能？",
    "RAG是什么技术？",
    "深度学习是怎么工作的？"
]

for q in questions:
    print(f"\n{'=' * 50}")
    print(f"问题: {q}")
    print(f"{'=' * 50}")

    # 检索最相关的3个片段
    results = vector_store.similarity_search(q, k=3)

    for i, doc in enumerate(results):
        print(f"\n--- 相关片段{i + 1} ---")
        print(f"内容: {doc.page_content}")
        print(f"相似度评分: 见元数据（首次检索无分数）")