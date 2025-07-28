from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import user as crud_user
from app.crud import post as crud_post
from app.schemas.user import User, UserCreate, UserUpdate, UserWithPosts
from app.schemas.post import Post

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await crud_user.create_user(db=db, user=user)

@router.get("/", response_model=list[User])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserWithPosts)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: int, user: UserUpdate, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.update_user(db, user_id=user_id, user_update=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud_user.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.post("/{user_id}/restore", response_model=User)
async def restore_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Restaura un usuario eliminado"""
    success = await crud_user.restore_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deleted user not found")
    db_user = await crud_user.get_user(db, user_id=user_id)
    return db_user

@router.get("/{user_id}/posts", response_model=list[Post])
async def read_user_posts(user_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    posts = await crud_post.get_posts_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return posts

@router.get("/deleted/", response_model=list[User])
async def read_deleted_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Obtiene usuarios eliminados"""
    users = await crud_user.get_deleted_users(db, skip=skip, limit=limit)
    return users