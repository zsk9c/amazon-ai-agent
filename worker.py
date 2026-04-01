import os
from celery import Celery
from dotenv import load_dotenv

from scraper import scrape_amazon_reviews
from vector_db import search_memories
from ai_agent import analyze_reviews_with_ai, analyze_reviews_with_ai_with_rag

load_dotenv()

celery_app = Celery(
    "amazon_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task(bind=True)
def process_analysis_task(self, url: str = None, user_query: str = None):
    try:
        # 模式 1：在线实时爬虫引擎
        if url and url.strip() != "":
            self.update_state(state='PROGRESS', meta={'status': '启动在线实时爬虫引擎...'})
            
            # 恢复 V3.0 逻辑：强加 target_count 约束
            reviews_text = scrape_amazon_reviews(url, target_count=20)
            
            # 恢复 V3.0 逻辑：绝对安全的空值兜底
            if not reviews_text:
                return {
                    "pain_points": ["抓取引擎拦截：触发了风控机制或该页面无有效文本数据。"], 
                    "selling_proposals": ["无有效数据输入，无法执行特征提炼。"], 
                    "auto_reply_template": "N/A"
                }
                
            self.update_state(state='PROGRESS', meta={'status': '正在执行多脑协同分析...'})
            safe_text = reviews_text[:4000]
            result = analyze_reviews_with_ai(safe_text)
            return result
            
        # 模式 2：本地 RAG 记忆检索引擎
        else:
            self.update_state(state='PROGRESS', meta={'status': '启动本地 RAG 记忆检索引擎...'})
            
            # 恢复 V3.0 逻辑：默认查询词重定向，阻断底层数据库类型异常
            search_query = user_query if user_query and user_query.strip() != "" else "critical complaints or best features"
            
            # 严格按 V3.0 的参数传入，明确指定 k 值
            context_text = search_memories(search_query, k=15)
            
            # 恢复 V3.0 逻辑：记忆检索为空的兜底防御
            if not context_text:
                return {
                    "pain_points": ["记忆检索阻断：本地高维向量库中未匹配到相关评论特征。"], 
                    "selling_proposals": ["缺乏上下文，无法提炼商业卖点。"], 
                    "auto_reply_template": "N/A"
                }
                
            self.update_state(state='PROGRESS', meta={'status': '正在执行 Actor-Critic 幻觉核验...'})
            result = analyze_reviews_with_ai_with_rag(context_text, search_query)
            return result
            
    except Exception as e:
        return {"error": str(e)}