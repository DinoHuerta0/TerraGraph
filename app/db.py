"""Conexión a PostgreSQL con SQLAlchemy."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Coincide con el Postgres de docker/docker-compose.yml; en producción llega DATABASE_URL.
LOCAL_DATABASE_URL = (
    "postgresql+psycopg://terragraph:terragraph@localhost:5432/terragraph"
)


def database_url() -> str:
    """URL de la base: `DATABASE_URL` si existe; si no, el Postgres local.

    Neon entrega la URL como `postgresql://...`, y con ese prefijo SQLAlchemy
    buscaría psycopg2. Se cambia a `postgresql+psycopg://` para usar psycopg 3.
    """
    url = os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL)
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


class Base(DeclarativeBase):
    """Clase base de los modelos; Alembic lee de aquí las tablas."""


# create_engine no se conecta todavía: la conexión se abre en la primera consulta.
engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
