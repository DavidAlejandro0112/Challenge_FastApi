from authlib.integrations.starlette_client import OAuth
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
oauth = OAuth()

try:
    # Registrar Google como proveedor OAuth
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    logger.info("Proveedor OAuth 'google' registrado correctamente.")
except Exception as e:
    logger.error(f"Error al registrar el proveedor OAuth 'google': {e}")
    raise