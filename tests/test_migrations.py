from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.models import Analysis

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


@pytest.fixture
def connection():
    # SQLite en memoria: revisa las migraciones sin Postgres. Contra Postgres
    # real, CI corre `alembic upgrade head` antes de las pruebas.
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        yield connection
    engine.dispose()


def alembic_config(connection):
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("path_separator", "os")
    # env.py usa esta conexión en lugar de abrir una con DATABASE_URL.
    config.attributes["connection"] = connection
    return config


def test_upgrade_creates_analyses_table_matching_the_model(connection):
    command.upgrade(alembic_config(connection), "head")

    columns = inspect(connection).get_columns("analyses")
    names = {column["name"] for column in columns}
    assert names == set(Analysis.__table__.columns.keys())


def test_downgrade_to_base_drops_analyses_table(connection):
    config = alembic_config(connection)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    assert "analyses" not in inspect(connection).get_table_names()
