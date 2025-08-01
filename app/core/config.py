from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Configuración general
    APP_NAME: str = "FastAPI Blog API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Base de datos
    DATABASE_URL: str

    # Seguridad
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    

    # Define el archivo .env
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Ignora campos extra en .env
    }

settings = Settings()# type: ignore