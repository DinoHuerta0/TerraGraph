from collections import deque

from app.core.graph import ResourceGraph


class BlastRadiusCalculator:
    """Calcula qué recursos se rompen si se destruye uno (BFS sobre el grafo invertido)."""

    def affected_by(self, graph: ResourceGraph, address: str) -> list[str]:
        """Todos los recursos que dependen de `address`, directa o transitivamente.

        No incluye a `address`. Lanza `KeyError` si el recurso no existe.
        """
        graph.get(address)
        return self._affected(graph.reversed(), address)

    def impact_score(self, graph: ResourceGraph, address: str) -> float:
        """Fracción de los demás recursos que se rompen: 0.0 (ninguno) a 1.0 (todos)."""
        others = graph.size() - 1
        affected = self.affected_by(graph, address)
        return len(affected) / others if others else 0.0

    def most_critical(
        self, graph: ResourceGraph, top: int = 5
    ) -> list[tuple[str, int]]:
        """Los `top` recursos que más afectan al destruirse, como (dirección, afectados).

        Se ordenan de más a menos afectados; los empates, por dirección.
        """
        if top < 0:
            raise ValueError(f"top no puede ser negativo: {top}")

        # Se invierte una sola vez y se reutiliza para todos los recursos.
        inverted = graph.reversed()
        ranking = [
            (address, len(self._affected(inverted, address)))
            for address in graph.addresses()
        ]
        ranking.sort(key=lambda item: (-item[1], item[0]))
        return ranking[:top]

    @staticmethod
    def _affected(inverted: ResourceGraph, address: str) -> list[str]:
        # En el grafo invertido, A -> B significa "B depende de A",
        # así que seguir las aristas desde `address` lleva a todo lo que se rompe.
        visited = {address}
        queue = deque([address])
        while queue:
            current = queue.popleft()
            for dependent in inverted.dependencies_of(current):
                if dependent not in visited:
                    visited.add(dependent)
                    queue.append(dependent)
        visited.discard(address)
        return sorted(visited)
