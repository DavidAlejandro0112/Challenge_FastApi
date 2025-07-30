from sqlalchemy import Boolean, String, Text, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tag import Tag  
    from app.models.comment import Comment
    


# Tabla intermedia para relación muchos a muchos Post-Tag
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Post(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)
    # Columna para la fecha de soft delete, puede ser NULL
    
    # Relación muchos a uno con User (usar string)
    author: Mapped["User"] = relationship("User", back_populates="posts")
    
    # Relación uno a muchos con Comment (usar string)
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    
    # Relación muchos a muchos con Tag (usar string)
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=post_tags, back_populates="posts")
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"

