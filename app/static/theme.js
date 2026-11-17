// Modo claro y modo oscuro. La elección se guarda en localStorage; si la persona
// nunca eligió, se usa el tema de su sistema (prefers-color-scheme).
//
// Este script se carga sin `defer` en el <head>, antes de que se dibuje la
// página: así el tema se aplica desde el inicio y no se ve un parpadeo blanco al
// abrirla en modo oscuro. El botón y el grafo los conecta app.js.

"use strict";

const THEME_KEY = "terragraph.theme";
const THEMES = ["light", "dark"];

// Tema guardado, o null si no hay uno válido o localStorage está bloqueado.
function savedTheme(storage) {
  try {
    const theme = storage && storage.getItem(THEME_KEY);
    return THEMES.includes(theme) ? theme : null;
  } catch {
    return null;
  }
}

// Si no se puede guardar (localStorage bloqueado o lleno), el tema cambia igual
// y solo se pierde al recargar.
function saveTheme(storage, theme) {
  try {
    if (storage) {
      storage.setItem(THEME_KEY, theme);
    }
  } catch {
    // Se ignora a propósito.
  }
}

function initialTheme(storage, prefersDark) {
  return savedTheme(storage) || (prefersDark ? "dark" : "light");
}

function otherTheme(theme) {
  return theme === "dark" ? "light" : "dark";
}

// Los estilos de styles.css dependen del atributo data-theme de <html>.
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
}

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

// Algunos navegadores lanzan un error solo por leer window.localStorage (por
// ejemplo, con las cookies bloqueadas). app.js también la usa para el historial.
function browserStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

if (typeof document !== "undefined") {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(initialTheme(browserStorage(), prefersDark));
}

// En el navegador quedan como globales para app.js; en Node se exportan para
// las pruebas de tests/js/.
if (typeof module !== "undefined") {
  module.exports = { THEME_KEY, savedTheme, saveTheme, initialTheme, otherTheme };
}
