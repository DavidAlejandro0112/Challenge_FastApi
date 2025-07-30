# app/api/deps.py
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_access_token
from app.crud.user import get_user
from app.core.database import get_db
from app.schemas.user import User  

async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise credentials_exception
    token = auth_header[7:]  
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception
    user_id = int(payload["sub"])
    db_user = await get_user(db, user_id=user_id)
    if not db_user or not db_user.is_active:
        raise credentials_exception
    return User.model_validate(db_user)  

def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not allowed: admin privileges required"
        )
    return current_user