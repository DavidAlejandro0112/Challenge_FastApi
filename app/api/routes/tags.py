from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import tag as crud_tag
from app.crud import user as crud_user
from app.schemas.tag import Tag, TagCreate, TagUpdate, TagWithPosts
from app.schemas.common import PaginatedResponse
from app.models.user import User
from app.core.logging import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting por IP
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/hour")
async def create_tag(
    request: Request,
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Crea una nueva etiqueta. Solo accesible para administradores.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta crear tag: {tag.name}")

        if not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó crear tag"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden crear etiquetas",
            )

        db_tag = await crud_tag.get_tag_by_name(db, name=tag.name)
        if db_tag:
            logger.warning(f"Intento de crear tag duplicado: {tag.name}")
            raise HTTPException(status_code=400, detail="El nombre del tag ya existe")

        db_tag = await crud_tag.create_tag(db=db, tag=tag)
        logger.info(f"Tag creado: ID={db_tag.id}, Nombre='{db_tag.name}'")
        return db_tag

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear tag '{tag.name}': {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/", response_model=PaginatedResponse[Tag])
@limiter.limit("50/minute")
async def read_tags(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene una lista paginada de tags activos.
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo tags (skip={skip}, limit={limit})")
        db_tags, total = await crud_tag.get_tags_paginated(db, skip=skip, limit=limit)

        pydantic_tags = [Tag.model_validate(db_tag) for db_tag in db_tags]
        page = skip // limit + 1 if limit > 0 else 1
        size = len(pydantic_tags)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        logger.info(f"Tags obtenidos: {size} de {total} totales")
        return PaginatedResponse[Tag](
            items=pydantic_tags,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Error al obtener tags paginados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener etiquetas")


@router.get("/{tag_id}", response_model=TagWithPosts)
@limiter.limit("50/minute")
async def read_tag(request: Request, tag_id: int, db: AsyncSession = Depends(get_db)):
    """
    Obtiene un tag por ID con sus posts asociados.
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo tag con relaciones: ID={tag_id}")
        db_tag = await crud_tag.get_tag(db, tag_id=tag_id)
        if not db_tag:
            logger.warning(f"Tag no encontrado: ID={tag_id}")
            raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
        return db_tag
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener la etiqueta")


@router.patch("/{tag_id}", response_model=Tag)
@limiter.limit("5/hour")
async def update_tag(
    request: Request,
    tag_id: int,
    tag: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Actualiza un tag. Solo accesible para administradores.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta actualizar tag: ID={tag_id}")

        if not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó editar tag {tag_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden editar etiquetas",
            )

        db_tag = await crud_tag.update_tag(db, tag_id=tag_id, tag_update=tag)
        if not db_tag:
            logger.warning(f"Tag no encontrado para actualizar: ID={tag_id}")
            raise HTTPException(status_code=404, detail="Etiqueta no encontrada")

        logger.info(f"Tag actualizado: ID={tag_id}")
        return db_tag

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar la etiqueta")


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
async def delete_tag(
    request: Request,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Elimina un tag (soft delete). Solo accesible para administradores.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta eliminar tag: ID={tag_id}")

        if not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó eliminar tag {tag_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden eliminar etiquetas",
            )

        success = await crud_tag.delete_tag(db, tag_id=tag_id)
        if not success:
            logger.warning(f"Tag no encontrado para eliminar: ID={tag_id}")
            raise HTTPException(status_code=404, detail="Etiqueta no encontrada")

        logger.info(f"Tag eliminado (soft): ID={tag_id}")
        return {"message": "Etiqueta eliminada correctamente"}

    except Exception as e:
        logger.error(f"Error al eliminar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar la etiqueta")


@router.post("/{tag_id}/restore", response_model=Tag)
@limiter.limit("5/hour")
async def restore_tag(
    request: Request,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Restaura un tag eliminado. Solo accesible para administradores.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta restaurar tag: ID={tag_id}")

        if not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó restaurar tag {tag_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden restaurar etiquetas",
            )

        success = await crud_tag.restore_tag(db, tag_id=tag_id)
        if not success:
            logger.warning(f"Tag eliminado no encontrado: ID={tag_id}")
            raise HTTPException(
                status_code=404, detail="Etiqueta eliminada no encontrada"
            )

        db_tag = await crud_tag.get_tag(db, tag_id=tag_id)
        logger.info(f"Tag restaurado: ID={tag_id}")
        return db_tag

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al restaurar tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar la etiqueta")


@router.get("/deleted/", response_model=PaginatedResponse[Tag])
@limiter.limit("10/minute")
async def read_deleted_tags(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Obtiene tags eliminados. Solo accesible para administradores.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta acceder a tags eliminados")

        if not current_user.is_admin:
            logger.warning(
                f"Acceso denegado a tags eliminados para usuario {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: solo administradores",
            )

        db_tags, total = await crud_tag.get_deleted_tags_paginated(
            db, skip=skip, limit=limit
        )
        pydantic_tags = [Tag.model_validate(db_tag) for db_tag in db_tags]
        page = skip // limit + 1 if limit > 0 else 1
        size = len(pydantic_tags)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        logger.info(f"Tags eliminados obtenidos: {size} de {total} totales")
        return PaginatedResponse[Tag](
            items=pydantic_tags,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener tags eliminados: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error al obtener etiquetas eliminadas"
        )
