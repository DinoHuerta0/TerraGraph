// Detalles de un recurso del grafo: sus datos y sus relaciones directas. Sirve
// para revisar un plan grande sin tener que seguir las flechas a ojo.
//
// Igual que blast-radius.js, recibe la instancia de Cytoscape (`cy`) para poder
// probarlo en Node sin navegador (tests/js/node-details.test.js). El panel lo
// llena app.js.

"use strict";

// Devuelve los datos del recurso y sus relaciones, o null si no está en el grafo.
// Una arista A -> B significa "A depende de B", así que:
//   - las aristas que salen del nodo llegan a sus dependencias (dependsOn);
//   - las que entran vienen de los recursos que dependen de él (dependents).
function nodeDetails(cy, address) {
  const node = cy.getElementById(address);
  if (node.empty()) {
    return null;
  }
  return {
    address,
    type: node.data("type"),
    name: node.data("name"),
    provider: node.data("provider"),
    action: node.data("action"),
    dependsOn: sortedIds(node.outgoers("node")),
    dependents: sortedIds(node.incomers("node")),
  };
}

// Ordenadas alfabéticamente para que la lista sea fácil de recorrer.
function sortedIds(nodes) {
  return nodes.map((node) => node.id()).sort();
}

// En el navegador queda como global para app.js; en Node se exporta para las
// pruebas de tests/js/.
if (typeof module !== "undefined") {
  module.exports = { nodeDetails };
}
