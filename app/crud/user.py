from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from typing import List, Optional

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(**user.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if db_user:
        update_data = user_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    return None

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    db_user = await get_user(db, user_id)
    if db_user:
        db_user.soft_delete()
        await db.commit()
        return True
    return False

async def restore_user(db: AsyncSession, user_id: int) -> bool:
    """Restaura un usuario eliminado"""
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    db_user = result.scalar_one_or_none()
    if db_user and db_user.is_deleted:
        db_user.restore()
        await db.commit()
        return True
    return False

async def get_deleted_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Obtiene usuarios eliminados"""
    result = await db.execute(
        select(User)
        .filter(User.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(User.deleted_at.desc())
    )
    return result.scalars().all()