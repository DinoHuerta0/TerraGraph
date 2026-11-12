from dataclasses import dataclass


@dataclass(frozen=True)
class Resource:
    address: str  # "aws_instance.app" o "module.net.aws_vpc.main"
    type: str  # "aws_instance"
    name: str  # "app"
    provider: str  # "aws"
    action: str  # "create", "update", "delete", "no-op"…


class ResourceGraph:
    """Grafo dirigido de recursos. Una arista A -> B significa "A depende de B"."""

    def __init__(self) -> None:
        self._nodes: dict[str, Resource] = {}  # address -> Resource
        self._edges: dict[str, set[str]] = {}  # address -> addresses de las que depende

    def add_resource(self, resource: Resource) -> None:
        if resource.address in self._nodes:
            raise ValueError(f"El recurso ya existe: {resource.address}")
        self._nodes[resource.address] = resource
        self._edges[resource.address] = set()

    def add_dependency(self, source: str, target: str) -> None:
        self._require(source)
        self._require(target)
        self._edges[source].add(target)

    def get(self, address: str) -> Resource:
        self._require(address)
        return self._nodes[address]

    def dependencies_of(self, address: str) -> list[str]:
        self._require(address)
        return sorted(self._edges[address])

    def dependents_of(self, address: str) -> list[str]:
        self._require(address)
        return sorted(
            source for source, targets in self._edges.items() if address in targets
        )

    def addresses(self) -> list[str]:
        return sorted(self._nodes)

    def reversed(self) -> "ResourceGraph":
        graph = ResourceGraph()
        for resource in self._nodes.values():
            graph.add_resource(resource)
        for source, targets in self._edges.items():
            for target in targets:
                graph.add_dependency(target, source)
        return graph

    def size(self) -> int:
        return len(self._nodes)

    def _require(self, address: str) -> None:
        if address not in self._nodes:
            raise KeyError(address)
