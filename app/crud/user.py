from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from typing import List, Optional
from jose import JWTError, jwt
from app.core.config import settings
from app.schemas.auth import TokenData
from datetime import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(
        select(User).filter(and_(User.email == email, User.is_deleted == False))
    )
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(select(User).filter(User.is_deleted == False).offset(skip).limit(limit))
    return list(result.scalars().all())

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(**user.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    if db_user.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot update a deleted user")
    
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    db_user = await get_user(db, user_id)
    if db_user:
        db_user.is_deleted = True
        db_user.deleted_at = datetime.utcnow()
        await db.commit()
        return True
    return False

async def restore_user(db: AsyncSession, user_id: int) -> bool:
    db_user = await get_user(db, user_id)
    if db_user and db_user.is_deleted:
        db_user.is_deleted = False
        db_user.deleted_at = None
        await db.commit()
        return True
    return False

async def get_deleted_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(
        select(User)
        .filter(User.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(User.deleted_at.desc())
    )
    return list(result.scalars().all())

async def get_current_user(
    db: AsyncSession = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):  # Verificación explícita
            raise credentials_exception
        token_data = TokenData(username=username)  # Asegúrate que TokenData.username sea str
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(db, username=token_data.username)
    if user is None or user.is_deleted:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.is_deleted:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user