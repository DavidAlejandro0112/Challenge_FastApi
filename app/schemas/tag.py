# app/schemas/tag.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    pass


class TagInDBBase(TagBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Tag(TagInDBBase):
    pass


class TagWithPosts(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    posts: List["Post"] = []  # ← Cadena

    class Config:
        from_attributes = True


# Importaciones circulares al final
from app.schemas.post import Post

# Reconstruye después de importar
TagWithPosts.model_rebuild()
