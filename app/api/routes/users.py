from fastapi import APIRouter, Depends, HTTPException, Query, status, Request,Security
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import user as crud_user
from app.crud import post as crud_post
from app.schemas.common import PaginatedResponse
from app.schemas.user import User, UserCreate, UserUpdate, UserWithPosts
from app.schemas.post import Post
from app.models.user import User as UserModel
from app.core.security import oauth2_scheme
from fastapi import Security
from app.core.deps import get_current_active_user
from app.core.logging import logger
from app.core.deps import require_admin
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting por IP
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=PaginatedResponse[User])
@limiter.limit("50/minute")
async def read_users(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene una lista paginada de usuarios activos.
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo usuarios (skip={skip}, limit={limit})")
        db_users, total = await crud_user.get_users_paginated(db, skip=skip, limit=limit)

        pydantic_users = [User.model_validate(db_user) for db_user in db_users]
        page = skip // limit + 1 if limit > 0 else 1
        size = len(pydantic_users)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        logger.info(f"Usuarios obtenidos: {size} de {total} totales")
        return PaginatedResponse[User](
            items=pydantic_users,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error al obtener usuarios paginados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener usuarios")




@router.get("/me", response_model=User)
@limiter.limit("100/minute")
async def read_user_me(
    request: Request,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Obtiene el perfil del usuario autenticado.
    Requiere autenticación.
    """
    try:
        logger.info(f"Acceso a /me por usuario: ID={current_user.id}, username='{current_user.username}'")
        return User.model_validate(current_user)
    except Exception as e:
        logger.error(f"Error al obtener perfil del usuario {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener perfil")



@router.get("/admin-only")
@limiter.limit("10/minute")
async def admin_only(
    request: Request,
    admin: UserModel = Depends(require_admin)
):
    """
    Endpoint de ejemplo para verificar permisos de administrador.
    Solo accesible para administradores.
    """
    try:
        logger.info(f"Acceso a /admin-only por administrador: {admin.username}")
        return {"message": f"Hello {admin.username}, you are an admin!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint admin-only: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno")



@router.get("/{user_id}", response_model=UserWithPosts)
@limiter.limit("50/minute")
async def read_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene un usuario por ID con sus posts asociados.
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo usuario con relaciones: ID={user_id}")
        db_user = await crud_user.get_user_with_posts(db, user_id=user_id)
        if not db_user:
            logger.warning(f"Usuario no encontrado: ID={user_id}")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return UserWithPosts.model_validate(db_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener el usuario")



@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")  # Evita spam de registros
async def create_user(
    request: Request,
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo usuario. Acceso público.
   
    """
    try:
        logger.info(f"Intento de registro: username='{user.username}', email='{user.email}'")

        db_user = await crud_user.get_user_by_username(db, username=user.username)
        if db_user:
            logger.warning(f"Registro fallido: username ya existe '{user.username}'")
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")

        db_user = await crud_user.get_user_by_email(db, email=user.email)
        if db_user:
            logger.warning(f"Registro fallido: email ya existe '{user.email}'")
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

        db_user = await crud_user.create_user(db=db, user=user)
        logger.info(f"Usuario registrado exitosamente: ID={db_user.id}, username='{db_user.username}'")
        return User.model_validate(db_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear usuario: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")




@router.patch("/{user_id}", response_model=User)
@limiter.limit("10/hour")
async def update_user(
    request: Request,
    user_id: int,
    user: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Actualiza un usuario. Solo el propio usuario o un admin puede hacerlo.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta actualizar usuario: ID={user_id}")

        # Verificar permisos
        if current_user.id != user_id and not current_user.is_admin:
            logger.warning(f"Permiso denegado: usuario {current_user.id} intentó editar usuario {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar este usuario"
            )

        # Verificar duplicados si se actualiza username o email
        if user.username:
            existing = await crud_user.get_user_by_username(db, username=user.username)
            if existing and existing.id != user_id:
                raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
        if user.email:
            existing = await crud_user.get_user_by_email(db, email=user.email)
            if existing and existing.id != user_id:
                raise HTTPException(status_code=400, detail="El correo electrónico ya está en uso")

        db_user = await crud_user.update_user(db, user_id=user_id, user_update=user)
        if not db_user:
            logger.warning(f"Usuario no encontrado para actualizar: ID={user_id}")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        logger.info(f"Usuario actualizado: ID={user_id}")
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar el usuario")



@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Elimina un usuario (soft delete). Solo el propio usuario o un admin puede hacerlo.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta eliminar usuario: ID={user_id}")

        # Verificar permisos
        if current_user.id != user_id and not current_user.is_admin:
            logger.warning(f"Permiso denegado: usuario {current_user.id} intentó eliminar usuario {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este usuario"
            )

        success = await crud_user.delete_user(db, user_id=user_id)
        if not success:
            logger.warning(f"Usuario no encontrado para eliminar: ID={user_id}")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        logger.info(f"Usuario eliminado (soft): ID={user_id}")
        return {"message": "Usuario eliminado correctamente"}

    except Exception as e:
        logger.error(f"Error al eliminar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar el usuario")




@router.post("/{user_id}/restore", response_model=User)
@limiter.limit("5/hour")
async def restore_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Security(require_admin)
):
    """
    Restaura un usuario eliminado. Solo accesible para administradores.
    """
    try:
        logger.info(f"Administrador {admin.id} intenta restaurar usuario: ID={user_id}")

        success = await crud_user.restore_user(db, user_id=user_id)
        if not success:
            logger.warning(f"Usuario eliminado no encontrado: ID={user_id}")
            raise HTTPException(status_code=404, detail="Usuario eliminado no encontrado")

        db_user = await crud_user.get_user(db, user_id=user_id)
        logger.info(f"Usuario restaurado: ID={user_id}")
        return db_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al restaurar usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar el usuario")



@router.get("/{user_id}/posts", response_model=list[Post])
@limiter.limit("50/minute")
async def read_user_posts(
    request: Request,
    user_id: int,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene los posts de un usuario.
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo posts del usuario: ID={user_id}")
        posts = await crud_post.get_posts_by_user(db, user_id=user_id, skip=skip, limit=limit)
        return posts
    except Exception as e:
        logger.error(f"Error al obtener posts del usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener los posts del usuario")



@router.get("/deleted/", response_model=list[User])
@limiter.limit("10/minute")
async def read_deleted_users(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    admin: UserModel = Security(require_admin)
):
    """
    Obtiene usuarios eliminados. Solo accesible para administradores.
    """
    try:
        logger.info(f"Administrador {admin.id} intenta acceder a usuarios eliminados")
        users = await crud_user.get_deleted_users(db, skip=skip, limit=limit)
        logger.info(f"Usuarios eliminados obtenidos: {len(users)}")
        return users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener usuarios eliminados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener usuarios eliminados")