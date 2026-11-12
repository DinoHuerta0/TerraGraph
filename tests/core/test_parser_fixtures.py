"""Pruebas de PlanParser con planes completos guardados en tests/fixtures/."""

from pathlib import Path

import pytest

from app.core.parser import PlanParseError, PlanParser

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load(name):
    """Parsea el fixture desde texto, igual que llegará por la API."""
    return PlanParser().parse((FIXTURES / name).read_text(encoding="utf-8"))


def edges(graph):
    """Todas las aristas del grafo como pares (origen, destino)."""
    return {
        (source, target)
        for source in graph.addresses()
        for target in graph.dependencies_of(source)
    }


# --- minimal.json -------------------------------------------------------------


def test_minimal_plan():
    graph = load("minimal.json")
    assert graph.addresses() == ["aws_s3_bucket.logs"]
    assert graph.get("aws_s3_bucket.logs").action == "create"
    assert edges(graph) == set()


# --- references.json ----------------------------------------------------------

SUBNET_A = 'aws_subnet.private["a"]'
SUBNET_B = 'aws_subnet.private["b"]'


@pytest.fixture(scope="module")
def references():
    return load("references.json")


def test_references_nodes(references):
    assert references.addresses() == [
        "aws_instance.app[0]",
        "aws_instance.app[1]",
        "aws_internet_gateway.gw",
        "aws_security_group.web",
        SUBNET_A,
        SUBNET_B,
        "aws_vpc.main",
        "data.aws_ami.ubuntu",
    ]


def test_data_source_read_during_plan_is_a_node(references):
    # Terraform lo deja solo en prior_state, no en planned_values.
    assert references.get("data.aws_ami.ubuntu").action == "no-op"


def test_references_edges(references):
    app = {
        "aws_internet_gateway.gw",
        "aws_security_group.web",
        SUBNET_A,
        SUBNET_B,
        "data.aws_ami.ubuntu",
    }
    assert edges(references) == {
        ("aws_internet_gateway.gw", "aws_vpc.main"),
        ("aws_security_group.web", "aws_vpc.main"),
        (SUBNET_A, "aws_vpc.main"),
        (SUBNET_B, "aws_vpc.main"),
        *(("aws_instance.app[0]", target) for target in app),
        *(("aws_instance.app[1]", target) for target in app),
    }


def test_depends_on_creates_edge(references):
    assert "aws_internet_gateway.gw" in references.dependencies_of(
        "aws_instance.app[0]"
    )


def test_for_each_and_count_variables_add_no_edge(references):
    # for_each = var.subnets, each.key, each.value y count.index no son recursos.
    assert references.dependencies_of(SUBNET_A) == ["aws_vpc.main"]


@pytest.mark.parametrize(
    "address, action",
    [
        ("aws_vpc.main", "no-op"),
        ("aws_security_group.web", "update"),
        (SUBNET_A, "create"),
    ],
)
def test_references_actions(references, address, action):
    assert references.get(address).action == action


# --- nested_modules.json ------------------------------------------------------

VPC = "module.network.aws_vpc.this"
SUBNET = "module.network.module.subnets.aws_subnet.this"


@pytest.fixture(scope="module")
def nested():
    return load("nested_modules.json")


def test_nested_modules_nodes(nested):
    assert nested.addresses() == [
        "aws_instance.app",
        "aws_route53_record.app",
        VPC,
        SUBNET,
    ]


def test_variable_passed_to_child_module(nested):
    assert nested.dependencies_of(SUBNET) == [VPC]


def test_output_through_two_modules(nested):
    assert nested.dependencies_of("aws_instance.app") == [SUBNET]


def test_depends_on_whole_module_includes_nested_modules(nested):
    assert nested.dependencies_of("aws_route53_record.app") == [VPC, SUBNET]


def test_constant_and_root_variables_add_no_edge(nested):
    assert nested.dependencies_of(VPC) == []


# --- locals.json --------------------------------------------------------------
# El JSON del plan no incluye los bloques locals (ver "Limitaciones conocidas").


@pytest.fixture(scope="module")
def with_locals():
    return load("locals.json")


def test_locals_do_not_drop_nodes(with_locals):
    assert with_locals.addresses() == [
        "aws_eip.app",
        "aws_instance.mixed",
        "aws_instance.via_local",
        "aws_instance.with_depends_on",
        "aws_subnet.main",
        "aws_vpc.main",
        "module.app.aws_network_interface.this",
    ]


def test_locals_add_no_extra_edges(with_locals):
    assert edges(with_locals) == {
        ("aws_subnet.main", "aws_vpc.main"),
        ("aws_instance.mixed", "aws_subnet.main"),
        ("aws_instance.with_depends_on", "aws_subnet.main"),
    }


def test_constant_local_adds_no_edge(with_locals):
    assert with_locals.dependencies_of("aws_vpc.main") == []


def test_local_pointing_to_resource_loses_the_edge(with_locals):
    # Limitación conocida: local.subnet_id = aws_subnet.main.id no se puede seguir.
    # Si algún día el parser resuelve locals, esta prueba debe cambiar.
    assert with_locals.dependencies_of("aws_instance.via_local") == []


def test_local_does_not_hide_direct_reference(with_locals):
    assert with_locals.dependencies_of("aws_instance.mixed") == ["aws_subnet.main"]


def test_depends_on_recovers_edge_lost_in_local(with_locals):
    assert with_locals.dependencies_of("aws_instance.with_depends_on") == [
        "aws_subnet.main"
    ]


def test_local_passed_to_module_adds_no_edge(with_locals):
    assert with_locals.dependencies_of("module.app.aws_network_interface.this") == []


def test_module_output_from_local_adds_no_edge(with_locals):
    assert with_locals.dependencies_of("aws_eip.app") == []


# --- Entradas que no son planes -----------------------------------------------


def test_state_file_is_rejected():
    # terraform show -json sobre un estado trae "values" y no "planned_values".
    with pytest.raises(PlanParseError):
        load("state.json")
