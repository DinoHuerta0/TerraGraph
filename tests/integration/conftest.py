"""Fixtures para probar contra un Postgres real.

Local: docker compose -f docker/docker-compose.yml up -d && alembic upgrade head
CI: el job `test` levanta Postgres como servicio y corre las migraciones antes.
"""

import os

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import database_url


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(database_url())
    try:
        with engine.connect() as connection:
            tables = inspect(connection).get_table_names()
    except OperationalError:
        engine.dispose()
        # En CI Postgres siempre debe estar: si no responde, la prueba falla
        # en lugar de saltarse sin que nadie lo note.
        if os.environ.get("CI"):
            raise
        pytest.skip("Postgres no responde; levántalo con Docker Compose")
    if "analyses" not in tables:
        pytest.fail("No existe la tabla analyses; corre `alembic upgrade head`")
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Sesión dentro de una transacción que se deshace al terminar la prueba.

    Con `create_savepoint`, el commit() del repositorio solo cierra un
    savepoint; el rollback final borra todo y la base queda limpia.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()
