from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import tag as crud_tag
from app.schemas.tag import Tag, TagCreate, TagUpdate, TagWithPosts

router = APIRouter(prefix="/tags", tags=["tags"])

@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(tag: TagCreate, db: AsyncSession = Depends(get_db)):
    db_tag = await crud_tag.get_tag_by_name(db, name=tag.name)
    if db_tag:
        raise HTTPException(status_code=400, detail="Tag already exists")
    return await crud_tag.create_tag(db=db, tag=tag)

@router.get("/", response_model=list[Tag])
async def read_tags(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    tags = await crud_tag.get_tags(db, skip=skip, limit=limit)
    return tags

@router.get("/{tag_id}", response_model=TagWithPosts)
async def read_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    db_tag = await crud_tag.get_tag(db, tag_id=tag_id)
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return db_tag

@router.put("/{tag_id}", response_model=Tag)
async def update_tag(tag_id: int, tag: TagUpdate, db: AsyncSession = Depends(get_db)):
    db_tag = await crud_tag.update_tag(db, tag_id=tag_id, tag_update=tag)
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return db_tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud_tag.delete_tag(db, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"message": "Tag deleted successfully"}