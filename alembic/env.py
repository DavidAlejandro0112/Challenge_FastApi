# alembic/env.py
import warnings
warnings.filterwarnings("ignore", message="Could not determine revision")

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base
from app.core.config import settings
import os
import sys

# Añade el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa todos los modelos
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.tag import Tag

config = context.config

# Configuración de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configura la URL de la base de datos
def get_database_url():
    """Convierte la URL asyncpg a psycopg2 para Alembic"""
    async_url = str(settings.DATABASE_URL)
    sync_url = async_url.replace("+asyncpg", "+psycopg2")
    if "postgresql" in sync_url and "sslmode" not in sync_url:
        sync_url += "?sslmode=require"
    return sync_url

# Asigna la URL al config
config.set_main_option('sqlalchemy.url', get_database_url())

# Metadatos objetivo
target_metadata = Base.metadata

# ========================
# FUNCIONES DE MIGRACIÓN
# ========================

def run_migrations_online():
    """Ejecuta migraciones en modo online (recomendado)"""
    # Asegúrate de que la sección exista
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        raise RuntimeError(f"Sección no encontrada: {config.config_ini_section}")

    # Asigna la URL directamente al diccionario
    configuration['sqlalchemy.url'] = get_database_url()

    connectable = engine_from_config(
        configuration,           # ✅ Ahora es un dict seguro
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        echo=False
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,
            process_revision_directives=lambda x, y, z: None,
        )

        with context.begin_transaction():
            context.run_migrations()

def run_migrations_offline():
    """Ejecuta migraciones en modo offline"""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True
    )

    with context.begin_transaction():
        context.run_migrations()

# ========================
# EJECUCIÓN
# ========================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()