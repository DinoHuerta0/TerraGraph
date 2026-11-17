// Página de TerraGraph: sube un plan, lo dibuja con Cytoscape.js y muestra el
// orden de creación, los niveles paralelos y los ciclos. Los planes subidos se
// recuerdan en "Mis análisis" (HistoryStore, en history.js). Al hacer clic en un
// nodo se resalta su radio de impacto (funciones de blast-radius.js) y se
// muestran sus datos y relaciones en el panel lateral (node-details.js). El
// botón del encabezado cambia entre modo claro y oscuro (theme.js).
//
// Un análisis se abre directamente con /?id=<uuid>. Todo el texto que viene del
// plan se escribe con textContent (nunca innerHTML) para que un nombre o una
// dirección con HTML no se ejecute en la página.

"use strict";

// Los mismos colores que styles.css; cualquier acción desconocida va en gris.
const ACTION_COLORS = {
  create: "#2e9e5b",
  update: "#d4a017",
  replace: "#8e5cc9",
  delete: "#d64545",
  read: "#3d85c6",
  "no-op": "#9aa0a6",
};
// Contorno de los recursos que se rompen (el mismo que --affected en styles.css).
const BLAST_COLOR = "#e8710a";
// Grosor de las aristas. Son delgadas para que un plan con muchos recursos no se
// sature; las de un ciclo o del radio de impacto son un poco más gruesas para
// que resalten. arrowScale encoge la punta de la flecha, que Cytoscape no
// achica por debajo de un tamaño mínimo aunque la línea sea delgada.
const EDGE_STYLE = { width: 0.8, highlightWidth: 1.6, arrowScale: 0.7 };
// Colores del grafo que cambian con el tema (theme.js): el texto de las
// etiquetas, las aristas y el contorno del recurso elegido. Los colores de las
// acciones y del radio de impacto se leen bien en los dos.
const GRAPH_COLORS = {
  light: { label: "#202124", edge: "#b0b5bd", source: "#1f2a44" },
  dark: { label: "#e8eaed", edge: "#6b7280", source: "#e8eaed" },
};

const elements = {
  themeToggle: document.getElementById("theme-toggle"),
  form: document.getElementById("upload-form"),
  file: document.getElementById("plan-file"),
  name: document.getElementById("plan-name"),
  button: document.getElementById("upload-button"),
  error: document.getElementById("error"),
  result: document.getElementById("result"),
  analysisName: document.getElementById("analysis-name"),
  analysisMeta: document.getElementById("analysis-meta"),
  analysisLink: document.getElementById("analysis-link"),
  graph: document.getElementById("graph"),
  blastInfo: document.getElementById("blast-info"),
  cyclesBox: document.getElementById("cycles-box"),
  cycles: document.getElementById("cycles"),
  creationOrder: document.getElementById("creation-order"),
  parallelLevels: document.getElementById("parallel-levels"),
  summary: document.getElementById("summary"),
  nodeDetails: document.getElementById("node-details"),
  nodeAddress: document.getElementById("node-address"),
  nodeType: document.getElementById("node-type"),
  nodeName: document.getElementById("node-name"),
  nodeProvider: document.getElementById("node-provider"),
  nodeAction: document.getElementById("node-action"),
  nodeActionSwatch: document.getElementById("node-action-swatch"),
  dependsOn: document.getElementById("depends-on"),
  dependsOnCount: document.getElementById("depends-on-count"),
  dependents: document.getElementById("dependents"),
  dependentsCount: document.getElementById("dependents-count"),
  historyList: document.getElementById("history-list"),
  historyEmpty: document.getElementById("history-empty"),
};

let cy = null; // instancia de Cytoscape del análisis que se está viendo
let currentId = null; // id del análisis que se está viendo, para marcarlo en el historial
let blastRequest = 0; // aumenta con cada clic en el grafo; sirve para ignorar respuestas viejas

// browserStorage() está en theme.js, que se carga primero. Si localStorage está
// bloqueado, el historial queda vacío.
const historyStore = new HistoryStore(browserStorage());

