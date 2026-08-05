from langchain_community.document_loaders import TextLoader

# 加载TXT
txt_path = "sample.txt"
loader = TextLoader(txt_path, encoding="utf-8")
documents = loader.load()

print(f"加载了 {len(documents)} 个文档片段")
print(f"内容:\n{documents[0].page_content}")