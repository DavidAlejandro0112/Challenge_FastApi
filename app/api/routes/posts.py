from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import post as crud_post
from app.crud import user as crud_user
from app.crud import tag as crud_tag
from app.schemas.post import Post, PostCreate, PostUpdate, CommentCreate, Comment
from app.schemas.tag import Tag

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, author_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.get_user(db, user_id=author_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return await crud_post.create_post(db=db, post=post, author_id=author_id)

@router.get("/", response_model=list[Post])
async def read_posts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    posts = await crud_post.get_posts(db, skip=skip, limit=limit)
    return posts

@router.get("/{post_id}", response_model=Post)
async def read_post(post_id: int, db: AsyncSession = Depends(get_db)):
    db_post = await crud_post.get_post(db, post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return db_post

@router.put("/{post_id}", response_model=Post)
async def update_post(post_id: int, post: PostUpdate, db: AsyncSession = Depends(get_db)):
    db_post = await crud_post.update_post(db, post_id=post_id, post_update=post)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return db_post

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud_post.delete_post(db, post_id=post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted successfully"}

@router.post("/{post_id}/comments", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def create_comment_for_post(post_id: int, comment: CommentCreate, db: AsyncSession = Depends(get_db)):
    db_post = await crud_post.get_post(db, post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return await crud_post.create_comment(db=db, comment=comment, post_id=post_id)

@router.post("/{post_id}/tags/{tag_id}", response_model=Post)
async def add_tag_to_post(post_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud_post.add_tag_to_post(db, post_id=post_id, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post or Tag not found, or already associated")
    db_post = await crud_post.get_post(db, post_id=post_id)
    return db_post

@router.delete("/{post_id}/tags/{tag_id}", response_model=Post)
async def remove_tag_from_post(post_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud_post.remove_tag_from_post(db, post_id=post_id, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post or Tag not found, or not associated")
    db_post = await crud_post.get_post(db, post_id=post_id)
    return db_post