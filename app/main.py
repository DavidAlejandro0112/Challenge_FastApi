from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from app.api.main import api_router
from app.middleware.logging import ResponseTimeMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings


app = FastAPI(title="FastAPI Blog API", version="1.0.0")


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# middleware
app.add_middleware(ResponseTimeMiddleware)


app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
