"""Pruebas de GraphAnalyzer con planes completos, como llegarán por la API."""

import json
from pathlib import Path

import pytest

from app.core.analyzer import AnalysisResult, GraphAnalyzer
from app.core.parser import PlanParseError

FIXTURES = Path(__file__).parent.parent / "fixtures"

analyzer = GraphAnalyzer()

VPC = "aws_vpc.main"
SUBNET = "aws_subnet.public"
INSTANCE = "aws_instance.app"


def plan(*resources: tuple[str, list[str]]) -> dict:
    """Plan mínimo: cada recurso es (dirección, recursos de los que depende)."""
    return {
        "resource_changes": [
            {
                "address": address,
                "type": address.split(".")[0],
                "name": address.split(".")[1],
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {"actions": ["create"]},
            }
            for address, _ in resources
        ],
        "configuration": {
            "root_module": {
                "resources": [
                    {
                        "address": address,
                        "mode": "managed",
                        "type": address.split(".")[0],
                        "name": address.split(".")[1],
                        "depends_on": depends_on,
                    }
                    for address, depends_on in resources
                ]
            }
        },
    }


# La instancia depende de la subred y la subred de la VPC.
CHAIN = plan((VPC, []), (SUBNET, [VPC]), (INSTANCE, [SUBNET]))


# --- analyze ------------------------------------------------------------------


def test_analyze_chain():
    result = analyzer.analyze(CHAIN)

    assert isinstance(result, AnalysisResult)
    assert [node["address"] for node in result.graph["nodes"]] == [
        INSTANCE,
        SUBNET,
        VPC,
    ]
    assert result.graph["edges"] == [
        {"source": INSTANCE, "target": SUBNET},
        {"source": SUBNET, "target": VPC},
    ]
    assert result.creation_order == [VPC, SUBNET, INSTANCE]
    assert result.parallel_levels == [[VPC], [SUBNET], [INSTANCE]]
    assert result.cycles == []


def test_analyze_accepts_text():
    # La API guarda y entrega el plan como texto.
    text = (FIXTURES / "minimal.json").read_text(encoding="utf-8")

    result = analyzer.analyze(text)

    assert result.creation_order == ["aws_s3_bucket.logs"]
    assert result.parallel_levels == [["aws_s3_bucket.logs"]]


def test_analyze_with_cycle_reports_it_without_order():
    cyclic = plan((VPC, [SUBNET]), (SUBNET, [VPC]))

    result = analyzer.analyze(cyclic)

    assert result.cycles == [[SUBNET, VPC]]
    assert result.creation_order == []
    assert result.parallel_levels == []
    assert len(result.graph["nodes"]) == 2


def test_analyze_invalid_plan():
    with pytest.raises(PlanParseError):
        analyzer.analyze("esto no es JSON")


# --- blast_radius -------------------------------------------------------------


def test_blast_radius():
    assert analyzer.blast_radius(CHAIN, VPC) == [INSTANCE, SUBNET]
    assert analyzer.blast_radius(CHAIN, INSTANCE) == []


def test_blast_radius_unknown_resource():
    with pytest.raises(KeyError):
        analyzer.blast_radius(CHAIN, "aws_s3_bucket.no_existe")


# --- export -------------------------------------------------------------------


def test_export_json_is_valid_text():
    exported = json.loads(analyzer.export(CHAIN, "json"))

    assert exported == analyzer.analyze(CHAIN).graph


@pytest.mark.parametrize(
    ("format", "start"), [("json", "{"), ("dot", "digraph"), ("mermaid", "flowchart")]
)
def test_export_formats(format, start):
    exported = analyzer.export(CHAIN, format)

    assert exported.startswith(start)
    assert VPC in exported


def test_export_unknown_format():
    with pytest.raises(ValueError, match="Formato no soportado"):
        analyzer.export(CHAIN, "png")
