import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Configurar logger
logger = logging.getLogger("response_time")
logger.setLevel(logging.INFO)

# Si no hay handlers, añadir uno
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Registrar el tiempo de inicio
        start_time = time.time()
        
        # Procesar la solicitud
        response = await call_next(request)
        
        # Calcular el tiempo de respuesta
        process_time = time.time() - start_time
        
        # Registrar el tiempo de respuesta
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Response Time: {process_time:.4f}s"
        )
        
        # Agregar el tiempo de respuesta como header
        response.headers["X-Response-Time"] = f"{process_time:.4f}s"
        
        return response