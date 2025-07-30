from pydantic import BaseModel
from typing import Optional, List

class ErrorDetail(BaseModel):
    loc: List[str]  # Ubicación del error (ej: ["body", "email"])
    msg: str       # Mensaje descriptivo
    type: str      # Tipo de error (ej: "value_error")

class APIError(BaseModel):
    success: bool = False
    message: str
    details: Optional[List[ErrorDetail]] = None