"""La API completa contra Postgres: router, servicio, repositorio y base.

En tests/test_analyses_api.py se reemplaza el servicio por uno en memoria. Aquí
solo se reemplaza la sesión, por la del fixture `session`, que deshace todo al
terminar la prueba.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from tests.helpers import PLAN, SUBNET, VPC


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_saved_analysis_can_be_opened_by_its_id(client):
    created = client.post("/api/analyses", json={"name": "demo", "plan": PLAN})

    assert created.status_code == 201
    response = client.get(f"/api/analyses/{created.json()['id']}")
    assert response.status_code == 200
    assert response.json() == created.json()
    assert response.json()["creation_order"] == [VPC, SUBNET]


def test_unknown_id_returns_404(client):
    response = client.get(f"/api/analyses/{uuid.uuid4()}")

    assert response.status_code == 404
