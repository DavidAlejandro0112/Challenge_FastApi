from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Boolean, DateTime
from datetime import datetime, timezone 
from typing import Optional

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)  
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),  
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc) 
    )
class SoftDeleteMixin:
    """Mixin para añadir soft delete functionality"""
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def soft_delete(self):
        """Marca el registro como eliminado"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restaura el registro eliminado"""
        self.is_deleted = False
        self.deleted_at = None