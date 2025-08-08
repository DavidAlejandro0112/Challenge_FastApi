from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud import post as crud_post
from app.crud import user as crud_user
from app.crud import comment as crud_comment
from app.crud import tag as crud_tag
from app.schemas.comment import CommentCreate
from app.schemas.post import Post, PostCreate, PostUpdate, Comment, PostWithRelations
from app.schemas.tag import Tag
from app.schemas.common import PaginatedResponse
from app.models.user import User
from app.core.logging import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting por IP
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")  # Evita spam de publicaciones
async def create_post(
    request: Request,
    post: PostCreate,
    author_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Crea un nuevo post. Solo el usuario autenticado puede crear posts.
    El `author_id` debe coincidir con el usuario autenticado o ser admin.
    """
    try:
        logger.info(
            f"Usuario {current_user.id} intenta crear post para author_id={author_id}"
        )

        # Verificar que el author_id sea válido
        if author_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó crear post como {author_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes crear un post en nombre de otro usuario",
            )

        db_user = await crud_user.get_user(db, user_id=author_id)
        if not db_user:
            logger.warning(
                f"Intento de crear post con usuario no existente: ID={author_id}"
            )
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        db_post = await crud_post.create_post(db=db, post=post, author_id=author_id)
        logger.info(f"Post creado: ID={db_post.id}, Autor={author_id}")
        return db_post

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/", response_model=PaginatedResponse[Post])
@limiter.limit("50/minute")
async def read_posts(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene una lista paginada de posts activos.
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo posts (skip={skip}, limit={limit})")
        db_posts, total = await crud_post.get_posts_paginated(
            db, skip=skip, limit=limit
        )

        pydantic_posts = [Post.model_validate(db_post) for db_post in db_posts]
        page = skip // limit + 1 if limit > 0 else 1
        size = len(pydantic_posts)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        logger.info(f"Posts obtenidos: {size} de {total} totales")
        return PaginatedResponse[Post](
            items=pydantic_posts,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Error al obtener posts paginados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener posts")


@router.get("/{post_id}", response_model=PostWithRelations)
@limiter.limit("50/minute")
async def read_post(request: Request, post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Obtiene un post por ID con todas sus relaciones (autor, comentarios, tags).
    Acceso público.
    """
    try:
        logger.info(f"Obteniendo post con relaciones: ID={post_id}")
        db_post = await crud_post.get_post(db, post_id=post_id)
        if not db_post:
            logger.warning(f"Post no encontrado: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post no encontrado")
        return db_post
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener el post")


@router.patch("/{post_id}", response_model=Post)
@limiter.limit("10/hour")
async def update_post(
    request: Request,
    post_id: int,
    post: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Actualiza un post. Solo el autor o un admin puede hacerlo.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta actualizar post: ID={post_id}")

        db_post = await crud_post.get_post(db, post_id=post_id)
        if not db_post:
            logger.warning(f"Intento de actualizar post no encontrado: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post no encontrado")

        # Verificar permisos
        if db_post.author_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó editar post {post_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar este post",
            )

        updated_post = await crud_post.update_post(
            db, post_id=post_id, post_update=post
        )
        if not updated_post:
            raise HTTPException(status_code=500, detail="Error al actualizar el post")

        logger.info(f"Post actualizado: ID={post_id}")
        return updated_post

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al actualizar el post")


@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def delete_post(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Elimina un post (soft delete). Solo el autor o un admin puede hacerlo.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta eliminar post: ID={post_id}")

        db_post = await crud_post.get_post(db, post_id=post_id)
        if not db_post:
            logger.warning(f"Post no encontrado para eliminar: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post no encontrado")

        # Verificar permisos
        if db_post.author_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó eliminar post {post_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este post",
            )

        success = await crud_post.delete_post(db, post_id=post_id)
        if not success:
            raise HTTPException(status_code=500, detail="Error al eliminar el post")

        logger.info(f"Post eliminado (soft): ID={post_id}")
        return {"message": "Post eliminado correctamente"}

    except Exception as e:
        logger.error(f"Error al eliminar post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar el post")


# ========================
# RESTAURAR POST
# ========================


@router.post("/{post_id}/restore", response_model=Post)
@limiter.limit("5/hour")
async def restore_post(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Restaura un post eliminado. Solo un admin puede hacerlo.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta restaurar post: ID={post_id}")

        if not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó restaurar post {post_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden restaurar posts",
            )

        success = await crud_post.restore_post(db, post_id=post_id)
        if not success:
            logger.warning(f"Post eliminado no encontrado: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post eliminado no encontrado")

        db_post = await crud_post.get_post(db, post_id=post_id)
        logger.info(f"Post restaurado: ID={post_id}")
        return db_post

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al restaurar post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al restaurar el post")


# ========================
# LISTAR POSTS ELIMINADOS
# ========================


@router.get("/deleted/", response_model=PaginatedResponse[Post])
@limiter.limit("10/minute")
async def read_deleted_posts(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Obtiene posts eliminados. Solo accesible para administradores.
    """
    try:
        logger.info(f"Usuario {current_user.id} intenta acceder a posts eliminados")

        if not current_user.is_admin:
            logger.warning(
                f"Acceso denegado a posts eliminados para usuario {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: solo administradores",
            )

        db_posts, total = await crud_post.get_deleted_posts_paginated(
            db, skip=skip, limit=limit
        )
        pydantic_posts = [Post.model_validate(db_post) for db_post in db_posts]
        page = skip // limit + 1 if limit > 0 else 1
        size = len(pydantic_posts)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        logger.info(f"Posts eliminados obtenidos: {size} de {total} totales")
        return PaginatedResponse[Post](
            items=pydantic_posts,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener posts eliminados: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener posts eliminados")


@router.post(
    "/{post_id}/comments", response_model=Comment, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/hour")
async def create_comment_for_post(
    request: Request,
    post_id: int,
    author_id: int,
    comment: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Crea un comentario en un post. El autor del comentario es el usuario autenticado.
    """
    try:
        logger.debug(f"Buscando username para author_id={author_id}")
        result = await db.execute(select(User.username).where(User.id == author_id))
        author_name = result.scalar_one_or_none()
        logger.info(f"Usuario {current_user.id} crea comentario en post: ID={post_id}")

        db_post = await crud_post.get_post(db, post_id=post_id)
        if not db_post:
            logger.warning(f"Post no encontrado para comentario: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post no encontrado")

        db_comment = await crud_comment.create_comment(
            db=db, comment=comment, post_id=post_id, author_id=current_user.id
        )
        logger.info(f"Comentario creado: ID={db_comment.id}, Post={post_id}")
        return db_comment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear comentario en post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al crear el comentario")


# ========================
# AÑADIR TAG A POST
# ========================


@router.post("/{post_id}/tags/{tag_id}", response_model=PostWithRelations)
@limiter.limit("10/hour")
async def add_tag_to_post(
    request: Request,
    post_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Añade un tag a un post. Solo el autor del post o un admin puede hacerlo.
    """
    try:
        logger.info(
            f"Usuario {current_user.id} intenta añadir tag {tag_id} al post {post_id}"
        )

        db_post = await crud_post.get_post(db, post_id=post_id)
        if not db_post:
            logger.warning(f"Post no encontrado: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post no encontrado")

        # Verificar permisos
        if db_post.author_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó editar tags del post {post_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar los tags de este post",
            )

        success = await crud_post.add_tag_to_post(db, post_id=post_id, tag_id=tag_id)
        if not success:
            logger.warning(f"No se pudo añadir tag {tag_id} al post {post_id}")
            raise HTTPException(
                status_code=404, detail="Tag no encontrado o ya asociado"
            )

        db_post = await crud_post.get_post(db, post_id=post_id)
        logger.info(f"Tag {tag_id} añadido al post {post_id}")
        return db_post

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al añadir tag {tag_id} al post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al añadir el tag")


# ========================
# REMOVER TAG DE POST
# ========================


@router.delete("/{post_id}/tags/{tag_id}", response_model=PostWithRelations)
@limiter.limit("10/hour")
async def remove_tag_from_post(
    request: Request,
    post_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(crud_user.get_current_active_user),
):
    """
    Remueve un tag de un post. Solo el autor del post o un admin puede hacerlo.
    """
    try:
        logger.info(
            f"Usuario {current_user.id} intenta remover tag {tag_id} del post {post_id}"
        )

        db_post = await crud_post.get_post(db, post_id=post_id)
        if not db_post:
            logger.warning(f"Post no encontrado: ID={post_id}")
            raise HTTPException(status_code=404, detail="Post no encontrado")

        # Verificar permisos
        if db_post.author_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Permiso denegado: usuario {current_user.id} intentó editar tags del post {post_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar los tags de este post",
            )

        success = await crud_post.remove_tag_from_post(
            db, post_id=post_id, tag_id=tag_id
        )
        if not success:
            logger.warning(f"No se pudo remover tag {tag_id} del post {post_id}")
            raise HTTPException(
                status_code=404, detail="Tag no encontrado o no asociado"
            )

        db_post = await crud_post.get_post(db, post_id=post_id)
        logger.info(f"Tag {tag_id} removido del post {post_id}")
        return db_post

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al remover tag {tag_id} del post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al remover el tag")
