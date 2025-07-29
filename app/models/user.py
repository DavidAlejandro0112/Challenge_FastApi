from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.post import Post 

class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    
    # Relación uno a muchos con Post
    posts: Mapped[List["Post"]] = relationship(
        "Post", 
        back_populates="author", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"