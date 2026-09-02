"use strict";

const APP_META = {
  n8n: { icon: "⚡", title: "n8n", desc: "Koppel apps en AI in workflows.", command: "pt services up automation" },
  penpot: { icon: "🎨", title: "Penpot", desc: "Ontwerpen en prototypes maken.", command: "pt services up design" },
  plausible: { icon: "📊", title: "Plausible", desc: "Bezoekersstatistieken voor je websites.", command: "make plausible" },
  ollama: { icon: "🦙", title: "Ollama", desc: "De lokale modelserver voor de CLI. De Docker-workflow gebruikt een aparte server." },
  fooocus: { icon: "🖼️", title: "Fooocus", desc: "Beelden genereren. Op Apple Silicon experimenteel.", command: "make fooocus" },
  dashboard: { icon: "◆", title: "Dashboard", desc: "Dit startoverzicht.", command: "pt dashboard" },
};
const CLI_COMMANDS = [
  { label: "Video downloaden", cmd: "pt download <url>" },
  { label: "Transcriberen (Whisper)", cmd: "pt transcribe <bestand>" },
  { label: "Vraag stellen (Ollama)", cmd: 'pt ask "jouw vraag"' },
  { label: "Downloaden en samenvatten", cmd: "pt pipeline <url>" },
  { label: "Automatisering starten", cmd: "pt services up automation" },
  { label: "Ontwerpmodule starten", cmd: "pt services up design" },
  { label: "Alle links tonen", cmd: "pt urls" },
];

function safeUrl(value) {
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("Ongeldige app-URL");
  }
  return url.href;
}

async function checkStatus(url, fetcher = fetch, timeout = 4000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const response = await fetcher(safeUrl(url), {
      mode: "cors", cache: "no-store", credentials: "omit", signal: ctrl.signal,
    });
    if (response.type === "opaque" || response.type === "opaqueredirect" || response.status === 0) {
      return { state: "unknown", label: "Niet bevestigd", detail: "De browser kan het antwoord niet controleren. Probeer Openen." };
    }
    if (!response.ok) {
      return { state: "error", label: `HTTP ${response.status}`, detail: "De dienst antwoordt met een fout." };
    }
    return { state: "online", label: "Bereikbaar", detail: "Een HTTP-antwoord is bevestigd; dit controleert niet alle functies van de app." };
  } catch {
    return { state: "unknown", label: "Niet bevestigd", detail: "De dienst is niet bereikbaar, reageert te traag of de browser blokkeert de controle. Probeer Openen." };
  } finally {
    clearTimeout(timer);
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function copyButton(value, label) {
  const button = element("button", "btn btn-copy", "⎘");
  button.type = "button";
  button.dataset.copy = value;
  button.setAttribute("aria-label", label);
  return button;
}

function renderCards(cfg) {
  const grid = document.getElementById("app-grid");
  grid.replaceChildren();
  for (const key of ["n8n", "penpot", "plausible", "ollama", "fooocus", "dashboard"]) {
    const app = cfg.apps[key];
    const meta = APP_META[key];
    if (!app) continue;
    const url = safeUrl(app.url);
    const card = element("article", "card" + (app.optional ? " optional" : ""));
    card.dataset.url = url;
    card.dataset.healthUrl = safeUrl(app.healthUrl || app.url);
    card.dataset.key = key;
    const top = element("div", "card-top");
    const badge = element("span", "badge checking", "Controleren");
    badge.dataset.status = "";
    top.append(element("div", "card-icon", meta.icon), badge);
    const title = element("h3", "", meta.title);
    if (app.optional) title.append(" ", element("span", "badge optional-tag", "optioneel"));
    const actions = element("div", "card-actions");
    const link = element("a", "btn btn-primary", "Openen");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    actions.append(link, copyButton(url, `Link naar ${meta.title} kopiëren`));
    card.append(top, title, element("p", "desc", meta.desc), element("p", "url", url));
    if (meta.command) card.append(element("code", "start-command", meta.command));
    card.append(actions);
    grid.append(card);
  }
}

function renderCli() {
  const list = document.getElementById("cli-list");
  list.replaceChildren();
  for (const command of CLI_COMMANDS) {
    const item = element("li", "cli-item");
    const text = element("span");
    text.append(command.label, element("br"), element("code", "", command.cmd));
    item.append(text, copyButton(command.cmd, `${command.label}: commando kopiëren`));
    list.append(item);
  }
}

let refreshing = false;
async function refreshStatus() {
  if (refreshing) return;
  refreshing = true;
  const refresh = document.getElementById("refresh-btn");
  refresh.disabled = true;
  try {
    await Promise.all([...document.querySelectorAll(".card[data-url]")].map(async (card) => {
      const badge = card.querySelector("[data-status]");
      badge.className = "badge checking";
      badge.textContent = "Controleren";
      const status = await checkStatus(card.dataset.healthUrl);
      badge.className = "badge " + status.state;
      badge.textContent = status.label;
      badge.title = status.detail;
    }));
    document.getElementById("updated-at").textContent = "Bijgewerkt " + new Date().toLocaleTimeString("nl-BE");
  } finally {
    refreshing = false;
    refresh.disabled = false;
  }
}

function bindCopy() {
  document.body.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy]");
    if (!button) return;
    const message = document.getElementById("copy-message");
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      message.textContent = "Gekopieerd.";
      button.textContent = "✓";
      setTimeout(() => { button.textContent = "⎘"; }, 1200);
    } catch {
      message.textContent = "Kopiëren lukt niet. Selecteer en kopieer de tekst zelf: " + button.dataset.copy;
    }
  });
}

function init() {
  const cfg = window.DASHBOARD_CONFIG;
  if (!cfg || !cfg.apps || !cfg.apps.dashboard) {
    document.getElementById("config-error").hidden = false;
    document.getElementById("refresh-btn").disabled = true;
    return;
  }
  try {
    renderCards(cfg);
    renderCli();
    document.getElementById("dashboard-url").textContent = safeUrl(cfg.apps.dashboard.url);
  } catch {
    document.getElementById("config-error").hidden = false;
    document.getElementById("refresh-btn").disabled = true;
    return;
  }
  bindCopy();
  refreshStatus();
  document.getElementById("refresh-btn").addEventListener("click", refreshStatus);
  setInterval(refreshStatus, 60000);
}

if (typeof module !== "undefined" && module.exports) module.exports = { checkStatus, safeUrl, CLI_COMMANDS };
if (typeof document !== "undefined") init();
