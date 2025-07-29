from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import post as crud_post
from app.crud import user as crud_user
from app.schemas.post import Comment, CommentCreate, CommentUpdate

router = APIRouter(prefix="/comments", tags=["comments"])

@router.get("/{comment_id}", response_model=Comment)
async def read_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    # Necesitamos crear una función específica para obtener comentarios
    from sqlalchemy.future import select
    from app.models.post import Comment as CommentModel
    from sqlalchemy import and_
    
    result = await db.execute(
        select(CommentModel).filter(and_(
            CommentModel.id == comment_id, 
            CommentModel.is_deleted == False
        ))
    )
    db_comment = result.scalar_one_or_none()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return db_comment

@router.put("/{comment_id}", response_model=Comment)
async def update_comment(comment_id: int, comment: CommentUpdate, db: AsyncSession = Depends(get_db)):
    """
    Actualizar comentario
    
    Actualiza los datos de un comentario existente.
    
    ## Parámetros:
    - **comment_id**: ID del comentario a actualizar
    - **comment**: Objeto con los datos a actualizar
    
    ## Respuesta:
    - Comentario actualizado
    
    ## Errores:
    - **404**: Comentario no encontrado
    """
    from sqlalchemy.future import select
    from app.models.post import Comment as CommentModel
    from sqlalchemy import and_, func
    
    result = await db.execute(
        select(CommentModel).filter(and_(
            CommentModel.id == comment_id, 
            CommentModel.is_deleted == False
        ))
    )
    db_comment = result.scalar_one_or_none()
    
    if db_comment:
        update_data = comment.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_comment, key, value)
        db_comment.updated_at = func.now()
        await db.commit()
        await db.refresh(db_comment)
        return db_comment
    raise HTTPException(status_code=404, detail="Comment not found")

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Eliminar comentario (soft delete)
    
    Marca un comentario como eliminado sin borrarlo físicamente.
    
    ## Parámetros:
    - **comment_id**: ID del comentario a eliminar
    
    ## Respuesta:
    - 204 No Content
    
    ## Errores:
    - **404**: Comentario no encontrado
    """
    from sqlalchemy.future import select
    from app.models.post import Comment as CommentModel
    from sqlalchemy import and_
    
    result = await db.execute(
        select(CommentModel).filter(and_(
            CommentModel.id == comment_id, 
            CommentModel.is_deleted == False
        ))
    )
    db_comment = result.scalar_one_or_none()
    
    if db_comment:
        db_comment.soft_delete()
        await db.commit()
        return {"message": "Comment deleted successfully"}
    raise HTTPException(status_code=404, detail="Comment not found")

@router.post("/{comment_id}/restore", response_model=Comment)
async def restore_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Restaurar comentario eliminado
    
    Restaura un comentario que fue eliminado (soft delete).
    
    ## Parámetros:
    - **comment_id**: ID del comentario a restaurar
    
    ## Respuesta:
    - Comentario restaurado
    
    ## Errores:
    - **404**: Comentario eliminado no encontrado
    """
    from sqlalchemy.future import select
    from app.models.post import Comment as CommentModel
    
    result = await db.execute(
        select(CommentModel).filter(CommentModel.id == comment_id)
    )
    db_comment = result.scalar_one_or_none()
    
    if db_comment and db_comment.is_deleted:
        db_comment.restore()
        await db.commit()
        await db.refresh(db_comment)
        return db_comment
    raise HTTPException(status_code=404, detail="Deleted comment not found")

@router.get("/deleted/", response_model=list[Comment])
async def read_deleted_comments(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Obtener comentarios eliminados
    
    Retorna una lista paginada de todos los comentarios eliminados.
    
    ## Parámetros:
    - **skip**: Número de registros a saltar (paginación)
    - **limit**: Número máximo de registros a retornar
    
    ## Respuesta:
    - Lista de comentarios eliminados
    """
    from sqlalchemy.future import select
    from app.models.post import Comment as CommentModel
    
    result = await db.execute(
        select(CommentModel)
        .filter(CommentModel.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(CommentModel.deleted_at.desc())
    )
    return result.scalars().all()