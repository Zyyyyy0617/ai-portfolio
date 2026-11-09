# 官方 RAG 流水线 ↔ 我的代码 5 行映射表

| 官方 RAG 流水线 | llm-universe 对应章节 | 我的 rag_qa.py / assistant_v1.py |
|---|---|---|
| Load + Split 加载与分块 | C3 数据处理：读取、清洗与切片 | TextLoader + RecursiveCharacterTextSplitter(500/50)，读取 HSK 等级标准节选 |
| Embed + Store 向量化入库 | C3 词向量及向量知识库、搭建并使用向量数据库 | OllamaEmbeddings(nomic-embed-text) + Chroma 本地持久化 |
| Retrieve 检索 | C4 基于 LangChain 搭建检索问答链 | retrieve() 取 top-k；use_rag=True 时先查资料再答 |
| Prompt + Generate 拼词与生成 | C4 将 LLM 接入 LangChain | build_prompt() 拼 SYSTEM_HINT + 资料 + 问题，交给 LLM().ask(prefer=...) |
| Deploy + Evaluate 部署与评估 | C4 Streamlit 部署；C5 系统评估与优化 | 本周先做命令行 assistant_v1.py；W7 幻觉对照表作为最朴素评估 |
