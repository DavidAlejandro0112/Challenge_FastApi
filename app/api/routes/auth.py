from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.core.logging import logger
from app.crud import user as crud_user
from app.schemas.auth import UserAuth, Token, UserInDB
from app.schemas.user import UserCreate
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.security import OAuth2PasswordRequestForm

# Rate limiting por IP
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_user(
    request: Request, user: UserAuth, db: AsyncSession = Depends(get_db)
):

    try:
        logger.info(
            f"Intento de registro: username='{user.username}', email='{user.email}'"
        )

        # Verificar si el username ya existe
        db_user = await crud_user.get_user_by_username(db, username=user.username)
        if db_user:
            logger.warning(f"Registro fallido: username ya existe '{user.username}'")
            raise HTTPException(
                status_code=400, detail="El nombre de usuario ya está registrado"
            )

        # Verificar si el email ya existe
        db_user = await crud_user.get_user_by_email(db, email=user.email)
        if db_user:
            logger.warning(f"Registro fallido: email ya existe '{user.email}'")
            raise HTTPException(
                status_code=400, detail="El correo electrónico ya está registrado"
            )

        # Crear usuario
        user_create = UserCreate(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            password=user.password,
            is_active=True,
            is_admin=False,
        )
        db_user = await crud_user.create_user(db=db, user=user_create)

        logger.info(
            f"Usuario registrado exitosamente: ID={db_user.id}, username='{db_user.username}'"
        )

        return UserInDB(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado durante registro: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_user(
    request: Request,  # Necesario para slowapi
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):

    username = form_data.username
    password = form_data.password

    try:
        logger.info(f"Intento de login: username='{username}'")

        db_user = await crud_user.authenticate_user(db, username, password)
        if not db_user:
            logger.warning(f"Login fallido: credenciales inválidas para '{username}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nombre de usuario o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not db_user.is_active:
            logger.warning(f"Login fallido: usuario inactivo '{username}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo"
            )

        # Crear token de acceso
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.username, "id": str(db_user.id)},
            expires_delta=access_token_expires,
        )

        logger.info(f"Login exitoso: username='{db_user.username}', ID={db_user.id}")
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado durante login: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
