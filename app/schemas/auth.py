from pydantic import BaseModel, validator
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str  
    
    # Validación adicional para asegurar que no sea string vacío
    @validator('username')
    def validate_username(cls, value):
        if not value.strip():
            raise ValueError("Username cannot be empty")
        return value

class UserAuth(BaseModel):
    username: str
    email: str
    full_name: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    full_name: str