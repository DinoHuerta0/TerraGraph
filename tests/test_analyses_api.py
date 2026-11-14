"""Pruebas de los endpoints de análisis con el TestClient de FastAPI.

El servicio usa un repositorio en memoria, así que no necesitan Postgres.
Primero van los casos exitosos y después los códigos de error (404, 413 y 422).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.analyses import get_analysis_service
from app.services import MAX_PLAN_BYTES, AnalysisService
from tests.helpers import PLAN, SUBNET, VPC, InMemoryAnalysisRepository


@pytest.fixture
def client():
    service = AnalysisService(InMemoryAnalysisRepository())
    app.dependency_overrides[get_analysis_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def analysis_id(client):
    response = client.post("/api/analyses", json={"name": "demo", "plan": PLAN})
    return response.json()["id"]


def test_post_analysis_stores_plan_and_returns_id_and_analysis(client):
    response = client.post("/api/analyses", json={"name": "demo", "plan": PLAN})

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["name"] == "demo"
    assert body["created_at"]
    assert body["resource_count"] == 2
    assert body["creation_order"] == [VPC, SUBNET]
    assert body["parallel_levels"] == [[VPC], [SUBNET]]
    assert body["cycles"] == []
    assert body["graph"]["edges"] == [{"source": SUBNET, "target": VPC}]


def test_post_analysis_strips_spaces_from_name(client):
    response = client.post("/api/analyses", json={"name": "  demo  ", "plan": PLAN})

    assert response.json()["name"] == "demo"


def test_get_analysis_returns_the_same_as_post(client):
    created = client.post("/api/analyses", json={"name": "demo", "plan": PLAN})

    response = client.get(f"/api/analyses/{created.json()['id']}")

    assert response.status_code == 200
    assert response.json() == created.json()


def test_get_blast_radius_returns_affected_resources(client, analysis_id):
    response = client.get(
        f"/api/analyses/{analysis_id}/blast-radius", params={"address": VPC}
    )

    assert response.status_code == 200
    assert response.json() == {"address": VPC, "affected": [SUBNET]}


@pytest.mark.parametrize(
    ("format", "media_type", "start"),
    [
        ("json", "application/json", "{"),
        ("dot", "text/vnd.graphviz", "digraph"),
        ("mermaid", "text/plain", "flowchart"),
    ],
)
def test_get_export_returns_graph_in_each_format(
    client, analysis_id, format, media_type, start
):
    response = client.get(
        f"/api/analyses/{analysis_id}/export", params={"format": format}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert response.text.startswith(start)


# --- Errores ------------------------------------------------------------------
# Los errores del servicio responden `{"detail": "<mensaje>"}`. Los 422 de
# validación los da FastAPI antes de llegar al router, con `detail` como lista.


@pytest.mark.parametrize(
    ("suffix", "params"),
    [
        ("", None),
        ("/blast-radius", {"address": VPC}),
        ("/export", {"format": "json"}),
    ],
    ids=["get", "blast_radius", "export"],
)
def test_unknown_id_returns_404(client, suffix, params):
    analysis_id = uuid.uuid4()

    response = client.get(f"/api/analyses/{analysis_id}{suffix}", params=params)

    assert response.status_code == 404
    assert response.json() == {"detail": f"No existe el análisis {analysis_id}"}


def test_blast_radius_of_unknown_resource_returns_404(client, analysis_id):
    response = client.get(
        f"/api/analyses/{analysis_id}/blast-radius",
        params={"address": "aws_instance.missing"},
    )

    assert response.status_code == 404
    assert "aws_instance.missing" in response.json()["detail"]


def test_plan_larger_than_limit_returns_413(client):
    plan = {**PLAN, "padding": "x" * MAX_PLAN_BYTES}

    response = client.post("/api/analyses", json={"name": "demo", "plan": plan})

    assert response.status_code == 413
    assert str(MAX_PLAN_BYTES) in response.json()["detail"]


def test_invalid_plan_returns_422_with_parser_message(client):
    # Es un objeto, así que pasa la validación de FastAPI, pero no es un plan.
    response = client.post("/api/analyses", json={"name": "demo", "plan": {}})

    assert response.status_code == 422
    assert response.json() == {"detail": "El JSON no parece un plan de Terraform"}


@pytest.mark.parametrize(
    "body",
    [
        {"plan": PLAN},
        {"name": "   ", "plan": PLAN},
        {"name": "x" * 201, "plan": PLAN},
        {"name": "demo"},
        {"name": "demo", "plan": ["no", "es", "un", "objeto"]},
    ],
    ids=["no_name", "blank_name", "long_name", "no_plan", "plan_not_object"],
)
def test_invalid_body_returns_422(client, body):
    response = client.post("/api/analyses", json=body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_id_that_is_not_a_uuid_returns_422(client):
    response = client.get("/api/analyses/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.parametrize("params", [{}, {"address": ""}], ids=["missing", "empty"])
def test_blast_radius_without_address_returns_422(client, analysis_id, params):
    response = client.get(f"/api/analyses/{analysis_id}/blast-radius", params=params)

    assert response.status_code == 422


@pytest.mark.parametrize("params", [{}, {"format": "png"}], ids=["missing", "png"])
def test_export_with_invalid_format_returns_422(client, analysis_id, params):
    response = client.get(f"/api/analyses/{analysis_id}/export", params=params)

    assert response.status_code == 422
