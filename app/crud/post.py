from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_
from app.models.post import Post, Comment
from app.models.user import User
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostUpdate, CommentCreate, CommentUpdate
from typing import List, Optional

async def get_post(db: AsyncSession, post_id: int) -> Optional[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
        .filter(and_(Post.id == post_id, Post.is_deleted == False))
    )
    return result.scalar_one_or_none()

async def get_posts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
        .filter(Post.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(Post.created_at.desc().all())
    )
    return list(result.scalars().all())

async def get_posts_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Post]:
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments), selectinload(Post.tags))
        .filter(and_(Post.author_id == user_id, Post.is_deleted == False))
        .offset(skip)
        .limit(limit)
        .order_by(Post.created_at.desc())
    )
    return list(result.scalars().all())

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
        db_post.updated_at = func.now()
        await db.commit()
        await db.refresh(db_post)
        return db_post
    return None

async def delete_post(db: AsyncSession, post_id: int) -> bool:
    db_post = await get_post(db, post_id)
    if db_post:
        db_post.soft_delete()
        await db.commit()
        return True
    return False

async def restore_post(db: AsyncSession, post_id: int) -> bool:
    """Restaura un post eliminado"""
    result = await db.execute(
        select(Post).filter(Post.id == post_id)
    )
    db_post = result.scalar_one_or_none()
    if db_post and db_post.is_deleted:
        db_post.restore()
        await db.commit()
        return True
    return False

async def get_deleted_posts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Post]:
    """Obtiene posts eliminados"""
    result = await db.execute(
        select(Post)
        .filter(Post.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(Post.deleted_at.desc())
    )
    return list(result.scalars().all())

async def create_comment(db: AsyncSession, comment: CommentCreate, post_id: int) -> Comment:
    db_comment = Comment(**comment.model_dump(), post_id=post_id)
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def add_tag_to_post(db: AsyncSession, post_id: int, tag_id: int) -> bool:
    db_post = await get_post(db, post_id)
    result = await db.execute(select(Tag).filter(and_(Tag.id == tag_id, Tag.is_deleted == False)))
    db_tag = result.scalar_one_or_none()
    
    if db_post and db_tag:
        if db_tag not in db_post.tags:
            db_post.tags.append(db_tag)
            await db.commit()
            return True
    return False

async def remove_tag_from_post(db: AsyncSession, post_id: int, tag_id: int) -> bool:
    db_post = await get_post(db, post_id)
    result = await db.execute(select(Tag).filter(Tag.id == tag_id))
    db_tag = result.scalar_one_or_none()
    
    if db_post and db_tag:
        if db_tag in db_post.tags:
            db_post.tags.remove(db_tag)
            await db.commit()
            return True
    return False

async def get_comment(db: AsyncSession, comment_id: int) -> Optional[Comment]:
    """Obtiene un comentario por ID"""
    result = await db.execute(
        select(Comment).filter(and_(
            Comment.id == comment_id, 
            Comment.is_deleted == False
        ))
    )
    return result.scalar_one_or_none()

async def update_comment(db: AsyncSession, comment_id: int, comment_update: CommentUpdate) -> Optional[Comment]:
    """Actualiza un comentario"""
    db_comment = await get_comment(db, comment_id)
    if db_comment:
        update_data = comment_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_comment, key, value)
        db_comment.updated_at = func.now()
        await db.commit()
        await db.refresh(db_comment)
        return db_comment
    return None

async def delete_comment(db: AsyncSession, comment_id: int) -> bool:
    """Elimina un comentario (soft delete)"""
    db_comment = await get_comment(db, comment_id)
    if db_comment:
        db_comment.soft_delete()
        await db.commit()
        return True
    return False

async def restore_comment(db: AsyncSession, comment_id: int) -> bool:
    """Restaura un comentario eliminado"""
    result = await db.execute(
        select(Comment).filter(Comment.id == comment_id)
    )
    db_comment = result.scalar_one_or_none()
    if db_comment and db_comment.is_deleted:
        db_comment.restore()
        await db.commit()
        return True
    return False

async def get_deleted_comments(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Comment]:
    """Obtiene comentarios eliminados"""
    result = await db.execute(
        select(Comment)
        .filter(Comment.is_deleted == True)
        .offset(skip)
        .limit(limit)
        .order_by(Comment.deleted_at.desc())
    )
    return list(result.scalars().all())