// --- API ---

// Error de la API con su código HTTP, para distinguir un 404 de otros errores.
class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Hace la petición y devuelve el JSON; si la API responde con error, lanza un
// ApiError con el mensaje de `detail` para mostrarlo tal cual.
async function requestJson(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("No se pudo conectar con el servidor.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response.status, body));
  }
  return body;
}

function errorMessage(status, body) {
  const detail = body && body.detail;
  // Los errores de validación de FastAPI (422) traen una lista de objetos.
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join("; ");
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (status === 413) {
    return "El plan pesa más de 2 MB.";
  }
  return `Error inesperado del servidor (${status}).`;
}

function createAnalysis(name, plan) {
  return requestJson("/api/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, plan }),
  });
}

function fetchAnalysis(id) {
  return requestJson(`/api/analyses/${encodeURIComponent(id)}`);
}

// --- Mensajes ---

function showError(message) {
  elements.error.textContent = message;
  elements.error.hidden = false;
}

function clearError() {
  elements.error.textContent = "";
  elements.error.hidden = true;
}

// --- Dibujo del grafo ---

// Pares [origen, destino] de las aristas que forman parte de un ciclo.
// Un ciclo [A, B, C] significa A -> B -> C -> A.
function cycleEdgeKeys(cycles) {
  const keys = new Set();
  for (const cycle of cycles) {
    cycle.forEach((address, i) => {
      keys.add(`${address}\n${cycle[(i + 1) % cycle.length]}`);
    });
  }
  return keys;
}

function toCytoscapeElements(graph, cycles) {
  const inCycle = cycleEdgeKeys(cycles);
  const nodes = graph.nodes.map((node) => ({
    data: {
      id: node.address,
      label: node.address,
      type: node.type,
      name: node.name,
      provider: node.provider,
      action: node.action,
    },
  }));
  const edges = graph.edges.map((edge) => ({
    data: { source: edge.source, target: edge.target },
    classes: inCycle.has(`${edge.source}\n${edge.target}`) ? "cycle" : "",
  }));
  return [...nodes, ...edges];
}

function drawGraph(analysis) {
  if (cy) {
    cy.destroy();
  }
  cy = cytoscape({
    container: elements.graph,
    elements: toCytoscapeElements(analysis.graph, analysis.cycles),
    wheelSensitivity: 0.2,
    // Sin la selección de Cytoscape (que pinta el nodo de azul): el clic solo
    // muestra el radio de impacto y los detalles.
    autounselectify: true,
    style: graphStyle(),
    layout: graphLayout(analysis),
  });

  // "tap" funciona con el mouse y con pantallas táctiles.
  cy.on("tap", "node", (event) => selectNode(analysis.id, event.target.id()));
  cy.on("tap", (event) => {
    // Clic en el fondo (no en un nodo ni en una arista).
    if (event.target === cy) {
      clearSelection();
    }
  });
  clearSelection();
}

// --- Selección de un recurso ---

function selectNode(analysisId, address) {
  showBlastRadius(analysisId, address);
  showNodeDetails(analysisId, address);
}

function clearSelection() {
  hideBlastRadius();
  hideNodeDetails();
}

// Elegir un recurso desde la lista del panel: además de seleccionarlo, mueve el
// grafo para que quede al centro, porque en un plan grande puede estar fuera de
// la vista.
function goToNode(analysisId, address) {
  selectNode(analysisId, address);
  cy.animate({ center: { eles: cy.getElementById(address) } }, { duration: 300 });
}

