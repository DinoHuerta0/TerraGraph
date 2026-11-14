"""Fachada del núcleo: un solo punto de entrada para analizar un plan de Terraform."""

import json
from dataclasses import dataclass

from app.core.blast_radius import BlastRadiusCalculator
from app.core.cycles import CycleDetector
from app.core.exporter import GraphExporter
from app.core.order import CyclicGraphError, OrderPlanner
from app.core.parser import PlanParser

FORMATS = ("json", "dot", "mermaid")

PlanInput = str | bytes | dict


@dataclass(frozen=True)
class AnalysisResult:
    """Resultado completo del análisis de un plan.

    Si el grafo tiene ciclos no existe un orden válido, así que `creation_order` y
    `parallel_levels` quedan vacíos y `cycles` dice dónde está el problema.
    """

    graph: dict  # nodos y aristas, en el mismo formato que GraphExporter.to_json
    creation_order: list[str]
    parallel_levels: list[list[str]]
    cycles: list[list[str]]


class GraphAnalyzer:
    """Orquesta el parser y los analizadores; el resto de la app solo usa esta clase.

    Cada método recibe el plan tal como se guarda (texto o dict), así el servicio
    no necesita saber nada del grafo.
    """

    def __init__(
        self,
        parser: PlanParser | None = None,
        planner: OrderPlanner | None = None,
        blast_radius: BlastRadiusCalculator | None = None,
        exporter: GraphExporter | None = None,
    ) -> None:
        self._parser = parser or PlanParser()
        self._planner = planner or OrderPlanner(CycleDetector())
        self._blast_radius = blast_radius or BlastRadiusCalculator()
        self._exporter = exporter or GraphExporter()

    def analyze(self, plan_json: PlanInput) -> AnalysisResult:
        """Grafo, orden de creación, niveles paralelos y ciclos del plan.

        Lanza `PlanParseError` si el plan no es válido.
        """
        graph = self._parser.parse(plan_json)
        try:
            levels = self._planner.parallel_levels(graph)
            cycles: list[list[str]] = []
        except CyclicGraphError as error:
            # El planner ya buscó los ciclos; se reutilizan en vez de buscarlos otra vez.
            levels = []
            cycles = error.cycles
        return AnalysisResult(
            graph=self._exporter.to_json(graph),
            # El orden de creación son los niveles uno tras otro (igual que en OrderPlanner).
            creation_order=[address for level in levels for address in level],
            parallel_levels=levels,
            cycles=cycles,
        )

    def blast_radius(self, plan_json: PlanInput, address: str) -> list[str]:
        """Recursos que se rompen si se destruye `address`.

        Lanza `KeyError` si el recurso no está en el plan.
        """
        graph = self._parser.parse(plan_json)
        return self._blast_radius.affected_by(graph, address)

    def export(self, plan_json: PlanInput, format: str) -> str:
        """El grafo como texto en `json`, `dot` o `mermaid`.

        Lanza `ValueError` si el formato no es uno de `FORMATS`.
        """
        if format not in FORMATS:
            raise ValueError(
                f"Formato no soportado: {format!r}; usa uno de {', '.join(FORMATS)}"
            )
        graph = self._parser.parse(plan_json)
        if format == "json":
            return json.dumps(self._exporter.to_json(graph), indent=2)
        if format == "dot":
            return self._exporter.to_dot(graph)
        return self._exporter.to_mermaid(graph)
