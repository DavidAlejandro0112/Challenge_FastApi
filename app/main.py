from fastapi import FastAPI
from app.api.main import api_router
from app.core.database import engine, Base
import asyncio

app = FastAPI(title="FastAPI Blog API", version="1.0.0")

app.include_router(api_router, prefix="/api")

# @app.get("/")
# async def root():
#     return {"message": "Welcome to FastAPI Blog API"}

# @app.on_event("startup")
# async def startup_event():
#     pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)