import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DataFrameLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 数据库存储路径
DB_DIR = "./chroma_db"
CSV_PATH = "mock_data.csv"

# 1. 初始化免费的 Embedding 模型 (大脑记忆编码器)
# 我们使用一个体积小、效果好的开源小模型，不需要额外花钱调用 API
print("正在加载 Embedding 模型（约需 10 秒），请保持专注...")
# 将 all-MiniLM-L6-v2 替换为 paraphrase-multilingual-MiniLM-L12-v2
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 局部复盘机制：如果数据库已存在，我们就不用每次重新编码
def ingest_data_if_needed():
    if os.path.exists(DB_DIR):
        print("本地向量记忆库已存在，直接读取...")
        return Chroma(persist_directory=DB_DIR, embedding_function=embedding_model)

    print("数据库不存在，开始进行长时程增强 (Ingestion) 的数据编码与存储...")
    
    # A. Pandas 读取脏数据
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"未找到模拟数据大文件: {CSV_PATH}")
    df = pd.DataFrame(pd.read_csv(CSV_PATH))
    df.dropna(inplace=True)
    df = df[df['ReviewText'].str.len() > 10]
    
    # B. LangChain 加载与物理切块 (Chunking)
    loader = DataFrameLoader(df, page_content_column="ReviewText")
    docs = loader.load()
    
    # 核心：将长评论切成小块（Chunk），防止大模型认知超载
    # 设想如果一万条评论，我们只要最精准的那几十个 Chunk
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    splits = text_splitter.split_documents(docs)
    print(f"原始大文件已被物理切块为 {len(splits)} 个高质量记忆片段。")
    
    # C. 存入 ChromaDB (向量数据库固化记忆)
    print("开始将记忆片段向量化并存入磁盘数据库，这需要消耗部分脑力，请调整呼吸...")
    vector_store = Chroma.from_documents(
        documents=splits, 
        embedding=embedding_model, 
        persist_directory=DB_DIR
    )
    print("长时程增强成功！所有模拟评论已永久固化在本地。")
    return vector_store

# 2. 对外暴露精准记忆调取接口 (Semantic Search)
def search_memories(user_query: str, k: int = 5):
    # 确保数据库加载
    vector_store = ingest_data_if_needed()
    # 执行语义相似度检索，取出最精准的 K 个相关评论片段
    results = vector_store.similarity_search(user_query, k=k)
    
    # ==========================================
    # 终极物理防线：利用哈希集合 (Set) 进行 O(1) 极速去重
    # ==========================================
    unique_texts = []
    seen_hashes = set()
    
    for doc in results:
        # 获取纯文本并去除首尾空白
        content = doc.page_content.strip()
        
        # 如果这个文本之前没出现过，才将其加入最终列表
        if content not in seen_hashes:
            seen_hashes.add(content)
            unique_texts.append(content)
            
    # 将绝对唯一的干净结果拼接返回给大模型
    return "\n---\n".join(unique_texts)
# ==========================================
# 物理执行触发器 (扳机)
# ==========================================
if __name__ == "__main__":
    print("\n[系统级指令] -> 独立运行此脚本，强制触发向量化入库程序...")
    ingest_data_if_needed()