from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str  
    is_active: bool
    is_admin: bool
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

class UserWithPosts(UserInDBBase):
    posts: List["Post"] = []

# Importaciones circulares
from app.schemas.post import Post
UserWithPosts.model_rebuild()