from enum import Enum

from app.core.graph import ResourceGraph


class _Color(Enum):
    WHITE = 0  # sin visitar
    GRAY = 1  # en el camino actual del DFS
    BLACK = 2  # terminado: él y todo lo que alcanza ya se revisaron


class CycleDetector:
    """Encuentra dependencias circulares con un DFS de tres colores."""

    def has_cycle(self, graph: ResourceGraph) -> bool:
        return bool(self.find_cycles(graph))

    def find_cycles(self, graph: ResourceGraph) -> list[list[str]]:
        """Devuelve cada ciclo como lista de direcciones, empezando por la menor.

        [A, B, C] significa A -> B -> C -> A.
        """
        color = {address: _Color.WHITE for address in graph.addresses()}
        path: list[str] = []
        cycles: list[list[str]] = []

        def visit(address: str) -> None:
            color[address] = _Color.GRAY
            path.append(address)
            for dependency in graph.dependencies_of(address):
                if color[dependency] is _Color.GRAY:
                    # Arista hacia atrás: el ciclo es el tramo del camino
                    # que va de `dependency` hasta `address`.
                    start = path.index(dependency)
                    cycles.append(_rotate(path[start:]))
                elif color[dependency] is _Color.WHITE:
                    visit(dependency)
            path.pop()
            color[address] = _Color.BLACK

        for address in graph.addresses():
            if color[address] is _Color.WHITE:
                visit(address)

        return sorted(cycles)


def _rotate(cycle: list[str]) -> list[str]:
    """Rota el ciclo para que empiece en su dirección menor.

    [B, C, A] y [A, B, C] son el mismo ciclo; así siempre se reporta igual.
    """
    start = cycle.index(min(cycle))
    return cycle[start:] + cycle[:start]
