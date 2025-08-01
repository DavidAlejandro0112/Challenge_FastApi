from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import post as crud_post
from app.crud import user as crud_user
from app.schemas.post import Comment
from app.schemas.comment import CommentUpdate
from app.models.comment import Comment as CommentModel
from app.models.user import User
from sqlalchemy.future import select
from sqlalchemy import and_, func
from app.core.logging import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting por IP
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/{comment_id}", response_model=Comment)
@limiter.limit("10/minute")
async def read_comment(
    request: Request, comment_id: int, db: AsyncSession = Depends(get_db)
):
    """
    Obtiene un comentario por ID si está activo.
    """
    try:
        logger.info(f"Intento de obtener comentario: ID={comment_id}")
        result = await db.execute(
            select(CommentModel).filter(
                and_(CommentModel.id == comment_id, CommentModel.is_deleted == False)
            )
        )
        db_comment = result.scalar_one_or_none()

        if not db_comment:
            logger.warning(f"Comentario no encontrado: ID={comment_id}")
            raise HTTPException(status_code=404, detail="Comentario no encontrado")

        logger.info(f"Comentario obtenido: ID={comment_id}, Post={db_comment.post_id}")
        return db_comment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.patch("/{comment_id}", response_model=Comment)
@limiter.limit("5/minute")
async def update_comment(
    request: Request,
    comment_id: int,
    comment: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):

    try:
        logger.info(
            f"Intento de actualizar comentario: ID={comment_id} por usuario {current_user.id}"
        )

        result = await db.execute(
            select(CommentModel).filter(
                and_(CommentModel.id == comment_id, CommentModel.is_deleted == False)
            )
        )
        db_comment = result.scalar_one_or_none()

        if not db_comment:
            logger.warning(
                f"Intento de actualizar comentario no encontrado: ID={comment_id}"
            )
            raise HTTPException(status_code=404, detail="Comentario no encontrado")

        # Verificar permisos: solo el autor o admin
        if (
            getattr(db_comment, "author_id", None) != current_user.id
            and not current_user.is_admin
        ):
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó editar comentario {comment_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar este comentario",
            )

        update_data = comment.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_comment, key, value)
        db_comment.updated_at = func.now()

        await db.commit()
        await db.refresh(db_comment)

        logger.info(f"Comentario actualizado: ID={comment_id}")
        return db_comment

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar comentario")


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_comment(
    request: Request,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Elimina un comentario (soft delete). Solo el autor o un admin puede hacerlo.
    """
    try:
        logger.info(
            f"Intento de eliminar comentario: ID={comment_id} por usuario {current_user.id}"
        )

        result = await db.execute(
            select(CommentModel).filter(
                and_(CommentModel.id == comment_id, CommentModel.is_deleted == False)
            )
        )
        db_comment = result.scalar_one_or_none()

        if not db_comment:
            logger.warning(f"Comentario no encontrado para eliminar: ID={comment_id}")
            raise HTTPException(status_code=404, detail="Comentario no encontrado")

        # Verificar permisos
        if (
            getattr(db_comment, "author_id", None) != current_user.id
            and not current_user.is_admin
        ):
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó eliminar comentario {comment_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este comentario",
            )

        db_comment.soft_delete()
        await db.commit()

        logger.info(f"Comentario eliminado (soft): ID={comment_id}")
        return {"message": "Comentario eliminado correctamente"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar comentario")


@router.post("/{comment_id}/restore", response_model=Comment)
@limiter.limit("5/minute")
async def restore_comment(
    request: Request,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Restaura un comentario eliminado. Solo un admin puede hacerlo.
    """
    try:
        logger.info(
            f"Intento de restaurar comentario: ID={comment_id} por usuario {current_user.id}"
        )

        # Solo admins pueden restaurar
        if not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó restaurar comentario {comment_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden restaurar comentarios",
            )

        result = await db.execute(
            select(CommentModel).filter(CommentModel.id == comment_id)
        )
        db_comment = result.scalar_one_or_none()

        if not db_comment or not db_comment.is_deleted:
            logger.warning(f"Comentario no encontrado o ya activo: ID={comment_id}")
            raise HTTPException(
                status_code=404, detail="Comentario eliminado no encontrado"
            )

        db_comment.restore()
        await db.commit()
        await db.refresh(db_comment)

        logger.info(f"Comentario restaurado: ID={comment_id}")
        return db_comment

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al restaurar comentario {comment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar comentario")


@router.get("/deleted/", response_model=list[Comment])
@limiter.limit("10/minute")
async def read_deleted_comments(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):

    try:
        logger.info(
            f"Usuario {current_user.id} intenta acceder a comentarios eliminados"
        )

        if not current_user.is_admin:
            logger.warning(
                f"Acceso denegado a comentarios eliminados para usuario {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: solo administradores",
            )

        result = await db.execute(
            select(CommentModel)
            .filter(CommentModel.is_deleted == True)
            .offset(skip)
            .limit(limit)
            .order_by(CommentModel.deleted_at.desc())
        )
        comments = result.scalars().all()

        logger.info(
            f"Obtenidos {len(comments)} comentarios eliminados (skip={skip}, limit={limit})"
        )
        return comments

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener comentarios eliminados: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error al obtener comentarios eliminados"
        )
