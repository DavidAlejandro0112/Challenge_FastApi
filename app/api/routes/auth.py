from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.crud import user as crud_user
from app.schemas.auth import UserAuth, UserLogin, Token, UserInDB
from app.schemas.user import UserCreate

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserAuth, db: AsyncSession = Depends(get_db)):
    """
    Registrar un nuevo usuario
    
    Crea una nueva cuenta de usuario en el sistema.
    
    ## Parámetros:
    - **user**: Objeto con los datos del usuario a registrar
    
    ## Respuesta:
    - Retorna los datos del usuario creado (sin la contraseña)
    
    ## Errores:
    - **400**: Username o email ya registrado
    """
    # Verificar si el username ya existe
    db_user = await crud_user.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Verificar si el email ya existe
    db_user = await crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Crear usuario
    user_create = UserCreate(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        password=user.password
    )
    db_user = await crud_user.create_user(db=db, user=user_create)
    
    return UserInDB(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name
    )

@router.post("/login", response_model=Token)
async def login_user(user: UserLogin, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token de acceso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
        )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user = Depends(crud_user.get_current_active_user)):
    return UserInDB(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name
    )