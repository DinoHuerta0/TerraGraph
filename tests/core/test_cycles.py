from app.core.cycles import CycleDetector
from tests.core.helpers import A, B, C, D, E, make_graph

detector = CycleDetector()


def test_empty_graph_has_no_cycles():
    graph = make_graph()
    assert detector.has_cycle(graph) is False
    assert detector.find_cycles(graph) == []


def test_diamond_is_not_a_cycle():
    # A depende de B y de C, y los dos dependen de D: D se visita dos veces,
    # pero no hay ciclo.
    graph = make_graph((A, B), (A, C), (B, D), (C, D))
    assert detector.has_cycle(graph) is False
    assert detector.find_cycles(graph) == []


def test_simple_cycle():
    graph = make_graph((A, B), (B, A))
    assert detector.has_cycle(graph) is True
    assert detector.find_cycles(graph) == [[A, B]]


def test_long_cycle():
    graph = make_graph((A, B), (B, C), (C, D), (D, A))
    assert detector.find_cycles(graph) == [[A, B, C, D]]


def test_self_reference():
    graph = make_graph((A, A))
    assert detector.find_cycles(graph) == [[A]]


def test_cycle_excludes_resources_that_only_lead_to_it():
    # A depende de C, pero solo B y C forman el ciclo.
    graph = make_graph((A, C), (C, B), (B, C))
    assert detector.find_cycles(graph) == [[B, C]]


def test_multiple_cycles():
    graph = make_graph((A, B), (B, A), (C, D), (D, C), (E, A))
    assert detector.find_cycles(graph) == [[A, B], [C, D]]


def test_cycles_sharing_a_resource():
    graph = make_graph((A, B), (B, A), (A, C), (C, A))
    assert detector.find_cycles(graph) == [[A, B], [A, C]]
