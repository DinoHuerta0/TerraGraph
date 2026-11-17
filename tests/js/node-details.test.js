// Pruebas de los detalles de un recurso con Cytoscape en modo headless (sin
// navegador), usando la misma copia de app/static/vendor/ que carga la página.

"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");

const cytoscape = require("../../app/static/vendor/cytoscape.min.js");
const { nodeDetails } = require("../../app/static/node-details.js");

function resource(address, type, name, action) {
  return { data: { id: address, type, name, provider: "aws", action } };
}

// subnet y bucket dependen de vpc; instance depende de subnet y de bucket.
function makeGraph() {
  return cytoscape({
    headless: true,
    elements: [
      resource("aws_vpc.main", "aws_vpc", "main", "create"),
      resource("aws_subnet.public", "aws_subnet", "public", "update"),
      resource("aws_s3_bucket.logs", "aws_s3_bucket", "logs", "no-op"),
      resource("aws_instance.web", "aws_instance", "web", "delete"),
      { data: { source: "aws_subnet.public", target: "aws_vpc.main" } },
      { data: { source: "aws_s3_bucket.logs", target: "aws_vpc.main" } },
      { data: { source: "aws_instance.web", target: "aws_subnet.public" } },
      { data: { source: "aws_instance.web", target: "aws_s3_bucket.logs" } },
    ],
  });
}

test("nodeDetails devuelve los datos del recurso", () => {
  const details = nodeDetails(makeGraph(), "aws_subnet.public");
  assert.equal(details.address, "aws_subnet.public");
  assert.equal(details.type, "aws_subnet");
  assert.equal(details.name, "public");
  assert.equal(details.provider, "aws");
  assert.equal(details.action, "update");
});

test("nodeDetails separa dependencias y dependientes directos", () => {
  const details = nodeDetails(makeGraph(), "aws_subnet.public");
  assert.deepEqual(details.dependsOn, ["aws_vpc.main"]);
  assert.deepEqual(details.dependents, ["aws_instance.web"]);
});

test("nodeDetails solo incluye relaciones directas, ordenadas", () => {
  // instance depende de vpc a través de subnet, pero no directamente.
  const details = nodeDetails(makeGraph(), "aws_instance.web");
  assert.deepEqual(details.dependsOn, ["aws_s3_bucket.logs", "aws_subnet.public"]);
  assert.deepEqual(details.dependents, []);
});

test("nodeDetails de un recurso raíz lista a todos los que dependen de él", () => {
  const details = nodeDetails(makeGraph(), "aws_vpc.main");
  assert.deepEqual(details.dependsOn, []);
  assert.deepEqual(details.dependents, ["aws_s3_bucket.logs", "aws_subnet.public"]);
});

test("nodeDetails con un ciclo incluye el recurso en las dos listas del otro", () => {
  const cy = cytoscape({
    headless: true,
    elements: [
      resource("a.one", "a", "one", "create"),
      resource("b.two", "b", "two", "create"),
      { data: { source: "a.one", target: "b.two" } },
      { data: { source: "b.two", target: "a.one" } },
    ],
  });
  const details = nodeDetails(cy, "a.one");
  assert.deepEqual(details.dependsOn, ["b.two"]);
  assert.deepEqual(details.dependents, ["b.two"]);
});

test("nodeDetails de un recurso inexistente devuelve null", () => {
  assert.equal(nodeDetails(makeGraph(), "aws_vpc.missing"), null);
});
