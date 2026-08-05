from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 加载文档
txt_path = "sample.txt"
loader = TextLoader(txt_path, encoding="utf-8")
documents = loader.load()

# 不同chunk_size的对比实验
chunk_sizes = [50, 200, 500]

for size in chunk_sizes:
    print(f"\n{'=' * 50}")
    print(f"chunk_size = {size}")
    print(f"{'=' * 50}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=size // 5,  # 重叠部分约20%
        separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]
    )

    chunks = splitter.split_documents(documents)
    print(f"分割成 {len(chunks)} 个片段")

    # 打印前3个片段
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- 片段{i + 1} ---")
        print(chunk.page_content)
        print(f"长度: {len(chunk.page_content)} 字符")