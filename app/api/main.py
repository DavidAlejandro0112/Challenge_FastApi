from fastapi import APIRouter
from app.api.routes import auth, users, posts, tags, comments


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(posts.router)
api_router.include_router(tags.router)
api_router.include_router(comments.router)
