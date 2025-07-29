from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = None

class TagInDBBase(TagBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Tag(TagInDBBase):
    pass

class TagWithPosts(TagInDBBase):
    # Usar la anotación correcta para forward reference
    posts: List["Post"] = []

# Importación circular al final del archivo
from app.schemas.post import Post
TagWithPosts.model_rebuild()