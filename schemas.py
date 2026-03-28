from pydantic import BaseModel

class ProductRequest(BaseModel):
    url: str               # 暂时作为模拟产品的 ID 触发器
    invite_code: str       # 安全锁
    user_query: str = None  # 新增：用户的具体问题（如果不填则进行全量分析）