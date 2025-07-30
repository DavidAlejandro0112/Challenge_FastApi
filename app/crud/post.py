
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError
from app.models.post import Post
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostUpdate
from app.core.logging import logger
from typing import List, Optional, Tuple
from fastapi import HTTPException


async def get_post(db: AsyncSession, post_id: int) -> Optional[Post]:
    try:
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
            .filter(and_(Post.id == post_id, Post.is_deleted == False))
        )
        post = result.scalar_one_or_none()
        if not post:
            logger.warning(f"Post no encontrado: ID={post_id}")
        return post
    except Exception as e:
        logger.error(f"Error al obtener post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def get_posts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Post]:
    try:
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
            .filter(Post.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .order_by(Post.created_at.desc())  
        )
        posts = list(result.scalars().all())
        logger.info(f"Obtenidos {len(posts)} posts (skip={skip}, limit={limit})")
        return posts
    except Exception as e:
        logger.error(f"Error al obtener posts: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener posts")

async def get_posts_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Post]:
    try:
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
            .filter(and_(Post.author_id == user_id, Post.is_deleted == False))
            .offset(skip)
            .limit(limit)
            .order_by(Post.created_at.desc())
        )
        posts = list(result.scalars().all())
        logger.info(f"Usuario {user_id} tiene {len(posts)} posts")
        return posts
    except Exception as e:
        logger.error(f"Error al obtener posts del usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener posts del usuario")

async def create_post(db: AsyncSession, post: PostCreate, author_id: int) -> Post:
    try:
        db_post = Post(**post.model_dump(), author_id=author_id)
        db.add(db_post)
        await db.commit()
        await db.refresh(db_post)
        logger.info(f"Post creado: ID={db_post.id}, Autor={author_id}")
        return db_post
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Error de integridad al crear post: {str(e)}")
        raise HTTPException(status_code=400, detail="Error de integridad (relación inválida)")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al crear post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al crear post")

async def update_post(db: AsyncSession, post_id: int, post_update: PostUpdate) -> Optional[Post]:
    db_post = await get_post(db, post_id)
    if not db_post:
        logger.warning(f"Intento de actualizar post no encontrado: ID={post_id}")
        return None
    try:
        update_data = post_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_post, key, value)
        db_post.updated_at = func.now()
        await db.commit()
        await db.refresh(db_post)
        logger.info(f"Post actualizado: ID={post_id}")
        return db_post
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar post")

async def delete_post(db: AsyncSession, post_id: int) -> bool:
    db_post = await get_post(db, post_id)
    if not db_post:
        logger.warning(f"Intento de eliminar post no encontrado: ID={post_id}")
        return False
    try:
        db_post.soft_delete()
        await db.commit()
        logger.info(f"Post eliminado (soft): ID={post_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar post")

async def restore_post(db: AsyncSession, post_id: int) -> bool:
    try:
        result = await db.execute(select(Post).filter(Post.id == post_id))
        db_post = result.scalar_one_or_none()
        if db_post and db_post.is_deleted:
            db_post.restore()
            await db.commit()
            logger.info(f"Post restaurado: ID={post_id}")
            return True
        logger.warning(f"No se puede restaurar post: ID={post_id}, ¿ya está activo?")
        return False
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al restaurar post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar post")

async def get_deleted_posts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Post]:
    try:
        result = await db.execute(
            select(Post)
            .filter(Post.is_deleted == True)
            .offset(skip)
            .limit(limit)
            .order_by(Post.deleted_at.desc())
        )
        posts = list(result.scalars().all())
        logger.info(f"Obtenidos {len(posts)} posts eliminados")
        return posts
    except Exception as e:
        logger.error(f"Error al obtener posts eliminados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener posts eliminados")

async def get_deleted_posts_paginated(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[Post], int]:
    try:
        result = await db.execute(
            select(Post)
            .filter(Post.is_deleted == True)
            .offset(skip)
            .limit(limit)
            .order_by(Post.deleted_at.desc())
        )
        posts: List[Post] = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Post).filter(Post.is_deleted == True)
        )
        total = count_result.scalar_one()

        logger.info(f"Paginación de posts eliminados: {skip}-{skip+limit}, total={total}")
        return (posts, total)
    except Exception as e:
        logger.error(f"Error en get_deleted_posts_paginated: {e}")
        return ([], 0)

async def get_posts_paginated(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[Post], int]:
    try:
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
            .filter(Post.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .order_by(Post.created_at.desc())
        )
        posts: List[Post] = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Post).filter(Post.is_deleted == False)
        )
        total = count_result.scalar_one()

        logger.info(f"Posts paginados: {skip}-{skip+limit}, total={total}")
        return (posts, total)
    except Exception as e:
        logger.error(f"Error en get_posts_paginated: {e}")
        return ([], 0)





async def add_tag_to_post(db: AsyncSession, post_id: int, tag_id: int) -> bool:
    db_post = await get_post(db, post_id)
    result = await db.execute(
        select(Tag).filter(and_(Tag.id == tag_id, Tag.is_deleted == False))
    )
    db_tag = result.scalar_one_or_none()

    if not db_post:
        logger.warning(f"Post no encontrado para añadir tag: post_id={post_id}")
        return False
    if not db_tag:
        logger.warning(f"Tag no encontrado o eliminado: tag_id={tag_id}")
        return False

    try:
        if db_tag not in db_post.tags:
            db_post.tags.append(db_tag)
            await db.commit()
            logger.info(f"Tag {tag_id} añadido al post {post_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al añadir tag {tag_id} al post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al añadir tag")

async def remove_tag_from_post(db: AsyncSession, post_id: int, tag_id: int) -> bool:
    db_post = await get_post(db, post_id)
    result = await db.execute(select(Tag).filter(Tag.id == tag_id))
    db_tag = result.scalar_one_or_none()

    if not db_post or not db_tag:
        return False

    try:
        if db_tag in db_post.tags:
            db_post.tags.remove(db_tag)
            await db.commit()
            logger.info(f"Tag {tag_id} removido del post {post_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al remover tag {tag_id} del post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al remover tag")