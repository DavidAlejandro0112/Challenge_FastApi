from fastapi import FastAPI
from app.api.main import api_router
from app.core.database import engine, Base
import asyncio
from app.middleware.logging import ResponseTimeMiddleware 


app = FastAPI(title="FastAPI Blog API", version="1.0.0")

# middleware
app.add_middleware(ResponseTimeMiddleware)


app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)