from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from schemas import ProductRequest

# 同时引入两个时代的引擎
from scraper import scrape_amazon_reviews
from vector_db import search_memories
from ai_agent import analyze_reviews_with_ai, analyze_reviews_with_ai_with_rag

app = FastAPI(title="Amazon SaaS AI Agent (V3.0 Hybrid)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze")
def analyze_product_route(request: ProductRequest):
    if request.invite_code != "626":
        raise HTTPException(status_code=401, detail="邀请码错误")

    try:
        # 核心路由逻辑：如果有 URL，走在线爬虫；如果没有，走本地 RAG
        if request.url and request.url.strip() != "":
            print("【丘脑路由分配】 -> 模式 1：启动在线实时爬虫引擎")
            reviews_text = scrape_amazon_reviews(request.url, target_count=20)
            
            if not reviews_text:
                return {"pain_points": ["抓取失败，触发了风控或无数据"], "selling_proposals": ["无"], "auto_reply_template": "无"}
                
            final_report = analyze_reviews_with_ai(reviews_text)
            return final_report
            
        else:
            print("【丘脑路由分配】 -> 模式 2：启动本地 RAG 记忆检索引擎")
            search_query = request.user_query or "critical complaints or best features"
            context_text = search_memories(search_query, k=15)
            
            if not context_text:
                return {"pain_points": ["记忆库中未找到相关评论"], "selling_proposals": ["无法提炼"], "auto_reply_template": "无"}

            final_report = analyze_reviews_with_ai_with_rag(context_text, request.user_query)
            return final_report

    except Exception as e:
        print(f"执行出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("正在启动 Amazon SaaS AI Agent 双引擎服务...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)