from fastapi import APIRouter
from app.api.routes import users, posts, tags

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(posts.router)
api_router.include_router(tags.router)