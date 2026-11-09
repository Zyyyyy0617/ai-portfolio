import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ---------- 1. Load + Split（对应官方流水线第 1 行） ----------
loader = TextLoader("./hsk_standard.txt", encoding="utf-8")
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
splits = text_splitter.split_documents(docs)

# ---------- 2. Embed + Store（对应官方流水线第 2 行） ----------
# 使用你本地已经 pull 好的 nomic-embed-text 模型
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectordb = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_hsk_db"  # 向量库会存到这个目录
)

# ---------- 3. Retrieve（对应官方流水线第 3 行） ----------
retriever = vectordb.as_retriever(search_kwargs={"k": 2})

# ---------- 4. Prompt + Generate（对应官方流水线第 4 行） ----------
# 使用你本地已有的 qwen2.5:0.5b 模型
llm = ChatOllama(model="qwen2.5:0.5b", temperature=0)

# 定义一个最简 RAG 提示词，把检索到的资料塞进去
prompt = ChatPromptTemplate.from_template("""
你是一个助手。请仅根据以下参考资料回答问题，如果资料中没有相关信息，请直接说“资料中未提及”。

参考资料：
{context}

问题：{question}
""")

# 用 LangChain 的 LCEL 语法串起整个 2-Step 流程
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# ---------- 5. 执行问答（Deploy + Evaluate 的雏形） ----------
if __name__ == "__main__":
    question = "HSK4的词汇量要求是多少？"
    print(f"Q: {question}")
    answer = rag_chain.invoke(question)
    print(f"A: {answer}")
