from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import  func, and_
from app.models.tag import Tag
from app.models.post import Post
from app.schemas.tag import TagCreate, TagUpdate
from typing import List, Optional, Tuple



async def get_tag(db: AsyncSession, tag_id: int) -> Optional[Tag]:
    result = await db.execute(
        select(Tag)
        .options(selectinload(Tag.posts))
        .filter(and_(Tag.id == tag_id, Tag.is_deleted == False))
    )
    return result.scalar_one_or_none()

async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[Tag]:
    result = await db.execute(
        select(Tag).filter(and_(Tag.name == name, Tag.is_deleted == False))
    )
    return result.scalar_one_or_none()

async def get_tags(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Tag]:
    result = await db.execute(
        select(Tag)
        .options(selectinload(Tag.posts))
        .filter(Tag.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(Tag.created_at.desc())
    )
    return list(result.scalars().all())

async def create_tag(db: AsyncSession, tag: TagCreate) -> Tag:
    db_tag = Tag(**tag.model_dump())
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag

async def update_tag(db: AsyncSession, tag_id: int, tag_update: TagUpdate) -> Optional[Tag]:
    db_tag = await get_tag(db, tag_id)
    if db_tag:
        update_data = tag_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_tag, key, value)
        db_tag.updated_at = func.now()
        await db.commit()
        await db.refresh(db_tag)
        return db_tag
    return None

async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
    db_tag = await get_tag(db, tag_id)
    if db_tag:
        db_tag.soft_delete()
        await db.commit()
        return True
    return False

async def restore_tag(db: AsyncSession, tag_id: int) -> bool:
    """Restaura un tag eliminado"""
    result = await db.execute(
        select(Tag).filter(Tag.id == tag_id)
    )
    db_tag = result.scalar_one_or_none()
    if db_tag and db_tag.is_deleted:
        db_tag.restore()
        await db.commit()
        return True
    return False

async def get_deleted_tags(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Tag]:
    """Obtiene tags eliminados"""
    result = await db.execute(
        select(Tag)
        .filter(Tag.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(Tag.deleted_at.desc())
    )
    return list(result.scalars().all())




async def get_tags_paginated(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[Tag], int]:
    """Obtiene una lista paginada de tags activos"""
    # Consulta para obtener los tags
    result = await db.execute(
        select(Tag)
        .filter(Tag.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(Tag.created_at.desc())
    )
    # Convertir explícitamente a List[Tag] para evitar errores de tipado
    tags: List[Tag] = list(result.scalars().all())
    
    # Consulta para obtener el conteo total
    count_result = await db.execute(
        select(func.count())
        .select_from(Tag)
        .filter(Tag.is_deleted == False)
    )
    total = count_result.scalar_one()
    
    return (tags, total)

async def get_deleted_tags_paginated(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[Tag], int]:
    """Obtiene una lista paginada de tags eliminados"""
    # Consulta para obtener los tags eliminados
    result = await db.execute(
        select(Tag)
        .filter(Tag.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(Tag.deleted_at.desc())
    )
    # Convertir explícitamente a List[Tag]
    tags: List[Tag] = list(result.scalars().all())
    
    # Consulta para obtener el conteo total
    count_result = await db.execute(
        select(func.count())
        .select_from(Tag)
        .filter(Tag.is_deleted == True)
    )
    total = count_result.scalar_one()
    
    return (tags, total)
