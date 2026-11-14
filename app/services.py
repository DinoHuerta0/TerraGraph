"""Lógica de la app entre la API y la base: guardar planes y analizarlos."""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.core.analyzer import AnalysisResult, GraphAnalyzer, PlanInput
from app.models import Analysis
from app.repositories import AnalysisRepository

# Límite por plan: como no hay cuentas, evita que se llene la base de datos.
MAX_PLAN_BYTES = 2 * 1024 * 1024  # 2 MB


class PlanTooLargeError(ValueError):
    """El plan pesa más de `MAX_PLAN_BYTES`."""


class AnalysisNotFoundError(LookupError):
    """No existe un análisis con ese id."""


@dataclass(frozen=True)
class AnalysisDetail:
    """Un análisis guardado junto con su resultado recalculado.

    Lo devuelven `create` y `get`, así la API responde igual al subir un plan y
    al abrirlo por su enlace.
    """

    id: uuid.UUID
    name: str
    created_at: datetime
    resource_count: int
    result: AnalysisResult


class AnalysisService:
    """Guarda los planes y recalcula su análisis cada vez que se consultan.

    Solo se guarda el plan, no el resultado: si mejora el núcleo de grafos, los
    análisis viejos se benefician sin migrar datos.
    """

    def __init__(
        self, repository: AnalysisRepository, analyzer: GraphAnalyzer | None = None
    ) -> None:
        # En las pruebas `repository` es un repositorio en memoria: basta con que
        # tenga `save` y `get`.
        self._repository = repository
        self._analyzer = analyzer or GraphAnalyzer()

    def create(self, name: str, plan_json: PlanInput) -> AnalysisDetail:
        """Valida el plan, lo guarda y devuelve su análisis con el id nuevo.

        Lanza `PlanTooLargeError` si pesa más de 2 MB y `PlanParseError` si no
        es un plan de Terraform válido. En ambos casos no se guarda nada.
        """
        self._validate_size(plan_json)
        # Analizar antes de guardar: si el plan no es válido, falla aquí.
        result = self._analyzer.analyze(plan_json)
        # El analizador ya comprobó que es JSON válido, así que esto no falla.
        plan = plan_json if isinstance(plan_json, dict) else json.loads(plan_json)
        analysis = self._repository.save(
            Analysis(
                name=name, plan_json=plan, resource_count=len(result.graph["nodes"])
            )
        )
        return self._detail(analysis, result)

    def get(self, analysis_id: uuid.UUID) -> AnalysisDetail:
        """El análisis guardado, recalculado a partir de su plan."""
        analysis = self._load(analysis_id)
        return self._detail(analysis, self._analyzer.analyze(analysis.plan_json))

    def blast_radius(self, analysis_id: uuid.UUID, address: str) -> list[str]:
        """Recursos afectados al destruir `address`.

        Lanza `KeyError` si el recurso no está en el plan.
        """
        return self._analyzer.blast_radius(self._load(analysis_id).plan_json, address)

    def export(self, analysis_id: uuid.UUID, format: str) -> str:
        """El grafo en `json`, `dot` o `mermaid`.

        Lanza `ValueError` si el formato no es válido.
        """
        return self._analyzer.export(self._load(analysis_id).plan_json, format)

    # --- Auxiliares -----------------------------------------------------------

    def _validate_size(self, plan_json: PlanInput) -> None:
        if isinstance(plan_json, dict):
            plan_json = json.dumps(plan_json)
        if isinstance(plan_json, str):
            # El límite es en bytes: un carácter como "ñ" ocupa 2 en UTF-8.
            plan_json = plan_json.encode()
        if len(plan_json) > MAX_PLAN_BYTES:
            raise PlanTooLargeError(
                f"El plan pesa {len(plan_json)} bytes; el máximo es {MAX_PLAN_BYTES}"
            )

    def _load(self, analysis_id: uuid.UUID) -> Analysis:
        analysis = self._repository.get(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError(f"No existe el análisis {analysis_id}")
        return analysis

    def _detail(self, analysis: Analysis, result: AnalysisResult) -> AnalysisDetail:
        return AnalysisDetail(
            id=analysis.id,
            name=analysis.name,
            created_at=analysis.created_at,
            resource_count=analysis.resource_count,
            result=result,
        )
