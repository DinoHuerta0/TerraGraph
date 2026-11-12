"""Convierte el JSON de `terraform show -json plan.tfplan` en un ResourceGraph."""

import json
import re
from typing import Any

from app.core.graph import Resource, ResourceGraph

# Quita los índices de count y for_each: aws_instance.app[0] -> aws_instance.app
_INDEX = re.compile(r"\[[^\]]*\]")

# Prefijos de referencias que no apuntan a un recurso.
_NOT_RESOURCES = {"count", "each", "local", "path", "self", "terraform"}


class PlanParseError(ValueError):
    """El contenido recibido no es un plan de Terraform válido."""


def _strip_index(address: str) -> str:
    return _INDEX.sub("", address)


class PlanParser:
    """Construye el grafo a partir de los recursos del plan y sus referencias."""

    def parse(self, plan_json: str | bytes | dict) -> ResourceGraph:
        plan = self._load(plan_json)
        graph = ResourceGraph()

        # 1. Nodos: un nodo por cada instancia de recurso del plan.
        actions = self._actions(plan)
        root = (plan.get("planned_values") or {}).get("root_module") or {}
        resources = self.extract_resources(root)
        # Los recursos que se van a destruir no aparecen en planned_values.
        known = {r.get("address") for r in resources}
        resources += [
            change
            for change in plan.get("resource_changes") or []
            if change.get("address") not in known
        ]
        try:
            for raw in resources:
                graph.add_resource(self._to_resource(raw, actions))
        except KeyError as error:
            raise PlanParseError(f"Recurso sin el campo {error}") from error

        # 2. Aristas: las referencias están en la configuración, no en los valores.
        config_root = (plan.get("configuration") or {}).get("root_module") or {}
        modules = self._index_modules(config_root)

        # Una dirección de la configuración puede tener varias instancias (count).
        instances: dict[str, list[str]] = {}
        for address in graph.addresses():
            instances.setdefault(_strip_index(address), []).append(address)

        for path, module in modules.items():
            for resource in module["config"].get("resources", []):
                source = self._config_address(path, resource)
                targets: set[str] = set()
                for reference in self.extract_references(resource):
                    targets |= self._resolve(reference, path, modules, set())
                for source_instance in instances.get(source, []):
                    for target in targets:
                        for target_instance in instances.get(target, []):
                            if source_instance != target_instance:
                                graph.add_dependency(source_instance, target_instance)
        return graph

    def extract_resources(self, module: dict) -> list[dict]:
        """Recursos de un módulo de planned_values y de sus módulos hijos."""
        resources = list(module.get("resources", []))
        for child in module.get("child_modules", []):
            resources += self.extract_resources(child)
        return resources

    def extract_references(self, resource: dict) -> list[str]:
        """Referencias de un recurso de la configuración, incluido depends_on."""
        references: list[str] = []
        for key in ("expressions", "count_expression", "for_each_expression"):
            _collect_references(resource.get(key), references)
        references += resource.get("depends_on", [])
        return references

    def normalize_address(self, reference: str) -> str | None:
        """Reduce una referencia a la cosa a la que apunta, o None si no es recurso.

        aws_subnet.public[0].id -> aws_subnet.public
        data.aws_ami.ubuntu.id  -> data.aws_ami.ubuntu
        module.net.vpc_id       -> module.net.vpc_id
        var.subnet_id           -> var.subnet_id
        local.tags, each.value  -> None
        """
        parts = _strip_index(reference).split(".")
        head = parts[0]
        if head in _NOT_RESOURCES:
            return None
        if head == "data":
            return ".".join(parts[:3]) if len(parts) >= 3 else None
        if head == "module":
            return ".".join(parts[:3]) if len(parts) >= 2 else None
        return ".".join(parts[:2]) if len(parts) >= 2 else None

    # --- Auxiliares -----------------------------------------------------------

    def _load(self, plan_json: str | bytes | dict) -> dict:
        if isinstance(plan_json, (str, bytes)):
            try:
                plan_json = json.loads(plan_json)
            except json.JSONDecodeError as error:
                raise PlanParseError(f"JSON inválido: {error}") from error
        if not isinstance(plan_json, dict):
            raise PlanParseError("El plan debe ser un objeto JSON")
        if "planned_values" not in plan_json and "resource_changes" not in plan_json:
            raise PlanParseError("El JSON no parece un plan de Terraform")
        return plan_json

    def _actions(self, plan: dict) -> dict[str, str]:
        """Acción de cada recurso según resource_changes."""
        result = {}
        for change in plan.get("resource_changes") or []:
            actions = (change.get("change") or {}).get("actions") or ["no-op"]
            if set(actions) == {"create", "delete"}:
                result[change["address"]] = "replace"
            else:
                result[change["address"]] = "-".join(actions)
        return result

    def _to_resource(self, raw: dict, actions: dict[str, str]) -> Resource:
        address = raw["address"]
        return Resource(
            address=address,
            type=raw["type"],
            name=raw["name"],
            # registry.terraform.io/hashicorp/aws -> aws
            provider=raw.get("provider_name", "").rsplit("/", 1)[-1],
            action=actions.get(address, "no-op"),
        )

    def _index_modules(self, root: dict) -> dict[str, dict]:
        """Recorre los module_calls de la configuración.

        Devuelve {prefijo: {config, parent, inputs}}, con prefijo "" para la raíz
        y "module.net." para un módulo llamado net.
        """
        modules: dict[str, dict] = {}

        def walk(module: dict, path: str, parent: str | None, inputs: dict) -> None:
            modules[path] = {"config": module, "parent": parent, "inputs": inputs}
            for name, call in module.get("module_calls", {}).items():
                walk(
                    call.get("module", {}),
                    f"{path}module.{name}.",
                    path,
                    call.get("expressions", {}),
                )

        walk(root, "", None, {})
        return modules

    def _config_address(self, path: str, resource: dict) -> str:
        prefix = "data." if resource.get("mode") == "data" else ""
        return f"{path}{prefix}{resource['type']}.{resource['name']}"

    def _resolve(self, reference: str, path: str, modules: dict, seen: set) -> set[str]:
        """Convierte una referencia escrita en el módulo `path` en direcciones
        de recursos de la configuración, siguiendo variables y outputs."""
        address = self.normalize_address(reference)
        if address is None or (path, address) in seen:
            return set()
        seen.add((path, address))
        parts = address.split(".")

        if parts[0] == "var":
            # La variable recibe su valor en el module_call del módulo padre.
            module = modules[path]
            expression = module["inputs"].get(parts[1])
            if module["parent"] is None or expression is None:
                return set()
            return self._resolve_all(expression, module["parent"], modules, seen)

        if parts[0] == "module":
            child = f"{path}module.{parts[1]}."
            if child not in modules:
                return set()
            if len(parts) == 2:
                # depends_on = [module.net]: todos los recursos del módulo.
                return {
                    self._config_address(p, r)
                    for p, m in modules.items()
                    if p.startswith(child)
                    for r in m["config"].get("resources", [])
                }
            output = modules[child]["config"].get("outputs", {}).get(parts[2])
            if output is None:
                return set()
            return self._resolve_all(output.get("expression"), child, modules, seen)

        return {path + address}

    def _resolve_all(
        self, expression: Any, path: str, modules: dict, seen: set
    ) -> set[str]:
        references: list[str] = []
        _collect_references(expression, references)
        result: set[str] = set()
        for reference in references:
            result |= self._resolve(reference, path, modules, seen)
        return result


def _collect_references(node: Any, out: list[str]) -> None:
    """Busca listas "references" a cualquier profundidad de una expresión."""
    if isinstance(node, dict):
        references = node.get("references")
        if isinstance(references, list):
            out += _most_specific(references)
        for key, value in node.items():
            if key not in ("references", "constant_value"):
                _collect_references(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_references(item, out)


def _most_specific(references: list[str]) -> list[str]:
    """Terraform lista module.net.vpc_id y también module.net; se queda la primera.

    Sin esto, usar un output haría depender al recurso de todo el módulo.
    """
    return [
        ref
        for ref in references
        if not any(other.startswith((ref + ".", ref + "[")) for other in references)
    ]
