from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import tag as crud_tag
from app.schemas.tag import Tag, TagCreate, TagUpdate, TagWithPosts
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/tags", tags=["tags"])

@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(tag: TagCreate, db: AsyncSession = Depends(get_db)):
    """Crear una nueva etiqueta"""
    db_tag = await crud_tag.get_tag_by_name(db, name=tag.name)
    if db_tag:
        raise HTTPException(status_code=400, detail="Tag already exists")
    return await crud_tag.create_tag(db=db, tag=tag)

@router.get("/", response_model=PaginatedResponse[Tag])
async def read_tags(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(10, ge=1, le=1000, description="Número máximo de registros a devolver"),
    db: AsyncSession = Depends(get_db)
):
    """Obtener lista paginada de etiquetas"""
    db_tags, total = await crud_tag.get_tags_paginated(db, skip=skip, limit=limit)
    pydantic_tags = [Tag.model_validate(db_tag) for db_tag in db_tags]
    page = skip // limit + 1 if limit > 0 else 1
    size = len(pydantic_tags)
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    return PaginatedResponse[Tag](
        items=pydantic_tags,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )

@router.get("/{tag_id}", response_model=TagWithPosts)
async def read_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    """Obtener etiqueta por ID"""
    db_tag = await crud_tag.get_tag(db, tag_id=tag_id)
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return db_tag

@router.patch("/{tag_id}", response_model=Tag)
async def update_tag(tag_id: int, tag: TagUpdate, db: AsyncSession = Depends(get_db)):
    """Actualizar etiqueta"""
    db_tag = await crud_tag.update_tag(db, tag_id=tag_id, tag_update=tag)
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return db_tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    """Eliminar etiqueta (soft delete)"""
    success = await crud_tag.delete_tag(db, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"message": "Tag deleted successfully"}

@router.post("/{tag_id}/restore", response_model=Tag)
async def restore_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    """Restaurar etiqueta eliminada"""
    success = await crud_tag.restore_tag(db, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deleted tag not found")
    db_tag = await crud_tag.get_tag(db, tag_id=tag_id)
    return db_tag

@router.get("/deleted/", response_model=PaginatedResponse[Tag])
async def read_deleted_tags(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(10, ge=1, le=1000, description="Número máximo de registros a devolver"),
    db: AsyncSession = Depends(get_db)
):
    """Obtener etiquetas eliminadas"""
    db_tags, total = await crud_tag.get_deleted_tags_paginated(db, skip=skip, limit=limit)
    pydantic_tags = [Tag.model_validate(db_tag) for db_tag in db_tags]
    page = skip // limit + 1 if limit > 0 else 1
    size = len(pydantic_tags)
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    return PaginatedResponse[Tag](
        items=pydantic_tags,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )
