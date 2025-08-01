from sqlalchemy import Boolean, DateTime, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.post import Post  # Import Post to resolve the undefined name


class Tag(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relación muchos a muchos con Post (usar string y secondary como string)
    posts: Mapped[List["Post"]] = relationship(
        "Post", secondary="post_tags", back_populates="tags"
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"
