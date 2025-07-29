from pydantic_settings import BaseSettings
from typing import Optional
class Settings(BaseSettings):
    # Configuración general
    APP_NAME: str = "FastAPI Blog API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/challengebd"
    
    # Seguridad
    SECRET_KEY: str = "tu_clave_secreta_aqui_cambia_en_produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()