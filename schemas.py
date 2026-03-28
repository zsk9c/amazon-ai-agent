# schemas.py
from pydantic import BaseModel

class ProductRequest(BaseModel):
    url: str
    invite_code: str