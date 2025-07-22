from typing import Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class Users(BaseModel):
    username: str
    password_hash: str

class URLs(BaseModel):
    original_url: str
    short_code: str
    owner_id: str  
    created_at: str  
    expire_at: str = None
    click_count: int = 0  

class URLRequest(BaseModel):
    original_url: HttpUrl
    expire_minutes: Optional[int] = None  


class URLResponse(BaseModel):
    short_url: str
    remaining_quota: int
    qr_code: str

# class URLInDB(BaseModel):
#     original_url: str
#     short_code: str
#     owner_id: str  
#     created_at: str  
#     click_count: int = 0  