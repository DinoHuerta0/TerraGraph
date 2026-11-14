from dataclasses import asdict

from app.core.graph import ResourceGraph


class GraphExporter:
    """Convierte el grafo a JSON, DOT (Graphviz) y Mermaid.

    En los tres formatos, una arista A -> B significa "A depende de B", igual que en
    `ResourceGraph`. Los nodos y las aristas salen ordenados para que la salida sea
    siempre la misma con el mismo grafo.
    """

    def to_json(self, graph: ResourceGraph) -> dict:
        """Diccionario con `nodes` y `edges`, listo para `json.dumps`."""
        return {
            "nodes": [asdict(graph.get(address)) for address in graph.addresses()],
            "edges": [
                {"source": source, "target": target}
                for source, target in self._edges(graph)
            ],
        }

    def to_dot(self, graph: ResourceGraph) -> str:
        """Texto DOT; se dibuja con Graphviz, por ejemplo `dot -Tpng grafo.dot`."""
        lines = ["digraph terraform {", "    rankdir=LR;"]
        for address in graph.addresses():
            lines.append(f"    {_dot_quote(address)};")
        for source, target in self._edges(graph):
            lines.append(f"    {_dot_quote(source)} -> {_dot_quote(target)};")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def to_mermaid(self, graph: ResourceGraph) -> str:
        """Texto Mermaid (`flowchart`); GitHub lo dibuja dentro de un bloque ```mermaid."""
        # Mermaid no acepta corchetes ni comillas en los ids, así que cada nodo
        # recibe un id corto (n0, n1…) y la dirección va como etiqueta.
        ids = {address: f"n{i}" for i, address in enumerate(graph.addresses())}
        lines = ["flowchart LR"]
        for address, node_id in ids.items():
            lines.append(f'    {node_id}["{_mermaid_label(address)}"]')
        for source, target in self._edges(graph):
            lines.append(f"    {ids[source]} --> {ids[target]}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _edges(graph: ResourceGraph) -> list[tuple[str, str]]:
        return [
            (source, target)
            for source in graph.addresses()
            for target in graph.dependencies_of(source)
        ]


def _dot_quote(text: str) -> str:
    # En DOT, un id entre comillas puede tener cualquier carácter
    # si se escapan la barra invertida y las comillas.
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _mermaid_label(text: str) -> str:
    # Dentro de una etiqueta de Mermaid, las comillas se escriben como entidad.
    return text.replace('"', "#quot;")
