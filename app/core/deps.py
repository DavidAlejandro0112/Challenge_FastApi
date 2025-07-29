
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_access_token
from app.crud.user import get_user_by_email
from app.core.database import get_db
from app.schemas.user import User as User

async def get_current_active_user(
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Obtener el token del header Authorization
    async def _get_user_from_request(request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise credentials_exception
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if payload is None or "sub" not in payload:
            raise credentials_exception
        user = await get_user_by_email(db, email=payload["sub"])
        if user is None or not user.is_active:
            raise credentials_exception
        return user

    return Depends(_get_user_from_request)

def require_admin(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not allowed: admin privileges required"
        )
    return current_user