
"""
Exporta todos los modelos para facilitar las importaciones.
"""
from .base import Base
from .user import User
from .post import Post
from .tag import Tag
from .comment import Comment

# Esto asegura que todos los modelos estén registrados en Base.metadata