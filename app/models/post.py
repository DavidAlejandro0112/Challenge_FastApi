from sqlalchemy import String, Text, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from typing import List, Optional

# Tabla intermedia para relación muchos a muchos Post-Tag
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    # Relación muchos a uno con User (usar string)
    author: Mapped["User"] = relationship("User", back_populates="posts")
    
    # Relación uno a muchos con Comment (usar string)
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    
    # Relación muchos a muchos con Tag (usar string)
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=post_tags, back_populates="posts")
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"

class Comment(Base, TimestampMixin):
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(100))
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"))
    
    # Relación muchos a uno con Post (usar string)
    post: Mapped["Post"] = relationship("Post", back_populates="comments")
    
    def __repr__(self):
        return f"<Comment(id={self.id}, content='{self.content[:50]}...')>"