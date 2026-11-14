import json

from app.core.exporter import GraphExporter
from app.core.graph import Resource, ResourceGraph
from tests.core.helpers import A, B, C, D, make_graph

exporter = GraphExporter()

# A depende de B y de C; D está suelto.
GRAPH = make_graph((A, B), (A, C), isolated=(D,))


def test_json_has_nodes_and_edges():
    result = exporter.to_json(GRAPH)

    assert [node["address"] for node in result["nodes"]] == [A, B, C, D]
    assert result["nodes"][0] == {
        "address": A,
        "type": "null_resource",
        "name": "a",
        "provider": "null",
        "action": "create",
    }
    assert result["edges"] == [
        {"source": A, "target": B},
        {"source": A, "target": C},
    ]


def test_json_is_serializable_and_edges_point_to_nodes():
    result = json.loads(json.dumps(exporter.to_json(GRAPH)))

    addresses = {node["address"] for node in result["nodes"]}
    for edge in result["edges"]:
        assert edge["source"] in addresses
        assert edge["target"] in addresses


def test_dot_output():
    assert exporter.to_dot(GRAPH) == (
        "digraph terraform {\n"
        "    rankdir=LR;\n"
        '    "null_resource.a";\n'
        '    "null_resource.b";\n'
        '    "null_resource.c";\n'
        '    "null_resource.d";\n'
        '    "null_resource.a" -> "null_resource.b";\n'
        '    "null_resource.a" -> "null_resource.c";\n'
        "}\n"
    )


def test_mermaid_output():
    assert exporter.to_mermaid(GRAPH) == (
        "flowchart LR\n"
        '    n0["null_resource.a"]\n'
        '    n1["null_resource.b"]\n'
        '    n2["null_resource.c"]\n'
        '    n3["null_resource.d"]\n'
        "    n0 --> n1\n"
        "    n0 --> n2\n"
    )


def test_empty_graph():
    empty = ResourceGraph()

    assert exporter.to_json(empty) == {"nodes": [], "edges": []}
    assert exporter.to_dot(empty) == "digraph terraform {\n    rankdir=LR;\n}\n"
    assert exporter.to_mermaid(empty) == "flowchart LR\n"


def test_addresses_with_quotes_are_escaped():
    # Con for_each, Terraform usa direcciones como aws_instance.app["web"].
    address = 'aws_instance.app["web"]'
    graph = ResourceGraph()
    graph.add_resource(
        Resource(
            address=address,
            type="aws_instance",
            name="app",
            provider="aws",
            action="create",
        )
    )

    assert '"aws_instance.app[\\"web\\"]";' in exporter.to_dot(graph)
    assert 'n0["aws_instance.app[#quot;web#quot;]"]' in exporter.to_mermaid(graph)
