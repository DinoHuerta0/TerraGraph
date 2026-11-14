import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Analysis

PLAN = {"format_version": "1.2", "planned_values": {"root_module": {}}}


@pytest.fixture
def session():
    # SQLite en memoria: prueba el modelo sin Postgres. Las pruebas contra
    # Postgres real están en tests/integration/.
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_table_has_expected_columns():
    columns = set(Analysis.__table__.columns.keys())

    assert columns == {"id", "name", "plan_json", "resource_count", "created_at"}
    assert Analysis.__tablename__ == "analyses"


def test_new_analysis_gets_uuid_and_created_at(session):
    analysis = Analysis(name="demo", plan_json=PLAN, resource_count=3)
    session.add(analysis)
    session.commit()

    assert isinstance(analysis.id, uuid.UUID)
    assert analysis.created_at is not None


def test_plan_json_is_stored_and_read_back(session):
    analysis = Analysis(name="demo", plan_json=PLAN, resource_count=3)
    session.add(analysis)
    session.commit()
    analysis_id = analysis.id
    # Se sacan los objetos de la sesión para que get() lea de la base, no de memoria.
    session.expunge_all()

    loaded = session.get(Analysis, analysis_id)

    assert loaded.name == "demo"
    assert loaded.plan_json == PLAN
    assert loaded.resource_count == 3


def test_ids_are_unique(session):
    first = Analysis(name="a", plan_json=PLAN, resource_count=0)
    second = Analysis(name="b", plan_json=PLAN, resource_count=0)
    session.add_all([first, second])
    session.commit()

    assert first.id != second.id


def test_name_is_required(session):
    session.add(Analysis(name=None, plan_json=PLAN, resource_count=0))

    with pytest.raises(IntegrityError):
        session.commit()