// Estilos del grafo. Dependen del tema (colores de las etiquetas, las aristas y
// el contorno del recurso elegido), así que se vuelven a calcular al cambiarlo.
function graphStyle() {
  const colors = GRAPH_COLORS[currentTheme()];
  return [
    {
      selector: "node",
      style: {
        "background-color": (node) => ACTION_COLORS[node.data("action")] || "#9aa0a6",
        label: "data(label)",
        color: colors.label,
        "font-size": 10,
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-wrap": "wrap",
        "text-max-width": 160,
        // Las direcciones no tienen espacios: se cortan en cualquier carácter
        // para que una larga no se salga del contenedor.
        "text-overflow-wrap": "anywhere",
        width: 22,
        height: 22,
      },
    },
    {
      // La flecha apunta a la dependencia: A -> B significa "A depende de B".
      selector: "edge",
      style: {
        width: EDGE_STYLE.width,
        "line-color": colors.edge,
        "target-arrow-color": colors.edge,
        "target-arrow-shape": "triangle",
        "arrow-scale": EDGE_STYLE.arrowScale,
        "curve-style": "bezier",
      },
    },
    {
      selector: "edge.cycle",
      style: {
        width: EDGE_STYLE.highlightWidth,
        "line-color": "#d64545",
        "target-arrow-color": "#d64545",
      },
    },
    // Radio de impacto. Van al final para ganarle a los estilos de arriba.
    {
      selector: "node.blast-source",
      style: {
        "border-width": 4,
        "border-color": colors.source,
        width: 30,
        height: 30,
      },
    },
    {
      selector: "node.affected",
      style: { "border-width": 4, "border-color": BLAST_COLOR },
    },
    {
      selector: "edge.affected",
      style: {
        width: EDGE_STYLE.highlightWidth,
        "line-color": BLAST_COLOR,
        "target-arrow-color": BLAST_COLOR,
      },
    },
    {
      selector: ".dimmed",
      style: { opacity: 0.15 },
    },
  ];
}

// Separación entre nodos, en píxeles; las direcciones son largas, así que la
// horizontal es mayor.
const LEVEL_GAP = { x: 220, y: 120 };

// Acomoda los nodos con los niveles paralelos que calcula la API (algoritmo de
// Kahn): abajo el nivel 1 (lo que no depende de nada, como la VPC) y arriba el
// último. Así cada flecha apunta hacia abajo, a su dependencia.
function graphLayout(analysis) {
  const levels = analysis.parallel_levels;
  if (levels.length === 0) {
    // Con ciclos no hay niveles: se usa un acomodo por fuerzas que trae Cytoscape.
    return { name: "cose", padding: 40, animate: false };
  }
  const positions = {};
  levels.forEach((level, depth) => {
    level.forEach((address, i) => {
      positions[address] = {
        // Cada nivel queda centrado en el eje x.
        x: (i - (level.length - 1) / 2) * LEVEL_GAP.x,
        y: (levels.length - 1 - depth) * LEVEL_GAP.y,
      };
    });
  });
  return { name: "preset", positions, fit: true, padding: 40 };
}

// --- Radio de impacto ---

const BLAST_HINT = "Haz clic en un recurso para ver sus relaciones y qué se rompe si lo destruyes.";

function setBlastInfo(text, isError = false) {
  elements.blastInfo.textContent = text;
  elements.blastInfo.classList.toggle("failed", isError);
}

async function showBlastRadius(analysisId, address) {
  // Si se hace clic en otro nodo (o en el fondo) antes de que llegue la
  // respuesta, esta ya no corresponde a lo que se ve y se ignora.
  const request = ++blastRequest;
  try {
    const result = await requestJson(blastRadiusUrl(analysisId, address));
    if (request !== blastRequest) {
      return;
    }
    highlightBlastRadius(cy, address, result.affected);
    setBlastInfo(
      `${blastRadiusMessage(address, result.affected)} Haz clic en el fondo para quitar el resaltado.`,
    );
  } catch (error) {
    if (request !== blastRequest) {
      return;
    }
    clearBlastRadius(cy);
    setBlastInfo(error.message, true);
  }
}

function hideBlastRadius() {
  blastRequest++;
  clearBlastRadius(cy);
  setBlastInfo(BLAST_HINT);
}

// --- Detalles del recurso ---

