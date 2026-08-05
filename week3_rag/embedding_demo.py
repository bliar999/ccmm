from sentence_transformers import SentenceTransformer
import time

# 加载本地Embedding模型（首次运行会下载约400MB）
print("加载Embedding模型...")
start = time.time()
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
print(f"加载完成，耗时 {time.time()-start:.1f} 秒")

# 测试句子
sentences = [
    "人工智能是计算机科学的分支",
    "大语言模型可以理解和生成文本",
    "RAG结合了检索和生成技术"
]

# 转换为向量
embeddings = model.encode(sentences)

print(f"\n共 {len(embeddings)} 个句子")
print(f"每个向量的维度: {len(embeddings[0])}")
print(f"第一个句子的前10个数值: {embeddings[0][:10]}")

# 计算相似度（验证向量质量）
from sklearn.metrics.pairwise import cosine_similarity
similarity = cosine_similarity([embeddings[0]], [embeddings[1]])
print(f"\n句子1和句子2的相似度: {similarity[0][0]:.4f}")