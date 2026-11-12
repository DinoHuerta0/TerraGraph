import json

import pytest

from app.core.parser import PlanParseError, PlanParser

AWS = "registry.terraform.io/hashicorp/aws"


def planned(address, type_, name, mode="managed", index=None):
    resource = {
        "address": address,
        "mode": mode,
        "type": type_,
        "name": name,
        "provider_name": AWS,
    }
    if index is not None:
        resource["index"] = index
    return resource


def change(address, type_, name, actions):
    return {**planned(address, type_, name), "change": {"actions": actions}}


def config(type_, name, expressions=None, mode="managed", **extra):
    return {
        "address": f"{type_}.{name}",
        "mode": mode,
        "type": type_,
        "name": name,
        "expressions": expressions or {},
        **extra,
    }


def refs(*references):
    return {"references": list(references)}


@pytest.fixture
def plan():
    """VPC y subred en el módulo "net"; dos instancias (count = 2) en la raíz."""
    return {
        "format_version": "1.2",
        "planned_values": {
            "root_module": {
                "resources": [
                    planned("aws_instance.app[0]", "aws_instance", "app", index=0),
                    planned("aws_instance.app[1]", "aws_instance", "app", index=1),
                    planned("aws_security_group.web", "aws_security_group", "web"),
                    planned("data.aws_ami.ubuntu", "aws_ami", "ubuntu", mode="data"),
                ],
                "child_modules": [
                    {
                        "address": "module.net",
                        "resources": [
                            planned("module.net.aws_vpc.main", "aws_vpc", "main"),
                            planned(
                                "module.net.aws_subnet.public", "aws_subnet", "public"
                            ),
                        ],
                    }
                ],
            }
        },
        "resource_changes": [
            change("aws_instance.app[0]", "aws_instance", "app", ["create"]),
            change("aws_instance.app[1]", "aws_instance", "app", ["create"]),
            change(
                "aws_security_group.web",
                "aws_security_group",
                "web",
                ["delete", "create"],
            ),
            change("aws_s3_bucket.old", "aws_s3_bucket", "old", ["delete"]),
        ],
        "configuration": {
            "root_module": {
                "resources": [
                    config(
                        "aws_instance",
                        "app",
                        {
                            "ami": refs(
                                "data.aws_ami.ubuntu.id", "data.aws_ami.ubuntu"
                            ),
                            "subnet_id": refs("module.net.subnet_id", "module.net"),
                            "tags": {"constant_value": {"Name": "app"}},
                        },
                        count_expression={"constant_value": 2},
                        depends_on=["aws_security_group.web"],
                    ),
                    config(
                        "aws_security_group",
                        "web",
                        {"vpc_id": refs("module.net.vpc_id", "module.net")},
                    ),
                    config("aws_ami", "ubuntu", mode="data"),
                ],
                "module_calls": {
                    "net": {
                        "source": "./modules/net",
                        "expressions": {"cidr": {"constant_value": "10.0.0.0/16"}},
                        "module": {
                            "outputs": {
                                "vpc_id": {"expression": refs("aws_vpc.main.id")},
                                "subnet_id": {
                                    "expression": refs("aws_subnet.public.id")
                                },
                            },
                            "resources": [
                                config(
                                    "aws_vpc", "main", {"cidr_block": refs("var.cidr")}
                                ),
                                config(
                                    "aws_subnet",
                                    "public",
                                    {"vpc_id": refs("aws_vpc.main.id", "aws_vpc.main")},
                                ),
                            ],
                        },
                    }
                },
            }
        },
    }


@pytest.fixture
def graph(plan):
    return PlanParser().parse(plan)


def test_creates_one_node_per_instance(graph):
    assert graph.addresses() == [
        "aws_instance.app[0]",
        "aws_instance.app[1]",
        "aws_s3_bucket.old",
        "aws_security_group.web",
        "data.aws_ami.ubuntu",
        "module.net.aws_subnet.public",
        "module.net.aws_vpc.main",
    ]


def test_resource_fields(graph):
    resource = graph.get("aws_instance.app[0]")
    assert (resource.type, resource.name, resource.provider) == (
        "aws_instance",
        "app",
        "aws",
    )


@pytest.mark.parametrize(
    "address, action",
    [
        ("aws_instance.app[0]", "create"),
        ("aws_security_group.web", "replace"),
        ("aws_s3_bucket.old", "delete"),
        ("module.net.aws_vpc.main", "no-op"),
    ],
)
def test_actions(graph, address, action):
    assert graph.get(address).action == action


def test_reference_inside_module(graph):
    assert graph.dependencies_of("module.net.aws_subnet.public") == [
        "module.net.aws_vpc.main"
    ]


def test_module_output_resolves_to_resource(graph):
    assert graph.dependencies_of("aws_security_group.web") == [
        "module.net.aws_vpc.main"
    ]


def test_every_count_instance_gets_the_edges(graph):
    expected = [
        "aws_security_group.web",
        "data.aws_ami.ubuntu",
        "module.net.aws_subnet.public",
    ]
    assert graph.dependencies_of("aws_instance.app[0]") == expected
    assert graph.dependencies_of("aws_instance.app[1]") == expected


def test_constant_variable_adds_no_edge(graph):
    assert graph.dependencies_of("module.net.aws_vpc.main") == []


def test_accepts_json_string(plan):
    assert PlanParser().parse(json.dumps(plan)).size() == 7


@pytest.mark.parametrize("content", ["{no es json", "[1, 2]", '{"hola": 1}'])
def test_invalid_plan_raises(content):
    with pytest.raises(PlanParseError):
        PlanParser().parse(content)


@pytest.mark.parametrize(
    "reference, expected",
    [
        ("aws_subnet.public[0].id", "aws_subnet.public"),
        ('aws_instance.app["web"]', "aws_instance.app"),
        ("data.aws_ami.ubuntu.id", "data.aws_ami.ubuntu"),
        ("module.net.vpc_id", "module.net.vpc_id"),
        ("var.cidr", "var.cidr"),
        ("local.tags", None),
        ("each.value", None),
        ("count.index", None),
    ],
)
def test_normalize_address(reference, expected):
    assert PlanParser().normalize_address(reference) == expected
