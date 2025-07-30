from sqlalchemy import Integer, Text, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, SoftDeleteMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.post import Post

class Comment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "comments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(100))
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"))

    # Relación con Post
    post: Mapped["Post"] = relationship("Post", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, content='{self.content[:50]}...')>"