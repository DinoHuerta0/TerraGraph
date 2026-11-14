import pytest

from app.core.blast_radius import BlastRadiusCalculator
from tests.core.helpers import A, B, C, D, E, make_graph

calculator = BlastRadiusCalculator()

# A y B dependen de C; C depende de D. E está suelto.
#   A ─┐
#      ├─> C ─> D
#   B ─┘
GRAPH = make_graph((A, C), (B, C), (C, D), isolated=(E,))


def test_leaf_has_no_affected():
    # Nadie depende de A: destruirlo no rompe nada.
    assert calculator.affected_by(GRAPH, A) == []
    assert calculator.impact_score(GRAPH, A) == 0.0


def test_root_affects_everything_connected():
    # Todo lo conectado depende de D, directa o transitivamente.
    assert calculator.affected_by(GRAPH, D) == [A, B, C]
    assert calculator.impact_score(GRAPH, D) == 3 / 4


def test_transitive_dependencies():
    # D -> C es directa; A y B dependen de D a través de C.
    chain = make_graph((A, B), (B, C), (C, D))
    assert calculator.affected_by(chain, D) == [A, B, C]
    assert calculator.affected_by(chain, B) == [A]


def test_cycle_does_not_loop_forever():
    graph = make_graph((A, B), (B, C), (C, A))
    assert calculator.affected_by(graph, A) == [B, C]


def test_unknown_resource_raises():
    with pytest.raises(KeyError):
        calculator.affected_by(GRAPH, "null_resource.missing")


def test_single_resource_score_is_zero():
    assert calculator.impact_score(make_graph(isolated=(A,)), A) == 0.0


def test_most_critical_ranking():
    # D afecta a 3, C a 2; A, B y E a 0 (empate: por dirección).
    assert calculator.most_critical(GRAPH) == [(D, 3), (C, 2), (A, 0), (B, 0), (E, 0)]
    assert calculator.most_critical(GRAPH, top=2) == [(D, 3), (C, 2)]


def test_most_critical_empty_graph():
    assert calculator.most_critical(make_graph()) == []


def test_most_critical_negative_top_raises():
    with pytest.raises(ValueError):
        calculator.most_critical(GRAPH, top=-1)
