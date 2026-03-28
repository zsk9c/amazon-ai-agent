# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import ProductRequest
from scraper import scrape_amazon_reviews
from ai_agent import analyze_reviews_with_ai

app = FastAPI(title="Amazon Review AI Analyzer V2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze")
def analyze_product(request: ProductRequest):
    # 物理防御锁
    if request.invite_code != "626":
        raise HTTPException(status_code=401, detail="邀请码错误或未授权，拒绝访问")

    try:
        print(f"开始处理请求，目标 URL: {request.url}")
        
        # 模块 1：调用独立爬虫层
        reviews_text = scrape_amazon_reviews(request.url, target_count=30)
        
        if not reviews_text:
            return {"pros": ["未抓取到数据"], "cons": ["页面滚动深度可能依然不足，或亚马逊启用了强风控。"]}

        # 模块 2：调用独立大脑层
        final_report = analyze_reviews_with_ai(reviews_text)

        print("AI 处理完成，已返回给前端！")
        return final_report

    except Exception as e:
        print(f"执行出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))