function showNodeDetails(analysisId, address) {
  const details = nodeDetails(cy, address);
  if (!details) {
    hideNodeDetails();
    return;
  }
  elements.nodeAddress.textContent = details.address;
  elements.nodeType.textContent = details.type || "—";
  elements.nodeName.textContent = details.name || "—";
  elements.nodeProvider.textContent = details.provider || "—";
  elements.nodeAction.textContent = details.action;
  elements.nodeActionSwatch.style.background = ACTION_COLORS[details.action] || "#9aa0a6";
  fillRelations(elements.dependsOn, elements.dependsOnCount, details.dependsOn, analysisId);
  fillRelations(elements.dependents, elements.dependentsCount, details.dependents, analysisId);
  elements.nodeDetails.hidden = false;
  // El panel está arriba del resumen; se sube el scroll para que se vea.
  elements.summary.scrollTop = 0;
}

function hideNodeDetails() {
  elements.nodeDetails.hidden = true;
}

// Cada relación es un botón que lleva a ese recurso, para recorrer el plan
// desde el panel.
function fillRelations(list, count, addresses, analysisId) {
  count.textContent = addresses.length;
  list.replaceChildren();
  if (addresses.length === 0) {
    const item = document.createElement("li");
    item.className = "hint";
    item.textContent = "Ninguno";
    list.appendChild(item);
    return;
  }
  for (const address of addresses) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = address;
    button.addEventListener("click", () => goToNode(analysisId, address));
    item.appendChild(button);
    list.appendChild(item);
  }
}

// --- Resumen ---

function fillList(list, items, emptyText) {
  list.replaceChildren();
  if (items.length === 0) {
    const item = document.createElement("li");
    item.className = "hint";
    item.textContent = emptyText;
    list.appendChild(item);
    return;
  }
  for (const text of items) {
    const item = document.createElement("li");
    item.textContent = text;
    list.appendChild(item);
  }
}

function showSummary(analysis) {
  const hasCycles = analysis.cycles.length > 0;
  elements.cyclesBox.hidden = !hasCycles;
  fillList(
    elements.cycles,
    analysis.cycles.map((cycle) => [...cycle, cycle[0]].join(" → ")),
    "",
  );
  const noOrder = hasCycles ? "No hay orden porque el plan tiene ciclos." : "El plan no tiene recursos.";
  fillList(elements.creationOrder, analysis.creation_order, noOrder);
  fillList(
    elements.parallelLevels,
    analysis.parallel_levels.map((level) => level.join(", ")),
    noOrder,
  );
}

function showAnalysis(analysis) {
  elements.analysisName.textContent = analysis.name;
  const date = new Date(analysis.created_at).toLocaleString();
  elements.analysisMeta.textContent = `${analysis.resource_count} recursos · subido el ${date}`;
  elements.analysisLink.href = analysisUrl(analysis.id);
  showSummary(analysis);
  // El contenedor tiene que estar visible antes de dibujar para que Cytoscape
  // conozca su tamaño.
  elements.result.hidden = false;
  drawGraph(analysis);
}

// --- Mis análisis ---

function renderHistory() {
  const entries = historyStore.list();
  elements.historyEmpty.hidden = entries.length > 0;
  elements.historyList.replaceChildren(...entries.map(historyItem));
}

function historyItem(entry) {
  const item = document.createElement("li");
  if (entry.id === currentId) {
    item.className = "current";
  }

  const info = document.createElement("div");
  info.className = "entry";
  const link = document.createElement("a");
  link.href = analysisUrl(entry.id);
  link.textContent = entry.name;
  link.title = entry.name;
  if (entry.id === currentId) {
    link.setAttribute("aria-current", "page");
  }
  // Abre el análisis sin recargar la página; con Ctrl o clic central se abre
  // en otra pestaña como cualquier enlace.
  link.addEventListener("click", (event) => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.button !== 0) {
      return;
    }
    event.preventDefault();
    openAnalysis(entry.id);
  });
  const date = document.createElement("small");
  date.textContent = new Date(entry.created_at).toLocaleString();
  info.append(link, date);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "Quitar";
  remove.setAttribute("aria-label", `Quitar ${entry.name} de Mis análisis`);
  // Solo lo quita del historial de este navegador; el análisis sigue en el
  // servidor y su enlace sigue funcionando.
  remove.addEventListener("click", () => {
    historyStore.remove(entry.id);
    renderHistory();
  });

  item.append(info, remove);
  return item;
}

