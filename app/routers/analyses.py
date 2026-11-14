"""Endpoints de análisis: subir un plan, consultarlo, radio de impacto y exportar."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.parser import PlanParseError
from app.db import get_session
from app.repositories import AnalysisRepository
from app.schemas import AnalysisCreate, AnalysisResponse, BlastRadiusResponse
from app.services import AnalysisNotFoundError, AnalysisService, PlanTooLargeError

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

# Errores del servicio y el código HTTP con el que responde la API.
# main.py los registra con `add_exception_handler`, así los endpoints no
# necesitan try/except para cada uno.
ERROR_STATUS_CODES: dict[type[Exception], int] = {
    AnalysisNotFoundError: status.HTTP_404_NOT_FOUND,
    PlanTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    PlanParseError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

# Los mismos formatos que GraphAnalyzer.export. Con Literal, FastAPI responde 422
# a un formato inválido y /docs muestra las opciones.
ExportFormat = Literal["json", "dot", "mermaid"]
EXPORT_MEDIA_TYPES: dict[str, str] = {
    "json": "application/json",
    "dot": "text/vnd.graphviz",
    "mermaid": "text/plain",
}


async def handle_service_error(request: Request, error: Exception) -> JSONResponse:
    """Convierte un error del servicio en una respuesta con su código HTTP.

    El cuerpo es `{"detail": ...}`, el mismo formato que usa FastAPI.
    """
    status_code = next(
        code
        for error_type, code in ERROR_STATUS_CODES.items()
        if isinstance(error, error_type)
    )
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


def get_analysis_service(
    session: Annotated[Session, Depends(get_session)],
) -> AnalysisService:
    """El servicio con un repositorio sobre la sesión de esta petición.

    Las pruebas lo reemplazan con `app.dependency_overrides` para no usar la base.
    """
    return AnalysisService(AnalysisRepository(session))


Service = Annotated[AnalysisService, Depends(get_analysis_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
def post_analysis(body: AnalysisCreate, service: Service) -> AnalysisResponse:
    """Guarda un plan y devuelve su `id` y su análisis."""
    return AnalysisResponse.from_detail(service.create(body.name, body.plan))


@router.get("/{analysis_id}")
def get_analysis(analysis_id: uuid.UUID, service: Service) -> AnalysisResponse:
    """Grafo, orden de creación, niveles paralelos y ciclos."""
    return AnalysisResponse.from_detail(service.get(analysis_id))


@router.get("/{analysis_id}/blast-radius")
def get_blast_radius(
    analysis_id: uuid.UUID,
    address: Annotated[str, Query(min_length=1)],
    service: Service,
) -> BlastRadiusResponse:
    """Recursos que se rompen si se destruye `address`."""
    try:
        affected = service.blast_radius(analysis_id, address)
    except KeyError:
        # El análisis existe pero el recurso no está en el plan.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"El recurso {address!r} no está en el plan"
        ) from None
    return BlastRadiusResponse(address=address, affected=affected)


@router.get("/{analysis_id}/export", response_class=Response)
def get_export(
    analysis_id: uuid.UUID,
    format: Annotated[ExportFormat, Query()],
    service: Service,
) -> Response:
    """El grafo como texto en JSON, DOT (Graphviz) o Mermaid."""
    content = service.export(analysis_id, format)
    return Response(content, media_type=EXPORT_MEDIA_TYPES[format])
