// HistoryStore: guarda en localStorage los análisis que subió esta persona, para
// la sección "Mis análisis". No hay cuentas: el historial vive solo en este
// navegador y nunca se manda al servidor.
//
// Cada entrada es { id, name, created_at }. La lista va de la más reciente a la
// más antigua y no repite ids.

"use strict";

const HISTORY_KEY = "terragraph.history";
// Tope para que el historial no crezca sin límite en localStorage.
const HISTORY_LIMIT = 50;

class HistoryStore {
  // `storage` es window.localStorage en la página y un objeto falso en las
  // pruebas. Puede ser null si el navegador bloquea localStorage: entonces el
  // historial queda vacío y la página sigue funcionando.
  constructor(storage, key = HISTORY_KEY) {
    this.storage = storage;
    this.key = key;
  }

  list() {
    if (!this.storage) {
      return [];
    }
    try {
      const entries = JSON.parse(this.storage.getItem(this.key));
      // Si alguien editó el valor a mano o es de otra versión, se ignora lo que
      // no tenga la forma esperada en vez de romper la página.
      return Array.isArray(entries) ? entries.filter(isValidEntry) : [];
    } catch {
      return [];
    }
  }

  add(id, name, createdAt) {
    const others = this.list().filter((entry) => entry.id !== id);
    const entries = [{ id, name, created_at: createdAt }, ...others];
    this.save(entries.slice(0, HISTORY_LIMIT));
  }

  remove(id) {
    this.save(this.list().filter((entry) => entry.id !== id));
  }

  has(id) {
    return this.list().some((entry) => entry.id === id);
  }

  save(entries) {
    if (!this.storage) {
      return;
    }
    try {
      this.storage.setItem(this.key, JSON.stringify(entries));
    } catch {
      // Almacenamiento lleno o bloqueado: el análisis ya está guardado en el
      // servidor, solo no queda en el historial.
    }
  }
}

function isValidEntry(entry) {
  return (
    entry !== null &&
    typeof entry === "object" &&
    typeof entry.id === "string" &&
    typeof entry.name === "string" &&
    typeof entry.created_at === "string"
  );
}

// En el navegador HistoryStore queda como global para app.js; en Node se
// exporta para las pruebas de tests/js/.
if (typeof module !== "undefined") {
  module.exports = { HistoryStore, HISTORY_LIMIT };
}
