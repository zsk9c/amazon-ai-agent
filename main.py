from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from worker import process_analysis_task
from celery.result import AsyncResult

app = FastAPI(title="Amazon AI Agent Gateway V5.0")

# 解决前后端分离导致的跨域问题 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境应严格配置为前端的实际域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str = ""
    user_query: str = ""
    invite_code: str = ""

# 接口 1：任务派发端 (非阻塞)
@app.post("/api/analyze")
async def start_analyze(request: AnalyzeRequest):
    if request.invite_code != "AI2026":
        raise HTTPException(status_code=403, detail="授权失败：非法的系统访问令牌。")
        
    if not request.url and not request.user_query:
        raise HTTPException(status_code=400, detail="协议错误：必须提供商品链接或检索问题。")

    # 将沉重的计算任务推入 Celery 队列，瞬间返回！
    task = process_analysis_task.delay(request.url, request.user_query)
    
    return {"task_id": task.id, "status": "Task dispatched to Celery Worker."}

# 接口 2：状态轮询端
@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    # 根据前端传来的号码牌，去 Redis 查询任务状态
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {"state": task_result.state, "status": "任务正在排队中..."}
    elif task_result.state == 'PROGRESS':
        return {"state": task_result.state, "status": task_result.info.get('status', '')}
    elif task_result.state == 'SUCCESS':
        # 任务完成，返回大模型吐出的最终 JSON 数据
        if "error" in task_result.info:
            return {"state": "FAILURE", "error": task_result.info["error"]}
        return {"state": task_result.state, "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"state": task_result.state, "error": str(task_result.info)}
    
    return {"state": task_result.state}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")