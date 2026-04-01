import sys  # 必须引入 sys
import os
from celery import Celery
from dotenv import load_dotenv

from scraper import scrape_amazon_reviews
from vector_db import search_memories
from ai_agent import analyze_reviews_with_ai, analyze_reviews_with_ai_with_rag

# 注意：这里已经删除了 from celery.signals import worker_process_init

from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource 
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# ==========================================
# 算力节点探针：工业级环境嗅探点火机制 (彻底剥离钩子，裸露在顶层)
# ==========================================
# 不用任何函数包裹！当文件被读取时，直接判断当前是被谁启动的。
# 如果是 Uvicorn (FastAPI) 导入的，sys.argv 里面没有 "celery"，探针静默。
# 如果是终端打 `celery -A worker worker` 启动的，条件成立，探针瞬间通电！
if "celery" in sys.argv[0].lower():
    print("\n[系统监控] -> 嗅探到 Celery 算力引擎启动，正在物理植入 OTel 探针...")
    
    resource = Resource(attributes={
        "service.name": "amazon-ai-worker" 
    })
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    CeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()

# ==========================================
# 基础业务配置
# ==========================================
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
            context_text = search_memories(search_query, k=5)
            
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