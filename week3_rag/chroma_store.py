from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. 加载文档
txt_path = "docs/sample.txt"
loader = TextLoader(txt_path, encoding="utf-8")
documents = loader.load()

# 2. 分割
splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=40,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]
)
chunks = splitter.split_documents(documents)
print(f"分割成 {len(chunks)} 个片段")

# 3. Embedding模型
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# 4. 存入Chroma（本地持久化）
db_path = "./chroma_db"
vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=db_path
)

print(f"✅ 成功存入 {len(chunks)} 个片段到 {db_path}")
print(f"向量库包含 {vector_store._collection.count()} 个向量")