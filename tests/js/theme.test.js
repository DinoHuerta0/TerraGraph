// Pruebas de la elección del tema (theme.js) con el runner que trae Node.

"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");

const {
  THEME_KEY,
  savedTheme,
  saveTheme,
  initialTheme,
  otherTheme,
} = require("../../app/static/theme.js");

// Imita la parte de localStorage que usa theme.js.
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

// localStorage bloqueado: cualquier acceso lanza un error.
const blockedStorage = {
  getItem() {
    throw new Error("bloqueado");
  },
  setItem() {
    throw new Error("bloqueado");
  },
};

test("sin tema guardado se usa el del sistema", () => {
  assert.equal(initialTheme(new FakeStorage(), true), "dark");
  assert.equal(initialTheme(new FakeStorage(), false), "light");
});

test("el tema guardado gana sobre el del sistema", () => {
  const storage = new FakeStorage();
  saveTheme(storage, "light");
  assert.equal(storage.getItem(THEME_KEY), "light");
  assert.equal(initialTheme(storage, true), "light");
});

test("un valor guardado inválido se ignora", () => {
  const storage = new FakeStorage();
  storage.setItem(THEME_KEY, "morado");
  assert.equal(savedTheme(storage), null);
  assert.equal(initialTheme(storage, false), "light");
});

test("con localStorage bloqueado o ausente no se rompe", () => {
  assert.equal(initialTheme(blockedStorage, true), "dark");
  assert.doesNotThrow(() => saveTheme(blockedStorage, "dark"));
  assert.equal(initialTheme(null, false), "light");
  assert.doesNotThrow(() => saveTheme(null, "dark"));
});

test("otherTheme alterna entre claro y oscuro", () => {
  assert.equal(otherTheme("light"), "dark");
  assert.equal(otherTheme("dark"), "light");
});
