from pydantic import BaseModel, Field
from typing import Optional, List

# ==========================================
# 防线一：网关进水口 (Frontend -> FastAPI)
# ==========================================
class ProductRequest(BaseModel):
    url: Optional[str] = None       # 标记为可选
    invite_code: str
    user_query: Optional[str] = None # 标记为可选

# ==========================================
# 防线二：算力出水口 (LLM -> Celery -> Redis)
# ==========================================
class AIAnalysisResult(BaseModel):
    """
    大模型输出的刚性约束模板。
    """
    pain_points: List[str] = Field(
        ..., 
        description="基于缺陷提炼建议。必须为字符串列表。",
        min_length=1
    )
    
    selling_proposals: List[str] = Field(
        ..., 
        description="基于赞点提炼卖点。必须为字符串列表。",
        min_length=1
    )
    
    auto_reply_template: str = Field(
        ..., 
        description="用于安抚客户的专业客服邮件模板。必须为纯字符串。",
        min_length=10 
    )