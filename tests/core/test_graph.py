import pytest

from app.core.graph import Resource, ResourceGraph

VPC = "aws_vpc.main"
SUBNET = "aws_subnet.public"
SG = "aws_security_group.web"
INSTANCE = "aws_instance.app"


def make_resource(address: str) -> Resource:
    type_, name = address.split(".")
    return Resource(
        address=address, type=type_, name=name, provider="aws", action="create"
    )


@pytest.fixture
def graph() -> ResourceGraph:
    g = ResourceGraph()
    for address in [VPC, SUBNET, SG, INSTANCE]:
        g.add_resource(make_resource(address))
    g.add_dependency(SUBNET, VPC)
    g.add_dependency(SG, VPC)
    g.add_dependency(INSTANCE, SUBNET)
    g.add_dependency(INSTANCE, SG)
    return g


def test_size_counts_resources(graph):
    assert graph.size() == 4


def test_get_returns_resource(graph):
    assert graph.get(VPC).type == "aws_vpc"


def test_duplicate_resource_raises(graph):
    with pytest.raises(ValueError):
        graph.add_resource(make_resource(VPC))


def test_dependencies_of(graph):
    assert graph.dependencies_of(INSTANCE) == [SG, SUBNET]


def test_dependents_of(graph):
    assert graph.dependents_of(VPC) == [SG, SUBNET]


def test_leaf_has_no_dependents(graph):
    assert graph.dependents_of(INSTANCE) == []


def test_duplicate_dependency_is_ignored(graph):
    graph.add_dependency(INSTANCE, SG)
    assert graph.dependencies_of(INSTANCE) == [SG, SUBNET]


def test_reversed_swaps_edges(graph):
    rev = graph.reversed()
    assert rev.size() == graph.size()
    assert rev.dependencies_of(VPC) == [SG, SUBNET]
    assert rev.dependencies_of(INSTANCE) == []


def test_reversed_does_not_modify_original(graph):
    graph.reversed()
    assert graph.dependencies_of(INSTANCE) == [SG, SUBNET]


def test_address(graph):
    assert graph.addresses() == [INSTANCE, SG, SUBNET, VPC]


@pytest.mark.parametrize("method", ["get", "dependencies_of", "dependents_of"])
def test_unknown_resource_raises(graph, method):
    with pytest.raises(KeyError):
        getattr(graph, method)("aws_s3_bucket.missing")


def test_dependency_with_unknown_resource_raises(graph):
    with pytest.raises(KeyError):
        graph.add_dependency(INSTANCE, "aws_s3_bucket.missing")
