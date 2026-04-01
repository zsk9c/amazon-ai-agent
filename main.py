from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult
from schemas import ProductRequest
# ==========================================
# 1. 优先注入网关探针 (绝对物理隔离：必须在导入 worker 之前执行)
# ==========================================
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource 
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor # 引入 Celery 发报机

resource = Resource(attributes={
    "service.name": "amazon-ai-gateway" 
})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# ==========================================
# 2. 探针就绪后，再导入业务逻辑
# ==========================================
from worker import process_analysis_task

app = FastAPI(title="Amazon AI Agent Gateway V6.0")

# 激活 FastAPI 路由监控 和 Celery 任务下发监控
FastAPIInstrumentor.instrument_app(app)
CeleryInstrumentor().instrument()

# 解决前后端分离导致的跨域问题 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 接口 1：任务派发端 (非阻塞)
@app.post("/api/analyze")
async def start_analyze(request: ProductRequest):
    if request.invite_code != "626":
        raise HTTPException(status_code=403, detail="授权失败：非法的系统访问令牌。")
        
    if not request.url and not request.user_query:
        raise HTTPException(status_code=400, detail="协议错误：必须提供商品链接或检索问题。")

    # 此时，CeleryInstrumentor 会自动把 Trace ID 塞进任务的 Header 里！
    task = process_analysis_task.delay(request.url, request.user_query)
    
    return {"task_id": task.id, "status": "Task dispatched to Celery Worker."}

# 接口 2：状态轮询端
@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {"state": task_result.state, "status": "任务正在排队中..."}
    elif task_result.state == 'PROGRESS':
        return {"state": task_result.state, "status": task_result.info.get('status', '')}
    elif task_result.state == 'SUCCESS':
        if "error" in task_result.info:
            return {"state": "FAILURE", "error": task_result.info["error"]}
        return {"state": task_result.state, "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"state": task_result.state, "error": str(task_result.info)}
    
    return {"state": task_result.state}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")