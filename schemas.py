from pydantic import BaseModel
from typing import Optional

class ProductRequest(BaseModel):
    url: Optional[str] = None       # 标记为可选
    invite_code: str
    user_query: Optional[str] = None # 标记为可选