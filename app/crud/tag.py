from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError, DBAPIError
from app.models.tag import Tag
from app.models.post import Post
from app.schemas.tag import TagCreate, TagUpdate
from app.core.logging import logger
from typing import List, Optional, Tuple
from fastapi import HTTPException


async def get_tag(db: AsyncSession, tag_id: int) -> Optional[Tag]:
    """Obtiene un tag por ID con sus posts asociados"""
    try:
        result = await db.execute(
            select(Tag)
            .options(selectinload(Tag.posts))
            .filter(and_(Tag.id == tag_id, Tag.is_deleted == False))
        )
        tag = result.scalar_one_or_none()
        if not tag:
            logger.warning(f"Tag no encontrado: ID={tag_id}")
        return tag
    except Exception as e:
        logger.error(f"Error al obtener tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[Tag]:
    """Obtiene un tag por nombre (case-insensitive)"""
    try:
        result = await db.execute(
            select(Tag).filter(
                and_(func.lower(Tag.name) == name.lower(), Tag.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error al buscar tag por nombre '{name}': {str(e)}")
        raise HTTPException(status_code=500, detail="Error al buscar tag")


async def get_tags(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Tag]:
    """Obtiene una lista de tags activos"""
    try:
        result = await db.execute(
            select(Tag)
            .options(selectinload(Tag.posts))
            .filter(Tag.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .order_by(Tag.created_at.desc())
        )
        tags = list(result.scalars().all())
        logger.info(f"Obtenidos {len(tags)} tags (skip={skip}, limit={limit})")
        return tags
    except Exception as e:
        logger.error(f"Error al obtener tags: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener tags")


async def create_tag(db: AsyncSession, tag: TagCreate) -> Tag:
    """Crea un nuevo tag"""
    try:
        # Evitar duplicados (case-insensitive)
        existing = await get_tag_by_name(db, tag.name)
        if existing:
            raise HTTPException(status_code=400, detail="El nombre del tag ya existe")

        db_tag = Tag(**tag.model_dump())
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)
        logger.info(f"Tag creado: ID={db_tag.id}, Nombre='{db_tag.name}'")
        return db_tag
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Error de integridad al crear tag: {str(e)}")
        raise HTTPException(status_code=400, detail="Error de integridad al crear tag")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inesperado al crear tag: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al crear tag")


async def update_tag(
    db: AsyncSession, tag_id: int, tag_update: TagUpdate
) -> Optional[Tag]:
    """Actualiza un tag existente"""
    db_tag = await get_tag(db, tag_id)
    if not db_tag:
        logger.warning(f"Intento de actualizar tag no encontrado: ID={tag_id}")
        return None

    try:
        # Si se cambia el nombre, verificar que no exista otro tag con ese nombre
        if tag_update.name and tag_update.name != db_tag.name:
            existing = await get_tag_by_name(db, tag_update.name)
            if existing:
                raise HTTPException(
                    status_code=400, detail="El nombre del tag ya existe"
                )

        update_data = tag_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_tag, key, value)
        db_tag.updated_at = func.now()

        await db.commit()
        await db.refresh(db_tag)
        logger.info(f"Tag actualizado: ID={tag_id}")
        return db_tag
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Error de integridad al actualizar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=400, detail="Error de integridad")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar tag")


async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
    """Elimina un tag (soft delete)"""
    db_tag = await get_tag(db, tag_id)
    if not db_tag:
        logger.warning(f"Intento de eliminar tag no encontrado: ID={tag_id}")
        return False

    try:
        db_tag.soft_delete()
        await db.commit()
        logger.info(f"Tag eliminado (soft): ID={tag_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar tag")


async def restore_tag(db: AsyncSession, tag_id: int) -> bool:
    """Restaura un tag eliminado"""
    try:
        result = await db.execute(select(Tag).filter(Tag.id == tag_id))
        db_tag = result.scalar_one_or_none()
        if not db_tag:
            logger.warning(f"Intento de restaurar tag no encontrado: ID={tag_id}")
            return False
        if not db_tag.is_deleted:
            logger.info(f"Tag ya está activo: ID={tag_id}")
            return True

        db_tag.restore()
        await db.commit()
        logger.info(f"Tag restaurado: ID={tag_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al restaurar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar tag")


async def get_deleted_tags(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Tag]:
    """Obtiene tags eliminados"""
    try:
        result = await db.execute(
            select(Tag)
            .filter(Tag.is_deleted == True)
            .offset(skip)
            .limit(limit)
            .order_by(Tag.deleted_at.desc())
        )
        tags = list(result.scalars().all())
        logger.info(f"Obtenidos {len(tags)} tags eliminados")
        return tags
    except Exception as e:
        logger.error(f"Error al obtener tags eliminados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener tags eliminados")


async def get_tags_paginated(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> Tuple[List[Tag], int]:
    """Obtiene una lista paginada de tags activos"""
    try:
        result = await db.execute(
            select(Tag)
            .filter(Tag.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .order_by(Tag.created_at.desc())
        )
        tags: List[Tag] = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Tag).filter(Tag.is_deleted == False)
        )
        total = count_result.scalar_one()

        logger.info(f"Tags paginados: {skip}-{skip+limit}, total={total}")
        return (tags, total)
    except Exception as e:
        logger.error(f"Error en get_tags_paginated: {e}")
        return ([], 0)


async def get_deleted_tags_paginated(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> Tuple[List[Tag], int]:
    """Obtiene una lista paginada de tags eliminados"""
    try:
        result = await db.execute(
            select(Tag)
            .filter(Tag.is_deleted == True)
            .offset(skip)
            .limit(limit)
            .order_by(Tag.deleted_at.desc())
        )
        tags: List[Tag] = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Tag).filter(Tag.is_deleted == True)
        )
        total = count_result.scalar_one()

        logger.info(f"Tags eliminados paginados: {skip}-{skip+limit}, total={total}")
        return (tags, total)
    except Exception as e:
        logger.error(f"Error en get_deleted_tags_paginated: {e}")
        return ([], 0)
