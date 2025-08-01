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
    author: "User"  # ← Cadena
    comments: List["Comment"] = []
    tags: List["Tag"] = []  # ← Cadena

    class Config:
        from_attributes = True


# Importaciones circulares al final
from app.schemas.user import User
from app.schemas.comment import Comment
from app.schemas.tag import Tag

# Reconstruye después de importar
PostWithRelations.model_rebuild()
