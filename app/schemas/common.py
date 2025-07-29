# app/schemas/common.py
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T') # T puede ser cualquier tipo, incluyendo esquemas Pydantic

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True # Esto es importante para la conversión automática
