"""Utilidades compartidas por las pruebas de `app.core`."""

from app.core.graph import Resource, ResourceGraph

A = "null_resource.a"
B = "null_resource.b"
C = "null_resource.c"
D = "null_resource.d"
E = "null_resource.e"


def make_graph(
    *edges: tuple[str, str], isolated: tuple[str, ...] = ()
) -> ResourceGraph:
    """Crea un grafo a partir de aristas (origen, destino) = "origen depende de destino".

    `isolated` agrega recursos sin aristas.
    """
    graph = ResourceGraph()
    addresses = {address for edge in edges for address in edge} | set(isolated)
    for address in sorted(addresses):
        type_, name = address.split(".")
        graph.add_resource(
            Resource(
                address=address, type=type_, name=name, provider="null", action="create"
            )
        )
    for source, target in edges:
        graph.add_dependency(source, target)
    return graph
