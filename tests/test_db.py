import pytest
from sqlalchemy.orm import Session

from app.db import LOCAL_DATABASE_URL, database_url, get_session


def test_database_url_defaults_to_local_postgres(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert database_url() == LOCAL_DATABASE_URL


def test_database_url_uses_environment_variable(monkeypatch):
    url = "postgresql+psycopg://user:pass@db.example.com:5432/app"
    monkeypatch.setenv("DATABASE_URL", url)

    assert database_url() == url


def test_database_url_switches_plain_postgres_urls_to_psycopg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@neon.tech/app?sslmode=require")

    assert database_url() == "postgresql+psycopg://u:p@neon.tech/app?sslmode=require"


def test_get_session_yields_one_session_and_then_closes_it():
    # La sesión no se conecta hasta la primera consulta: no hace falta Postgres.
    sessions = get_session()

    assert isinstance(next(sessions), Session)
    # Lo que hace FastAPI al terminar de responder: el generador sigue, sale del
    # `with` (cierra la sesión) y termina.
    with pytest.raises(StopIteration):
        next(sessions)
