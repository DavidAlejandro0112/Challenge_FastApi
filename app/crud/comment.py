from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate
from app.core.logging import logger
from typing import Optional
from fastapi import HTTPException


async def get_comment(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    try:
        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.post))
            .filter(and_(Comment.id == comment_id, Comment.is_deleted == False))
        )
        comment = result.scalar_one_or_none()
        if not comment:
            logger.warning(f"Comentario no encontrado: ID={comment_id}")
        return comment
    except Exception as e:
        logger.error(f"Error al obtener comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

async def create_comment(db: AsyncSession, comment: CommentCreate, post_id: int, author_id: int) -> Comment:
    """
    Crea un nuevo comentario asociado a un post y un autor.
    """
    try:
        db_comment = Comment(
            **comment.model_dump(),  
            post_id=post_id,
            author_id=author_id    
            
        )
        db.add(db_comment)
        await db.commit()
        await db.refresh(db_comment)
        logger.info(f"Comentario creado: ID={db_comment.id}, Post={post_id}, Autor={author_id}")
        return db_comment

    except IntegrityError as e:
        
        await db.rollback()
        logger.error(f"Error de integridad al crear comentario en post {post_id} por autor {author_id}: {str(e)}")
        
        raise HTTPException(
            status_code=400,
            detail="Error de integridad (el post podría no existir o datos inválidos)"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inesperado al crear comentario en post {post_id} por autor {author_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al crear el comentario")

async def update_comment(db: AsyncSession, comment_id: int, comment_update: CommentUpdate) -> Optional[Comment]:
    db_comment = await get_comment(db, comment_id)
    if not db_comment:
        return None
    try:
        update_data = comment_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_comment, key, value)
        db_comment.updated_at = func.now()
        await db.commit()
        await db.refresh(db_comment)
        logger.info(f"Comentario actualizado: ID={comment_id}")
        return db_comment
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar comentario")

async def delete_comment(db: AsyncSession, comment_id: int) -> bool:
    db_comment = await get_comment(db, comment_id)
    if not db_comment:
        return False
    try:
        db_comment.soft_delete()
        await db.commit()
        logger.info(f"Comentario eliminado (soft): ID={comment_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar comentario")

async def restore_comment(db: AsyncSession, comment_id: int) -> bool:
    result = await db.execute(select(Comment).filter(Comment.id == comment_id))
    db_comment = result.scalar_one_or_none()
    if db_comment and db_comment.is_deleted:
        try:
            db_comment.restore()
            await db.commit()
            logger.info(f"Comentario restaurado: ID={comment_id}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Error al restaurar comentario {comment_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al restaurar comentario")
    return False