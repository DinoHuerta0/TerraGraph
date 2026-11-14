"""Datos y dobles de prueba compartidos por las pruebas del servicio y de la API."""

import uuid
from datetime import UTC, datetime

from app.models import Analysis

VPC = "aws_vpc.main"
SUBNET = "aws_subnet.public"


def resource(address: str) -> dict:
    type_, name = address.split(".")
    return {
        "address": address,
        "type": type_,
        "name": name,
        "provider_name": "registry.terraform.io/hashicorp/aws",
        "change": {"actions": ["create"]},
    }


# La subnet depende de la VPC.
PLAN = {
    "resource_changes": [resource(VPC), resource(SUBNET)],
    "configuration": {
        "root_module": {
            "resources": [
                {"address": VPC, "mode": "managed", "type": "aws_vpc", "name": "main"},
                {
                    "address": SUBNET,
                    "mode": "managed",
                    "type": "aws_subnet",
                    "name": "public",
                    "expressions": {"vpc_id": {"references": ["aws_vpc.main.id"]}},
                },
            ]
        }
    },
}


class InMemoryAnalysisRepository:
    """Mismo `save` y `get` que AnalysisRepository, pero en un dict.

    Pone `id` y `created_at` como lo harían SQLAlchemy y Postgres.
    """

    def __init__(self) -> None:
        self.analyses: dict[uuid.UUID, Analysis] = {}

    def save(self, analysis: Analysis) -> Analysis:
        analysis.id = uuid.uuid4()
        analysis.created_at = datetime.now(UTC)
        self.analyses[analysis.id] = analysis
        return analysis

    def get(self, analysis_id: uuid.UUID) -> Analysis | None:
        return self.analyses.get(analysis_id)
