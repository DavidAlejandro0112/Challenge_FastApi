from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.oauth import oauth
from app.crud import user as crud_user
from app.schemas.user import UserCreate
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/google", tags=["authentication"])


@router.get("/login")
async def google_login(request: Request):
    """Inicia el flujo de autenticación con Google"""
    try:
        redirect_uri = str(request.url_for('google_callback'))
        logger.info(f"Generando redirección a Google con URI: {redirect_uri}")
        # Asegúrate de que esta redirect_uri ESTÉ REGISTRADA en Google Cloud Console
        return await oauth.google.authorize_redirect(request, redirect_uri) # type: ignore
    except Exception as e:
        logger.error(f"Error al iniciar redirección a Google: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al iniciar login con Google")

@router.get("/callback", name="google_callback") # Asegúrate de tener el 'name' para url_for
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Maneja la respuesta de Google después de la autenticación"""
    try:
        logger.info("Recibida callback de Google")
        # Obtener el token de acceso
        token = await oauth.google.authorize_access_token(request) # type: ignore
        user_info = token.get('userinfo')
        
        if not user_info:
            logger.warning("No se recibió 'userinfo' del token de Google")
            raise HTTPException(status_code=400, detail="No se pudo obtener información del usuario de Google")

        # Extraer información del usuario
        google_id = user_info.get("sub")
        email = user_info.get("email")
        full_name = user_info.get("name", "")
        # picture = user_info.get("picture", "") # Opcional

        if not email:
            logger.warning("Google no proporcionó un email")
            raise HTTPException(status_code=400, detail="Google no proporcionó un email")

        logger.info(f"Usuario autenticado con Google: {email}")

        # Verificar si el usuario ya existe
        db_user = await crud_user.get_user_by_email(db, email=email)
        
        if not db_user:
            logger.info(f"Creando nuevo usuario para {email}")
            # Crear nuevo usuario si no existe
            username = email.split("@")[0]
            temp_username = username
            counter = 1
            while await crud_user.get_user_by_username(db, username=temp_username):
                temp_username = f"{username}_{counter}"
                counter += 1
            username = temp_username
            
            import secrets
            random_password = secrets.token_urlsafe(32)
            
            user_create = UserCreate(
                username=username,
                email=email,
                full_name=full_name,
                password=random_password,
                is_active=True,
                is_admin=False,
            )
            db_user = await crud_user.create_user(db=db, user=user_create)
            logger.info(f"Usuario {db_user.id} creado para {email}")
        else:
            logger.info(f"Usuario existente encontrado: {db_user.id} ({email})")
        
        # Crear token JWT para tu aplicación
        from app.core.security import create_access_token
        from datetime import timedelta
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(db_user.id)}, expires_delta=access_token_expires
        )
        logger.info(f"JWT creado para usuario {db_user.id}")

        # Opción 1: Devolver JSON (útil para pruebas o clientes API)
        # return {"access_token": access_token, "token_type": "bearer"}

        # Opción 2: Redirigir a frontend con token (más común para web apps)
        # Asegúrate de que tu frontend puede manejar este parámetro
        frontend_url = "http://localhost:3000/login-success"  # Cambia según tu frontend
        redirect_url_with_token = f"{frontend_url}?access_token={access_token}&token_type=bearer"
        logger.info(f"Redirigiendo a frontend: {frontend_url}")
        return RedirectResponse(url=redirect_url_with_token)
        
    except Exception as e:
        logger.error(f"Error en callback de Google: {e}", exc_info=True) # Log más detallado
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error en autenticación con Google"
        )
