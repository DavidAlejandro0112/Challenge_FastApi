import logging
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from app.api.main import api_router
from app.middleware.logging import ResponseTimeMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FastAPI Blog API", version="1.0.0")


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# middleware
app.add_middleware(ResponseTimeMiddleware)


app.include_router(api_router, prefix="/api")


@app.get("/", include_in_schema=False, response_class=RedirectResponse)
async def redirect_to_swagger():
    logger.info("Redirect to swagger...")
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