// --- Tema ---

// El tema ya lo aplicó theme.js al cargar; aquí solo se conecta el botón.
function renderThemeToggle() {
  const dark = currentTheme() === "dark";
  elements.themeToggle.textContent = dark ? "Modo claro" : "Modo oscuro";
  elements.themeToggle.setAttribute("aria-pressed", String(dark));
}

function toggleTheme() {
  const theme = otherTheme(currentTheme());
  applyTheme(theme);
  saveTheme(browserStorage(), theme);
  renderThemeToggle();
  // Cytoscape dibuja en un canvas y no usa styles.css: se le pasan los estilos
  // con los colores del nuevo tema. Las clases (radio de impacto, ciclos) se
  // conservan.
  if (cy) {
    cy.style(graphStyle());
  }
}

// --- Flujo de la página ---

function analysisUrl(id) {
  return `/?id=${encodeURIComponent(id)}`;
}

// Cambia la URL al análisis (para compartirla o recargar) y lo abre.
function openAnalysis(id) {
  history.pushState({ id }, "", analysisUrl(id));
  loadAnalysis(id);
}

function setCurrent(id) {
  currentId = id;
  renderHistory();
}

async function loadAnalysis(id) {
  clearError();
  setCurrent(id);
  try {
    showAnalysis(await fetchAnalysis(id));
  } catch (error) {
    elements.result.hidden = true;
    setCurrent(null);
    if (error.status === 404 && historyStore.has(id)) {
      // El análisis ya no está en el servidor (por ejemplo, se limpió la base
      // de datos): se quita del historial para que no vuelva a fallar.
      historyStore.remove(id);
      renderHistory();
      showError("Ese análisis ya no existe, así que se quitó de Mis análisis.");
    } else {
      showError(error.message);
    }
  }
}

async function readPlanFile(file) {
  const text = await file.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("El archivo no es un JSON válido.");
  }
}

async function onSubmit(event) {
  event.preventDefault();
  clearError();
  elements.button.disabled = true;
  try {
    const plan = await readPlanFile(elements.file.files[0]);
    const analysis = await createAnalysis(elements.name.value, plan);
    // Solo se guardan en el historial los planes que se suben aquí, no los
    // que alguien abre con un enlace compartido.
    historyStore.add(analysis.id, analysis.name, analysis.created_at);
    // La URL queda con el id para poder compartirla o recargar la página.
    history.pushState({ id: analysis.id }, "", analysisUrl(analysis.id));
    setCurrent(analysis.id);
    showAnalysis(analysis);
  } catch (error) {
    showError(error.message);
  } finally {
    elements.button.disabled = false;
  }
}

// Al elegir un archivo, su nombre (sin .json) reemplaza el nombre del plan, para
// que no se quede el del archivo anterior. Se puede editar después de elegirlo.
function onFileChange() {
  const file = elements.file.files[0];
  if (file) {
    elements.name.value = file.name.replace(/\.json$/i, "");
  }
}

// Abre el análisis de la URL (/?id=…) o deja la página vacía si no hay id.
function loadFromUrl() {
  const id = new URLSearchParams(window.location.search).get("id");
  if (id) {
    loadAnalysis(id);
  } else {
    clearError();
    elements.result.hidden = true;
    setCurrent(null);
  }
}

elements.form.addEventListener("submit", onSubmit);
elements.file.addEventListener("change", onFileChange);
elements.themeToggle.addEventListener("click", toggleTheme);
renderThemeToggle();
// Botones de atrás y adelante del navegador.
window.addEventListener("popstate", loadFromUrl);
loadFromUrl();
