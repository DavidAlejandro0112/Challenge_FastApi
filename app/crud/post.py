from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.post import Post, Comment
from app.models.user import User
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostUpdate, CommentCreate
from typing import List, Optional

async def get_post(db: AsyncSession, post_id: int) -> Optional[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
        .filter(Post.id == post_id)
    )
    return result.scalar_one_or_none()

async def get_posts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_posts_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
        .filter(Post.author_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_post(db: AsyncSession, post: PostCreate, author_id: int) -> Post:
    db_post = Post(**post.model_dump(), author_id=author_id)
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return db_post

async def update_post(db: AsyncSession, post_id: int, post_update: PostUpdate) -> Optional[Post]:
    db_post = await get_post(db, post_id)
    if db_post:
        update_data = post_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_post, key, value)
        await db.commit()
        await db.refresh(db_post)
        return db_post
    return None

async def delete_post(db: AsyncSession, post_id: int) -> bool:
    db_post = await get_post(db, post_id)
    if db_post:
        await db.delete(db_post)
        await db.commit()
        return True
    return False

async def create_comment(db: AsyncSession, comment: CommentCreate, post_id: int) -> Comment:
    db_comment = Comment(**comment.model_dump(), post_id=post_id)
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def add_tag_to_post(db: AsyncSession, post_id: int, tag_id: int) -> bool:
    db_post = await get_post(db, post_id)
    db_tag = await db.execute(select(Tag).filter(Tag.id == tag_id))
    db_tag = db_tag.scalar_one_or_none()
    
    if db_post and db_tag:
        if db_tag not in db_post.tags:
            db_post.tags.append(db_tag)
            await db.commit()
            return True
    return False

async def remove_tag_from_post(db: AsyncSession, post_id: int, tag_id: int) -> bool:
    db_post = await get_post(db, post_id)
    db_tag = await db.execute(select(Tag).filter(Tag.id == tag_id))
    db_tag = db_tag.scalar_one_or_none()
    
    if db_post and db_tag:
        if db_tag in db_post.tags:
            db_post.tags.remove(db_tag)
            await db.commit()
            return True
    return False