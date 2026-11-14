"""Formato de entrada y salida de la API (modelos de Pydantic).

FastAPI usa estos modelos para validar las peticiones (si algo no cuadra responde
`422` sin llegar al router) y para generar la documentación en `/docs`.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, StringConstraints

from app.services import AnalysisDetail

# Mismo largo máximo que la columna `name` del modelo `Analysis`.
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class AnalysisCreate(BaseModel):
    """Cuerpo de `POST /api/analyses`."""

    name: Name
    # El JSON de `terraform show -json`; Pydantic solo revisa que sea un objeto,
    # el servicio revisa que sea un plan válido.
    plan: dict[str, Any]


class AnalysisResponse(BaseModel):
    """Un análisis guardado con su resultado recalculado."""

    id: uuid.UUID
    name: str
    created_at: datetime
    resource_count: int
    graph: dict[str, Any]
    creation_order: list[str]
    parallel_levels: list[list[str]]
    cycles: list[list[str]]

    @classmethod
    def from_detail(cls, detail: AnalysisDetail) -> "AnalysisResponse":
        # Se aplana el resultado: la API responde con un solo objeto.
        return cls(
            id=detail.id,
            name=detail.name,
            created_at=detail.created_at,
            resource_count=detail.resource_count,
            graph=detail.result.graph,
            creation_order=detail.result.creation_order,
            parallel_levels=detail.result.parallel_levels,
            cycles=detail.result.cycles,
        )


class BlastRadiusResponse(BaseModel):
    """Recursos que se rompen si se destruye `address`."""

    address: str
    affected: list[str]
