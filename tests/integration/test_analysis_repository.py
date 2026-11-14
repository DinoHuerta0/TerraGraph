import uuid

from sqlalchemy import text

from app.models import Analysis
from app.repositories import AnalysisRepository

PLAN = {
    "format_version": "1.2",
    "resource_changes": [
        {"address": "aws_vpc.main", "change": {"actions": ["create"]}},
    ],
}


def make_analysis(name="demo"):
    return Analysis(name=name, plan_json=PLAN, resource_count=1)


def test_save_assigns_id_and_created_at(session):
    saved = AnalysisRepository(session).save(make_analysis())

    assert isinstance(saved.id, uuid.UUID)
    assert saved.created_at is not None


def test_get_returns_saved_analysis(session):
    repository = AnalysisRepository(session)
    analysis_id = repository.save(make_analysis()).id
    # Se vacía la sesión para que get() lea de Postgres y no del objeto en memoria.
    session.expunge_all()

    loaded = repository.get(analysis_id)

    assert loaded.id == analysis_id
    assert loaded.name == "demo"
    assert loaded.plan_json == PLAN
    assert loaded.resource_count == 1


def test_get_unknown_id_returns_none(session):
    assert AnalysisRepository(session).get(uuid.uuid4()) is None


def test_saved_analyses_get_different_ids(session):
    repository = AnalysisRepository(session)

    first = repository.save(make_analysis("a"))
    second = repository.save(make_analysis("b"))

    assert first.id != second.id


def test_plan_is_stored_as_jsonb(session):
    analysis_id = AnalysisRepository(session).save(make_analysis()).id

    stored_type = session.scalar(
        text("SELECT pg_typeof(plan_json)::text FROM analyses WHERE id = :id"),
        {"id": analysis_id},
    )

    assert stored_type == "jsonb"
