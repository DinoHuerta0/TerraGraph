// Pruebas de HistoryStore con el runner que trae Node (node --test), sin
// instalar nada. Corren en CI en el job test-js.

"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");

const { HistoryStore, HISTORY_LIMIT } = require("../../app/static/history.js");

// Imita la parte de localStorage que usa HistoryStore.
class FakeStorage {
  constructor() {
    this.items = new Map();
  }

  getItem(key) {
    return this.items.has(key) ? this.items.get(key) : null;
  }

  setItem(key, value) {
    this.items.set(key, String(value));
  }
}

test("empieza vacío", () => {
  assert.deepEqual(new HistoryStore(new FakeStorage()).list(), []);
});

test("add guarda id, nombre y fecha, del más reciente al más antiguo", () => {
  const store = new HistoryStore(new FakeStorage());
  store.add("a", "red", "2026-11-16T10:00:00Z");
  store.add("b", "cómputo", "2026-11-16T11:00:00Z");

  assert.deepEqual(store.list(), [
    { id: "b", name: "cómputo", created_at: "2026-11-16T11:00:00Z" },
    { id: "a", name: "red", created_at: "2026-11-16T10:00:00Z" },
  ]);
});

test("el historial sobrevive a una nueva instancia (como al recargar)", () => {
  const storage = new FakeStorage();
  new HistoryStore(storage).add("a", "red", "2026-11-16T10:00:00Z");

  assert.equal(new HistoryStore(storage).list().length, 1);
});

test("add con un id repetido no lo duplica y lo sube al inicio", () => {
  const store = new HistoryStore(new FakeStorage());
  store.add("a", "red", "2026-11-16T10:00:00Z");
  store.add("b", "cómputo", "2026-11-16T11:00:00Z");
  store.add("a", "red", "2026-11-16T10:00:00Z");

  assert.deepEqual(
    store.list().map((entry) => entry.id),
    ["a", "b"],
  );
});

test("remove quita solo esa entrada", () => {
  const store = new HistoryStore(new FakeStorage());
  store.add("a", "red", "2026-11-16T10:00:00Z");
  store.add("b", "cómputo", "2026-11-16T11:00:00Z");
  store.remove("a");

  assert.deepEqual(
    store.list().map((entry) => entry.id),
    ["b"],
  );
  assert.equal(store.has("a"), false);
  assert.equal(store.has("b"), true);
});

test("guarda como máximo HISTORY_LIMIT entradas, descartando las más viejas", () => {
  const store = new HistoryStore(new FakeStorage());
  for (let i = 0; i <= HISTORY_LIMIT; i++) {
    store.add(`id-${i}`, `plan ${i}`, "2026-11-16T10:00:00Z");
  }

  const ids = store.list().map((entry) => entry.id);
  assert.equal(ids.length, HISTORY_LIMIT);
  assert.equal(ids[0], `id-${HISTORY_LIMIT}`);
  assert.ok(!ids.includes("id-0"));
});

test("un valor dañado en localStorage no rompe la lista", () => {
  const storage = new FakeStorage();
  const store = new HistoryStore(storage);

  storage.setItem("terragraph.history", "{no es json");
  assert.deepEqual(store.list(), []);

  storage.setItem("terragraph.history", JSON.stringify([{ id: 1 }, null, "x"]));
  assert.deepEqual(store.list(), []);
});

test("sin localStorage (bloqueado) el historial queda vacío sin errores", () => {
  const store = new HistoryStore(null);
  store.add("a", "red", "2026-11-16T10:00:00Z");
  store.remove("a");

  assert.deepEqual(store.list(), []);
});

test("si setItem falla (almacenamiento lleno) no lanza error", () => {
  const storage = new FakeStorage();
  storage.setItem = () => {
    throw new Error("QuotaExceededError");
  };

  assert.doesNotThrow(() => new HistoryStore(storage).add("a", "red", "2026-11-16T10:00:00Z"));
});
