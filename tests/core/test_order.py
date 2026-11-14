import pytest

from app.core.graph import Resource, ResourceGraph
from app.core.order import CyclicGraphError, OrderPlanner

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


planner = OrderPlanner()


def test_empty_graph():
    graph = make_graph()
    assert planner.parallel_levels(graph) == []
    assert planner.creation_order(graph) == []
    assert planner.destroy_order(graph) == []


def test_linear_chain():
    # A depende de B y B depende de C: primero C, luego B, luego A.
    graph = make_graph((A, B), (B, C))
    assert planner.parallel_levels(graph) == [[C], [B], [A]]
    assert planner.creation_order(graph) == [C, B, A]


def test_diamond():
    # A depende de B y de C, y los dos dependen de D.
    # B y C no dependen entre sí, así que pueden crearse al mismo tiempo.
    graph = make_graph((A, B), (A, C), (B, D), (C, D))
    assert planner.parallel_levels(graph) == [[D], [B, C], [A]]


def test_resource_waits_for_its_slowest_dependency():
    # A depende de C (nivel 0) y de B (nivel 1): A va en el nivel 2, no en el 1.
    graph = make_graph((A, B), (A, C), (B, C))
    assert planner.parallel_levels(graph) == [[C], [B], [A]]


def test_disconnected_components():
    # Dos cadenas independientes y un recurso suelto: sus niveles se juntan.
    graph = make_graph((A, B), (C, D), isolated=(E,))
    assert planner.parallel_levels(graph) == [[B, D, E], [A, C]]


def test_creation_order_respects_every_dependency():
    graph = make_graph((A, B), (A, C), (B, D), (C, D), (E, A))
    order = planner.creation_order(graph)
    assert sorted(order) == graph.addresses()
    for address in graph.addresses():
        for dependency in graph.dependencies_of(address):
            assert order.index(dependency) < order.index(address)


def test_destroy_order_is_the_reverse():
    graph = make_graph((A, B), (A, C), (B, D), (C, D))
    creation = planner.creation_order(graph)
    assert planner.destroy_order(graph) == list(reversed(creation))
    assert planner.destroy_order(graph)[0] == A
    assert planner.destroy_order(graph)[-1] == D


@pytest.mark.parametrize(
    "method", ["parallel_levels", "creation_order", "destroy_order"]
)
def test_cycle_raises(method):
    graph = make_graph((A, B), (B, C), (C, A), (D, A))
    with pytest.raises(CyclicGraphError) as error:
        getattr(planner, method)(graph)
    assert error.value.cycles == [[A, B, C]]
    assert f"{A} -> {B} -> {C} -> {A}" in str(error.value)


def test_self_reference_raises():
    graph = make_graph((A, A))
    with pytest.raises(CyclicGraphError):
        planner.creation_order(graph)
