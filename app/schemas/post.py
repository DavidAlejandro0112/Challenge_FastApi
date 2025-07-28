from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PostBase(BaseModel):
    title: str
    content: str

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostInDBBase(PostBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Post(PostInDBBase):
    pass

class PostWithRelations(PostInDBBase):
    author: "User"
    comments: List["Comment"] = []
    tags: List["Tag"] = []

class CommentBase(BaseModel):
    content: str
    author_name: str

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    post_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Importaciones circulares
from app.schemas.user import User
from app.schemas.tag import Tag
PostWithRelations.model_rebuild()