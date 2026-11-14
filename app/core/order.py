from app.core.cycles import CycleDetector
from app.core.graph import ResourceGraph


class CyclicGraphError(ValueError):
    """El grafo tiene dependencias circulares, así que no existe un orden válido."""

    def __init__(self, cycles: list[list[str]]) -> None:
        self.cycles = cycles
        listed = "; ".join(" -> ".join([*cycle, cycle[0]]) for cycle in cycles)
        super().__init__(f"El grafo tiene ciclos: {listed}")


class OrderPlanner:
    """Calcula en qué orden se crean y se destruyen los recursos (algoritmo de Kahn)."""

    def __init__(self, detector: CycleDetector | None = None) -> None:
        self._detector = detector or CycleDetector()

    def parallel_levels(self, graph: ResourceGraph) -> list[list[str]]:
        """Agrupa los recursos en niveles que pueden crearse en paralelo.

        El nivel 0 son los recursos sin dependencias; cada nivel siguiente
        solo depende de recursos de niveles anteriores.
        """
        cycles = self._detector.find_cycles(graph)
        if cycles:
            raise CyclicGraphError(cycles)

        # Cuántas dependencias le faltan a cada recurso para poder crearse.
        pending = {
            address: len(graph.dependencies_of(address))
            for address in graph.addresses()
        }
        level = [address for address, count in pending.items() if count == 0]
        levels: list[list[str]] = []

        while level:
            levels.append(level)
            next_level = []
            for address in level:
                # Este recurso ya existe: sus dependientes tienen una dependencia menos.
                for dependent in graph.dependents_of(address):
                    pending[dependent] -= 1
                    if pending[dependent] == 0:
                        next_level.append(dependent)
            level = sorted(next_level)

        return levels

    def creation_order(self, graph: ResourceGraph) -> list[str]:
        """Un orden válido para crear todo: cada recurso va después de sus dependencias."""
        return [address for level in self.parallel_levels(graph) for address in level]

    def destroy_order(self, graph: ResourceGraph) -> list[str]:
        """El inverso del orden de creación: primero se borra lo que depende de otros."""
        return list(reversed(self.creation_order(graph)))
