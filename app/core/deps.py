from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.schemas.user import User  # Esquema Pydantic
from app.core.security import oauth2_scheme
from app.core.config import settings
from jose import JWTError, jwt
from app.models.user import User as UserModel  # Modelo SQLAlchemy

# --- Funciones auxiliares locales para evitar importaciones circulares ---

async def _get_user_by_id(db: AsyncSession, user_id: int) -> UserModel | None:
    """Obtiene un usuario por ID."""
    try:
        
        result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
       
        return result.scalar_one_or_none()
    except Exception:
     
        return None

async def _get_user_by_username(db: AsyncSession, username: str) -> UserModel | None:
    """Obtiene un usuario por username."""
    try:
        result = await db.execute(select(UserModel).filter(UserModel.username == username))
        return result.scalar_one_or_none()
    except Exception:
        return None

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User: # Devuelve el esquema Pydantic
    """Obtiene el usuario actual desde el token JWT (usando username como 'sub')"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
       
        
        payload: dict = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # print(f"DEBUG: Payload decodificado: {payload}") # Para depurar
        sub_value = payload.get("sub")
        if not isinstance(sub_value, str)or not sub_value: # isinstance maneja el caso None también
          raise credentials_exception # o manejar el error como corresponda
        sub: str = sub_value
        # sub: str = payload.get("sub") # Anotamos la variable como str
        # print(f"DEBUG: Valor de 'sub' (username): {sub}") # Para depurar
        db_user: UserModel | None = await _get_user_by_username(db, sub)
        # print(f"DEBUG: Usuario encontrado en BD: {db_user}") # Para depurar

        if db_user is None or db_user.is_deleted:
            raise credentials_exception
        
        
        return User.model_validate(db_user) 

    except JWTError:
        
        raise credentials_exception
    #


async def get_current_active_user(
   
    current_user: User = Depends(get_current_user) 
) -> User: # Devuelve el esquema Pydantic
    """Verifica que el usuario esté activo."""
    
    if not current_user.is_active: 
       
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return current_user



def require_admin(
    current_user: User = Depends(get_current_active_user) # Usa el esquema
) -> User: # Devuelve el esquema
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not allowed: admin privileges required"
        )
    return current_user
