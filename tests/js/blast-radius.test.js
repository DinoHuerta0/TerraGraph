// Pruebas del radio de impacto con Cytoscape en modo headless (sin navegador),
// usando la misma copia de app/static/vendor/ que carga la página.

"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");

const cytoscape = require("../../app/static/vendor/cytoscape.min.js");
const {
  blastRadiusUrl,
  blastRadiusMessage,
  highlightBlastRadius,
  clearBlastRadius,
} = require("../../app/static/blast-radius.js");

// subnet y bucket dependen de vpc; instance depende de subnet.
// bucket no depende de nada que se rompa al destruir subnet.
function makeGraph() {
  return cytoscape({
    headless: true,
    elements: [
      { data: { id: "aws_vpc.main" } },
      { data: { id: "aws_subnet.public" } },
      { data: { id: "aws_instance.web" } },
      { data: { id: "aws_s3_bucket.logs" } },
      { data: { id: "subnet-vpc", source: "aws_subnet.public", target: "aws_vpc.main" } },
      { data: { id: "instance-subnet", source: "aws_instance.web", target: "aws_subnet.public" } },
      { data: { id: "bucket-vpc", source: "aws_s3_bucket.logs", target: "aws_vpc.main" } },
    ],
  });
}

function idsWithClass(cy, className) {
  return cy
    .elements(`.${className}`)
    .map((element) => element.id())
    .sort();
}

test("blastRadiusUrl codifica el id y la dirección", () => {
  assert.equal(
    blastRadiusUrl("abc-123", 'aws_subnet.private["a"]'),
    "/api/analyses/abc-123/blast-radius?address=aws_subnet.private%5B%22a%22%5D",
  );
});

test("blastRadiusMessage muestra el número de afectados", () => {
  assert.equal(
    blastRadiusMessage("aws_instance.web", []),
    "Si destruyes aws_instance.web, no se rompe ningún otro recurso.",
  );
  assert.equal(
    blastRadiusMessage("aws_subnet.public", ["aws_instance.web"]),
    "Si destruyes aws_subnet.public, se rompe 1 recurso.",
  );
  assert.equal(
    blastRadiusMessage("aws_vpc.main", ["a", "b", "c"]),
    "Si destruyes aws_vpc.main, se rompen 3 recursos.",
  );
});

test("resalta el recurso, sus afectados y las aristas entre ellos", () => {
  const cy = makeGraph();
  highlightBlastRadius(cy, "aws_subnet.public", ["aws_instance.web"]);

  assert.deepEqual(idsWithClass(cy, "blast-source"), ["aws_subnet.public"]);
  assert.deepEqual(idsWithClass(cy, "affected"), ["aws_instance.web", "instance-subnet"]);
});

test("atenúa todo lo que no se rompe", () => {
  const cy = makeGraph();
  highlightBlastRadius(cy, "aws_subnet.public", ["aws_instance.web"]);

  assert.deepEqual(idsWithClass(cy, "dimmed"), [
    "aws_s3_bucket.logs",
    "aws_vpc.main",
    "bucket-vpc",
    "subnet-vpc",
  ]);
});

test("un recurso sin afectados solo se marca a sí mismo", () => {
  const cy = makeGraph();
  highlightBlastRadius(cy, "aws_instance.web", []);

  assert.deepEqual(idsWithClass(cy, "blast-source"), ["aws_instance.web"]);
  assert.deepEqual(idsWithClass(cy, "affected"), []);
  assert.equal(cy.elements(".dimmed").length, cy.elements().length - 1);
});

test("elegir otro recurso reemplaza el resaltado anterior", () => {
  const cy = makeGraph();
  highlightBlastRadius(cy, "aws_subnet.public", ["aws_instance.web"]);
  highlightBlastRadius(cy, "aws_vpc.main", [
    "aws_instance.web",
    "aws_s3_bucket.logs",
    "aws_subnet.public",
  ]);

  assert.deepEqual(idsWithClass(cy, "blast-source"), ["aws_vpc.main"]);
  assert.deepEqual(idsWithClass(cy, "dimmed"), []);
  assert.equal(cy.elements(".affected").length, cy.elements().length - 1);
});

test("clearBlastRadius quita el resaltado", () => {
  const cy = makeGraph();
  highlightBlastRadius(cy, "aws_subnet.public", ["aws_instance.web"]);
  clearBlastRadius(cy);

  for (const className of ["blast-source", "affected", "dimmed"]) {
    assert.equal(cy.elements(`.${className}`).length, 0);
  }
});
