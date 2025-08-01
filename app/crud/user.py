from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.post import Post
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.logging import logger
from typing import List, Optional, Tuple
from sqlalchemy.orm import selectinload


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Obtiene un usuario por ID (incluye eliminados)"""
    try:
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error al obtener usuario por ID {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


async def get_user_with_posts(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Obtiene un usuario con sus posts, comentarios y tags cargados.
    """
    try:
        logger.info(f"Obteniendo usuario con posts: ID={user_id}")
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.posts).selectinload(
                    Post.comments
                ),  # ← Carga comentarios
                selectinload(User.posts).selectinload(Post.tags),  # ← Carga tags
            )
            .filter(User.id == user_id, User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"Usuario no encontrado: ID={user_id}")
        return user
    except Exception as e:
        logger.error(f"Error al obtener usuario con posts {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Obtiene un usuario por nombre de usuario"""
    try:
        result = await db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error al obtener usuario por username '{username}': {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Obtiene un usuario activo por email"""
    try:
        result = await db.execute(
            select(User).filter(and_(User.email == email, User.is_deleted == False))
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.info(f"Usuario no encontrado por email: {email}")
        return user
    except Exception as e:
        logger.error(f"Error al obtener usuario por email '{email}': {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


async def get_users_paginated(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> Tuple[List[User], int]:
    """Obtiene una lista paginada de usuarios activos"""
    try:
        result = await db.execute(
            select(User)
            .filter(User.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        users: List[User] = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(User).filter(User.is_deleted == False)
        )
        total = count_result.scalar_one()

        logger.info(f"Usuarios paginados: {skip}-{skip+limit}, total={total}")
        return (users, total)
    except Exception as e:
        logger.error(f"Error en get_users_paginated: {e}")
        return ([], 0)


# ========================
# AUTENTICACIÓN
# ========================


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """Autentica un usuario verificando su contraseña"""
    try:
        user = await get_user_by_username(db, username=username)
        if not user:
            logger.info(
                f"Intento de autenticación fallida: usuario '{username}' no encontrado"
            )
            return None
        if not verify_password(password, user.hashed_password):
            logger.info(
                f"Intento de autenticación fallida: contraseña incorrecta para '{username}'"
            )
            return None
        if user.is_deleted:
            logger.warning(
                f"Intento de autenticación con usuario eliminado: {username}"
            )
            return None
        return user
    except Exception as e:
        logger.error(f"Error al autenticar usuario '{username}': {str(e)}")
        raise HTTPException(status_code=500, detail="Error al autenticar usuario")


# ========================
# CRUD DE USUARIOS
# ========================


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Crea un nuevo usuario"""
    try:
        # Verificar duplicados
        if await get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        if await get_user_by_username(db, user.username):
            raise HTTPException(
                status_code=400, detail="El nombre de usuario ya está en uso"
            )

        user_data = user.model_dump(exclude={"password"})
        hashed_password = get_password_hash(user.password)
        db_user = User(**user_data, hashed_password=hashed_password)

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        logger.info(
            f"Usuario creado: ID={db_user.id}, Username='{db_user.username}', Email='{db_user.email}'"
        )
        return db_user
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Error de integridad al crear usuario: {str(e)}")
        raise HTTPException(
            status_code=400, detail="Error de integridad en la base de datos"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inesperado al crear usuario: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al crear usuario")


async def update_user(
    db: AsyncSession, user_id: int, user_update: UserUpdate
) -> Optional[User]:
    """Actualiza un usuario existente"""
    db_user = await get_user(db, user_id)
    if not db_user:
        logger.warning(f"Intento de actualizar usuario no encontrado: ID={user_id}")
        return None
    if db_user.is_deleted:
        raise HTTPException(
            status_code=400, detail="No se puede actualizar un usuario eliminado"
        )

    try:
        update_data = user_update.model_dump(exclude_unset=True)

        # Evitar duplicados al actualizar email o username
        if "email" in update_data:
            existing = await get_user_by_email(db, update_data["email"])
            if existing and existing.id != user_id:
                raise HTTPException(status_code=400, detail="El email ya está en uso")
        if "username" in update_data:
            existing = await get_user_by_username(db, update_data["username"])
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=400, detail="El nombre de usuario ya está en uso"
                )

        for key, value in update_data.items():
            setattr(db_user, key, value)
        db_user.updated_at = func.now()

        await db.commit()
        await db.refresh(db_user)

        logger.info(f"Usuario actualizado: ID={user_id}")
        return db_user
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Error de integridad al actualizar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=400, detail="Error de integridad")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar usuario")


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Elimina un usuario (soft delete)"""
    db_user = await get_user(db, user_id)
    if not db_user:
        logger.warning(f"Intento de eliminar usuario no encontrado: ID={user_id}")
        return False
    if db_user.is_deleted:
        logger.info(f"Usuario ya está eliminado: ID={user_id}")
        return True

    try:
        db_user.soft_delete()
        await db.commit()
        logger.info(f"Usuario eliminado (soft): ID={user_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar usuario")


async def restore_user(db: AsyncSession, user_id: int) -> bool:
    """Restaura un usuario eliminado"""
    db_user = await get_user(db, user_id)
    if not db_user:
        logger.warning(f"Intento de restaurar usuario no encontrado: ID={user_id}")
        return False
    if not db_user.is_deleted:
        logger.info(f"Usuario ya está activo: ID={user_id}")
        return True

    try:
        db_user.restore()
        await db.commit()
        logger.info(f"Usuario restaurado: ID={user_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al restaurar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar usuario")


async def get_deleted_users(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[User]:
    """Obtiene usuarios eliminados"""
    try:
        result = await db.execute(
            select(User)
            .filter(User.is_deleted == True)
            .offset(skip)
            .limit(limit)
            .order_by(User.deleted_at.desc())
        )
        users = list(result.scalars().all())
        logger.info(f"Obtenidos {len(users)} usuarios eliminados")
        return users
    except Exception as e:
        logger.error(f"Error al obtener usuarios eliminados: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error al obtener usuarios eliminados"
        )


# ========================
# AUTENTICACIÓN Y SEGURIDAD
# ========================


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verifica que el usuario esté activo"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
