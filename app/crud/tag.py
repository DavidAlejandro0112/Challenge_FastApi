from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.tag import Tag
from app.models.post import Post
from app.schemas.tag import TagCreate, TagUpdate
from typing import List, Optional

async def get_tag(db: AsyncSession, tag_id: int) -> Optional[Tag]:
    result = await db.execute(
        select(Tag)
        .options(selectinload(Tag.posts))
        .filter(Tag.id == tag_id)
    )
    return result.scalar_one_or_none()

async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[Tag]:
    result = await db.execute(select(Tag).filter(Tag.name == name))
    return result.scalar_one_or_none()

async def get_tags(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Tag]:
    result = await db.execute(
        select(Tag)
        .options(selectinload(Tag.posts))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

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
        await db.commit()
        await db.refresh(db_tag)
        return db_tag
    return None

async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
    db_tag = await get_tag(db, tag_id)
    if db_tag:
        await db.delete(db_tag)
        await db.commit()
        return True
    return False