"""Pruebas de los endpoints de análisis con el TestClient de FastAPI.

El servicio usa un repositorio en memoria, así que no necesitan Postgres.
Aquí van los casos exitosos; los códigos de error se prueban en el #18.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.analyses import get_analysis_service
from app.services import AnalysisService
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
