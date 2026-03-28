from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from schemas import ProductRequest
# 废弃 scraper.py
from vector_db import search_memories
from ai_agent import analyze_reviews_with_ai_with_rag # 使用 RAG 版大脑

app = FastAPI(title="Amazon SaaS AI Agent (V3.0 RAG)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze")
def analyze_product_with_rag(request: ProductRequest):
    if request.invite_code != "626":
        raise HTTPException(status_code=401, detail="邀请码错误")

    try:
        # 如果用户没填问题，我们就用一个通用的、能覆盖全局的情绪词来检索
        search_query = request.user_query or "critical complaints or best features"
        
        print(f"收到请求。正在为模拟产品进行 RAG 语义检索，问题: {search_query}...")
        
        # 模块 1：调用本地向量记忆引擎进行精准召回
        context_text = search_memories(search_query, k=15)
        
        if not context_text:
            return {"pain_points": ["记忆库中未找到相关评论"], "selling_proposals": ["无法提炼"], "auto_reply_template": "N/A"}

        # 模块 2：调用独立版本大脑层，进行三维商业深度报告提炼
        final_report = analyze_reviews_with_ai_with_rag(context_text, request.user_query)

        print("RAG 商业分析完成！")
        return final_report

    except Exception as e:
        print(f"执行出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("正在启动 Amazon SaaS AI Agent 服务...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)