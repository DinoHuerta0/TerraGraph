"""Entorno de Alembic: conecta las migraciones con la base y con los modelos."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Importar los modelos registra sus tablas en Base.metadata.
import app.models  # noqa: F401
from app.db import Base, database_url

config = context.config

# Solo hay archivo .ini cuando se usa la terminal; las pruebas crean Config() en código.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Lo que usa `alembic revision --autogenerate` y `alembic check` para comparar
# los modelos contra la base.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: imprime el SQL sin conectarse a la base."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Se conecta a la base y aplica las migraciones.

    Si quien llama ya trae una conexión (las pruebas), se usa esa; si no, se
    abre una con la misma URL que usa la app.
    """
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_migrations(connection)
        return

    engine = create_engine(database_url())
    with engine.connect() as connection:
        _run_migrations(connection)
    engine.dispose()


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
