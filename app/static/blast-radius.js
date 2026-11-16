// Radio de impacto en el grafo: al hacer clic en un recurso se resaltan los que
// se rompen si se destruye y el resto se atenúa. La lista de afectados la
// calcula la API (BlastRadiusCalculator); aquí solo se pinta.
//
// Las funciones reciben la instancia de Cytoscape (`cy`) para poder probarlas en
// Node con Cytoscape sin navegador (tests/js/blast-radius.test.js).

"use strict";

function blastRadiusUrl(analysisId, address) {
  // URLSearchParams codifica los caracteres de direcciones como
  // aws_subnet.private["a"] o module.red.aws_vpc.main[0].
  const query = new URLSearchParams({ address });
  return `/api/analyses/${encodeURIComponent(analysisId)}/blast-radius?${query}`;
}

function blastRadiusMessage(address, affected) {
  const count = affected.length;
  if (count === 0) {
    return `Si destruyes ${address}, no se rompe ningún otro recurso.`;
  }
  if (count === 1) {
    return `Si destruyes ${address}, se rompe 1 recurso.`;
  }
  return `Si destruyes ${address}, se rompen ${count} recursos.`;
}

// Marca el recurso elegido (blast-source), los afectados y las aristas entre
// ellos (affected), y atenúa todo lo demás (dimmed).
function highlightBlastRadius(cy, address, affected) {
  clearBlastRadius(cy);
  const affectedSet = new Set(affected);
  const source = cy.getElementById(address);
  const affectedNodes = cy.nodes().filter((node) => affectedSet.has(node.id()));
  const group = source.union(affectedNodes);
  // Aristas con los dos extremos en el grupo: el camino por el que se propaga
  // la falla, del recurso elegido hacia los que dependen de él.
  const paths = group.edgesWith(group);

  source.addClass("blast-source");
  affectedNodes.addClass("affected");
  paths.addClass("affected");
  cy.elements().not(group).not(paths).addClass("dimmed");
}

function clearBlastRadius(cy) {
  cy.elements().removeClass("blast-source affected dimmed");
}

// En el navegador quedan como globales para app.js; en Node se exportan para
// las pruebas de tests/js/.
if (typeof module !== "undefined") {
  module.exports = {
    blastRadiusUrl,
    blastRadiusMessage,
    highlightBlastRadius,
    clearBlastRadius,
  };
}
