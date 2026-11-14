"""Pruebas de AnalysisService con un repositorio en memoria (sin base de datos)."""

import json
import uuid

import pytest

from app.core.parser import PlanParseError
from app.services import (
    MAX_PLAN_BYTES,
    AnalysisNotFoundError,
    AnalysisService,
    PlanTooLargeError,
)
from tests.helpers import PLAN, SUBNET, VPC, InMemoryAnalysisRepository


@pytest.fixture
def repository():
    return InMemoryAnalysisRepository()


@pytest.fixture
def service(repository):
    return AnalysisService(repository)


# --- create -------------------------------------------------------------------


def test_create_stores_plan_and_returns_analysis_with_uuid(service, repository):
    detail = service.create("demo", PLAN)

    assert isinstance(detail.id, uuid.UUID)
    assert detail.name == "demo"
    assert detail.created_at is not None
    assert detail.resource_count == 2
    assert detail.result.creation_order == [VPC, SUBNET]
    assert repository.analyses[detail.id].plan_json == PLAN


@pytest.mark.parametrize("plan", [json.dumps(PLAN), json.dumps(PLAN).encode()])
def test_create_accepts_text_and_stores_it_as_dict(service, repository, plan):
    detail = service.create("demo", plan)

    assert repository.analyses[detail.id].plan_json == PLAN


def test_each_plan_gets_a_different_id(service):
    first = service.create("a", PLAN)
    second = service.create("b", PLAN)

    assert first.id != second.id


def test_invalid_plan_is_rejected_and_not_stored(service, repository):
    with pytest.raises(PlanParseError):
        service.create("demo", "{not json")

    assert repository.analyses == {}


# --- límite de 2 MB -----------------------------------------------------------


def test_plan_larger_than_limit_is_rejected_and_not_stored(service, repository):
    too_large = b" " * (MAX_PLAN_BYTES + 1)

    with pytest.raises(PlanTooLargeError):
        service.create("demo", too_large)

    assert repository.analyses == {}


def test_plan_exactly_at_limit_passes_size_check(service):
    # Mide 2 MB justos: pasa el límite y falla después, al analizarlo.
    with pytest.raises(PlanParseError):
        service.create("demo", b" " * MAX_PLAN_BYTES)


def test_limit_counts_bytes_not_characters(service):
    # "ñ" ocupa 2 bytes en UTF-8: son menos de 2 M caracteres, pero más de 2 MB.
    with pytest.raises(PlanTooLargeError):
        service.create("demo", "ñ" * (MAX_PLAN_BYTES // 2 + 1))


def test_large_dict_plan_is_rejected(service):
    plan = {**PLAN, "padding": "x" * MAX_PLAN_BYTES}

    with pytest.raises(PlanTooLargeError):
        service.create("demo", plan)


# --- consultas -----------------------------------------------------------------


def test_get_recalculates_analysis_from_stored_plan(service):
    created = service.create("demo", PLAN)

    detail = service.get(created.id)

    assert detail == created


def test_blast_radius_uses_stored_plan(service):
    analysis_id = service.create("demo", PLAN).id

    assert service.blast_radius(analysis_id, VPC) == [SUBNET]


def test_blast_radius_of_unknown_resource_raises_key_error(service):
    analysis_id = service.create("demo", PLAN).id

    with pytest.raises(KeyError):
        service.blast_radius(analysis_id, "aws_instance.missing")


def test_export_uses_stored_plan(service):
    analysis_id = service.create("demo", PLAN).id

    assert service.export(analysis_id, "mermaid").startswith("flowchart")


def test_export_with_invalid_format_raises_value_error(service):
    analysis_id = service.create("demo", PLAN).id

    with pytest.raises(ValueError):
        service.export(analysis_id, "png")


@pytest.mark.parametrize(
    "call",
    [
        lambda service, analysis_id: service.get(analysis_id),
        lambda service, analysis_id: service.blast_radius(analysis_id, VPC),
        lambda service, analysis_id: service.export(analysis_id, "json"),
    ],
    ids=["get", "blast_radius", "export"],
)
def test_unknown_id_raises_not_found(service, call):
    with pytest.raises(AnalysisNotFoundError):
        call(service, uuid.uuid4())
