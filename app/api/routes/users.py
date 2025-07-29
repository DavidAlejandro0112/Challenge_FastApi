from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
# from app.core.dependencies import get_current_active_user
from app.crud import user as crud_user
from app.crud import post as crud_post
from app.schemas.user import User, UserCreate, UserUpdate, UserWithPosts
from app.schemas.post import Post

router = APIRouter(prefix="/users", tags=["users"])

# Endpoints públicos (sin autenticación)
@router.get("/", response_model=list[User])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Obtener lista de usuarios (público)"""
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserWithPosts)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Obtener usuario por ID (público)"""
    db_user = await crud_user.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Endpoints protegidos (requieren autenticación)
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(crud_user.get_current_active_user)
):
    db_user = await crud_user.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await crud_user.create_user(db=db, user=user)

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int, 
    user: UserUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(crud_user.get_current_active_user)
):
    # Verificar permisos (solo el propio usuario o admin)
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db_user = await crud_user.update_user(db, user_id=user_id, user_update=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(crud_user.get_current_active_user)
):
    """
    Eliminar usuario (protegido)
    
    Solo usuarios autenticados pueden eliminar usuarios.
    """
    # Verificar permisos (solo el propio usuario o admin)
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    success = await crud_user.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.post("/{user_id}/restore", response_model=User)
async def restore_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(crud_user.get_current_active_user)
):
    # Verificar permisos (solo administradores)
    # Aquí puedes agregar lógica para verificar si es admin
    
    success = await crud_user.restore_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deleted user not found")
    db_user = await crud_user.get_user(db, user_id=user_id)
    return db_user

@router.get("/{user_id}/posts", response_model=list[Post])
async def read_user_posts(
    user_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """Obtener posts de un usuario (público)"""
    posts = await crud_post.get_posts_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return posts

@router.get("/deleted/", response_model=list[User])
async def read_deleted_users(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(crud_user.get_current_active_user)
):
    users = await crud_user.get_deleted_users(db, skip=skip, limit=limit)
    return users