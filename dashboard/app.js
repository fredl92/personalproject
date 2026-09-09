"use strict";

function safeUrl(value) {
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("Ongeldige app-URL");
  }
  return url.href;
}

async function checkStatus(url, fetcher = fetch, timeout = 4000, options = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const response = await fetcher(safeUrl(url), {
      mode: "cors", cache: "no-store", credentials: "omit", signal: ctrl.signal,
    });
    if (response.type === "opaque" || response.type === "opaqueredirect" || response.status === 0) {
      return { state: "unknown", label: "Niet bevestigd", detail: "De browser kan het antwoord niet controleren. Probeer Openen." };
    }
    if ([502, 503, 504].includes(response.status)) {
      return { state: "unknown", label: "Niet bevestigd", detail: "De dienst is niet bereikbaar of start nog. Probeer Openen of de starthulp." };
    }
    if (!response.ok) {
      return { state: "error", label: `HTTP ${response.status}`, detail: "De dienst antwoordt met een fout." };
    }
    const result = { state: "online", label: "Bereikbaar", detail: "Een HTTP-antwoord is bevestigd; dit controleert niet alle functies van de app." };
    if (options.kind !== "ollama") return result;
    try {
      const body = typeof response.text === "function" ? await response.text() : "";
      return inspectOllamaHealth(body, options.model, result);
    } catch {
      return result;
    }
  } catch {
    return { state: "unknown", label: "Niet bevestigd", detail: "De dienst is niet bereikbaar, reageert te traag of de browser blokkeert de controle. Probeer Openen." };
  } finally {
    clearTimeout(timer);
  }
}

function inspectOllamaHealth(body, wanted, fallback) {
  let payload;
  try { payload = JSON.parse(body); } catch {
    return { ...fallback, detail: "Ollama antwoordt; de modellijst kon niet worden gelezen." };
  }
  const names = [];
  if (Array.isArray(payload?.models)) {
    for (const item of payload.models) {
      if (item && typeof item === "object") names.push(item.name || "", item.model || "");
      else if (typeof item === "string") names.push(item);
    }
  }
  if (!wanted) return fallback;
  if (!names.includes(wanted)) {
    return { state: "error", label: "Model ontbreekt", detail: `Ollama draait, maar ${wanted} is niet geïnstalleerd. Voer pt doctor uit.` };
  }
  return { state: "online", label: "Model klaar", detail: `${wanted} is geïnstalleerd. Dit test geen antwoordkwaliteit.` };
}

const TASKS = {
  pipeline: { title: "Samenvatting maken", short: "Samenvatten", icon: "≋", description: "Maak een transcript en Nederlandse samenvatting van een video of opname.", result: "De eerste verwerking kan even duren. Terminal toont waar het transcript en de samenvatting zijn opgeslagen. Bij een fout of Ctrl-C blijft het transcript bewaard; hervat met pt retry <id>." },
  transcribe: { title: "Opname uitschrijven", short: "Uitschrijven", icon: "↳", description: "Zet een audio- of videobestand om naar tekst met tijdsaanduidingen.", result: "Terminal toont het pad naar je tekstbestand. Het spraakmodel wordt bij het eerste gebruik gedownload." },
  download: { title: "Video downloaden", short: "Downloaden", icon: "↓", description: "Bewaar een video of alleen het geluid op je Mac.", result: "Terminal toont waar je download is opgeslagen." },
  ask: { title: "Vraag aan je AI", short: "Vraag stellen", icon: "✦", description: "Laat je lokale AI iets uitleggen, ideeën geven of een tekst helpen schrijven.", result: "Het antwoord verschijnt in Terminal. Controleer belangrijke feiten altijd zelf." },
};
const APP_META = {
  n8n: { title: "Taken automatiseren", name: "n8n", description: "Verbind je apps en laat terugkerende taken samenwerken.", command: "pt services up automation", help: "Open eerst Docker Desktop en wacht tot het draait. Plak daarna deze opdracht in Terminal. De eerste start downloadt ook een taalmodel en kan enkele minuten duren." },
  penpot: { title: "Ontwerpen maken", name: "Penpot", description: "Werk aan een ontwerp, scherm of klikbaar prototype.", command: "pt services up design", help: "Open eerst Docker Desktop en wacht tot het draait. Plak deze opdracht in Terminal en wacht tot de diensten gestart zijn." },
  plausible: { title: "Websitebezoekers bekijken", name: "Plausible", description: "Bekijk het bezoek aan een website die je zelf beheert.", command: 'cd "$HOME/PersonalToolkit" && make plausible', help: "Open Docker Desktop. Deze opdracht bereidt Plausible voor; voer daarna de startopdracht uit die Terminal toont. Dit gaat uit van de standaardinstallatie in ~/PersonalToolkit." },
  fooocus: { title: "Beelden maken", name: "Fooocus", description: "Genereer beelden op je eigen computer. Op Apple Silicon experimenteel.", command: 'cd "$HOME/PersonalToolkit" && make fooocus', help: "Deze opdracht bereidt de optionele installatie voor. Voer daarna de startopdracht uit die Terminal toont. Er worden extra bestanden en modellen gedownload. Dit gaat uit van de standaardinstallatie in ~/PersonalToolkit." },
  ollama: { title: "Je lokale AI starten", name: "Ollama", command: "brew services start ollama", help: "Ollama draait normaal na de installatie al op de achtergrond. Start de dienst zo nodig met deze opdracht. Gebruik daarna pt doctor om de installatie en het taalmodel te controleren." },
  dashboard: { name: "Dashboard" },
};
const CLI_COMMANDS = [
  { label: "Video downloaden", cmd: "pt download <url>" },
  { label: "Opname uitschrijven", cmd: "pt transcribe <bestand>" },
  { label: "Vraag stellen", cmd: 'pt ask "jouw vraag"' },
  { label: "Samenvatting maken", cmd: "pt pipeline <url>" },
  { label: "Automatisering starten", cmd: "pt services up automation" },
  { label: "Ontwerpen starten", cmd: "pt services up design" },
  { label: "Installatie controleren", cmd: "pt doctor" },
  { label: "Recente taken tonen", cmd: "pt jobs" },
  { label: "Taakdetails tonen", cmd: "pt job <id>" },
  { label: "Mislukte taak hervatten", cmd: "pt retry <id>" },
  { label: "Alle adressen tonen", cmd: "pt urls" },
];

function shellQuote(value) {
  return "'" + value.replace(/'/g, "'\\''") + "'";
}

function mediaUrl(value) {
  let url;
  try { url = new URL(value); } catch { throw new Error("Plak een volledige videolink die begint met https:// of http://."); }
  if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password || /\s/.test(value)) {
    throw new Error("Gebruik een http(s)-videolink zonder spaties, gebruikersnaam of wachtwoord.");
  }
  return shellQuote(value);
}

function localFilePath(value) {
  if (!/^file:/i.test(value)) return value;
  let url;
  try { url = new URL(value); } catch { throw new Error("Plak een geldig bestandspad of een lokale file://-link."); }
  if (url.protocol !== "file:" || url.username || url.password || url.search || url.hash) {
    throw new Error("Gebruik een lokaal bestandspad, zonder gebruikersnaam, wachtwoord of extra parameters.");
  }
  const host = (url.hostname || "").toLowerCase();
  if (host && host !== "localhost") throw new Error("Alleen lokale bestanden zijn toegestaan.");
  try {
    value = decodeURIComponent(url.pathname);
  } catch {
    throw new Error("De file://-link kon niet worden gelezen.");
  }
  if (!value || value === "/") throw new Error("Kies een bestand, niet alleen je thuismap.");
  return value;
}

function mediaPath(value) {
  value = localFilePath(value);
  if (!value.startsWith("/") && !value.startsWith("~/")) {
    throw new Error("Plak het volledige bestandspad uit Finder. Selecteer het bestand en druk op ⌥ + ⌘ + C.");
  }
  if (value === "/" || value === "~/") throw new Error("Kies een bestand, niet alleen je thuismap.");
  return value.startsWith("~/") ? '"$HOME"/' + shellQuote(value.slice(2)) : shellQuote(value);
}

function cycleTask(current, key, tasks = Object.keys(TASKS)) {
  const index = tasks.indexOf(current);
  if (key === "Home") return tasks[0];
  if (key === "End") return tasks[tasks.length - 1];
  const delta = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[key];
  if (!delta || index < 0) return current;
  return tasks[(index + delta + tasks.length) % tasks.length];
}

function describeModels(cfg) {
  const models = cfg?.models || {};
  const ollama = typeof models.ollama === "string" && models.ollama ? models.ollama : "het taalmodel";
  const whisper = typeof models.whisper === "string" ? models.whisper : "";
  const lang = typeof models.whisperLanguage === "string" ? models.whisperLanguage : "";
  let text = `Ollama voert ${ollama} uit. Het antwoord verschijnt in Terminal.`;
  if (whisper) {
    text += ` Uitschrijven gebruikt Whisper ${whisper}`;
    text += lang && lang !== "auto" ? ` (${lang}).` : ".";
  }
  return text;
}

function createCommand(task, input, { source = "url", audio = false } = {}) {
  if (!Object.hasOwn(TASKS, task)) throw new Error("Kies eerst een taak.");
  const value = typeof input === "string" ? input.trim() : "";
  if (!value) throw new Error(task === "ask" ? "Vul eerst je vraag in." : "Vul eerst een link of bestandspad in.");
  if (/[\x00-\x08\x0b-\x1f\x7f]/.test(value) || (task !== "ask" && /[\r\n\t]/.test(value))) {
    throw new Error("Verwijder onzichtbare tekens en plak de invoer opnieuw.");
  }
  if (task === "ask") return "pt ask -- " + shellQuote(value);
  if (task === "download") return "pt download " + mediaUrl(value) + (audio ? " --audio" : "");
  if (task === "transcribe") return "pt transcribe " + mediaPath(value);
  if (!["url", "file"].includes(source)) throw new Error("Kies een video of opname als bron.");
  return "pt pipeline " + (source === "file" ? mediaPath(value) : mediaUrl(value));
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function copyButton(value, label = "Kopieer", accessibleLabel = label) {
  const button = element("button", "btn btn-secondary", label);
  button.type = "button";
  button.dataset.copy = value;
  button.setAttribute("aria-label", accessibleLabel);
  return button;
}

let selectedTask = "pipeline";
let currentConfig = null;
let refreshBusy = false;
let toastTimer;

function invalidateResult() {
  document.getElementById("task-result").hidden = true;
  document.getElementById("generated-command").textContent = "";
  delete document.getElementById("copy-command").dataset.copy;
  document.getElementById("input-error").hidden = true;
  document.getElementById("task-input").removeAttribute("aria-invalid");
}

function configureInput() {
  const file = selectedTask === "transcribe" || (selectedTask === "pipeline" && document.getElementById("source-kind").value === "file");
  const ask = selectedTask === "ask";
  document.getElementById("source-field").hidden = selectedTask !== "pipeline";
  document.getElementById("audio-field").hidden = selectedTask !== "download";
  document.getElementById("input-label").textContent = ask ? "Je vraag" : file ? "Bestandspad van je opname" : "Videolink";
  const input = document.getElementById("task-input");
  input.placeholder = ask ? "Bijvoorbeeld: leg obligatieduration uit in eenvoudige woorden." : file ? "/Users/…/Documents/opname.m4a" : "https://www.youtube.com/watch?v=…";
  input.rows = ask ? 4 : 2;
  document.getElementById("input-help").textContent = ask ? "Stel je vraag in gewone taal." : file ? "Selecteer de opname in Finder, druk op ⌥ + ⌘ + C en plak het pad hier. Een file://-link mag ook. Je uploadt geen bestand." : "Plak de link van de video die je wilt verwerken.";
  invalidateResult();
}

function selectTask(task, focus = true) {
  selectedTask = task;
  for (const button of document.querySelectorAll("[data-task]")) {
    const on = button.dataset.task === task;
    button.setAttribute("aria-checked", String(on));
    button.tabIndex = on ? 0 : -1;
  }
  document.getElementById("task-heading").textContent = TASKS[task].title;
  document.getElementById("task-description").textContent = TASKS[task].description;
  document.getElementById("task-input").value = "";
  configureInput();
  if (focus) document.getElementById("task-input").focus();
}

function bindTasks() {
  const choices = document.getElementById("task-choices");
  choices.setAttribute("role", "radiogroup");
  choices.setAttribute("aria-label", "Kies je taak");
  for (const [key, task] of Object.entries(TASKS)) {
    const button = element("button", "task-choice");
    button.type = "button";
    button.dataset.task = key;
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(key === selectedTask));
    button.tabIndex = key === selectedTask ? 0 : -1;
    const icon = element("span", "task-icon", task.icon);
    icon.setAttribute("aria-hidden", "true");
    button.append(icon, element("span", "", task.short));
    button.addEventListener("click", () => selectTask(key));
    choices.append(button);
  }
  choices.addEventListener("keydown", event => {
    if (!["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = cycleTask(selectedTask, event.key);
    selectTask(next, false);
    choices.querySelector('[data-task="' + CSS.escape(next) + '"]')?.focus();
  });
  selectTask(selectedTask, false);
  document.getElementById("source-kind").addEventListener("change", configureInput);
  document.getElementById("audio-only").addEventListener("change", invalidateResult);
  document.getElementById("task-input").addEventListener("input", invalidateResult);
  document.getElementById("task-input").addEventListener("keydown", event => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      document.getElementById("task-form").requestSubmit();
    }
  });
  document.getElementById("task-form").addEventListener("submit", event => {
    event.preventDefault();
    invalidateResult();
    try {
      const command = createCommand(selectedTask, document.getElementById("task-input").value, {
        source: document.getElementById("source-kind").value, audio: document.getElementById("audio-only").checked,
      });
      document.getElementById("generated-command").textContent = command;
      document.getElementById("copy-command").dataset.copy = command;
      document.getElementById("result-help").textContent = TASKS[selectedTask].result;
      document.getElementById("task-result").hidden = false;
      document.getElementById("result-heading").focus();
    } catch (error) {
      const message = document.getElementById("input-error");
      message.textContent = error.message;
      message.hidden = false;
      document.getElementById("task-input").setAttribute("aria-invalid", "true");
      document.getElementById("task-input").focus();
    }
  });
}

function statusElements(target, app, key) {
  target.dataset.healthUrl = safeUrl(app.healthUrl || app.url);
  target.dataset.key = key;
  if (app.healthKind) target.dataset.healthKind = app.healthKind;
  const badge = element("span", "status checking", "Controleren…");
  badge.dataset.status = "";
  const detail = element("p", "status-detail", "");
  detail.dataset.statusDetail = "";
  return { badge, detail };
}

function renderApps(cfg) {
  const empty = document.getElementById("apps-empty");
  if (empty) empty.remove();
  const extraEmpty = document.getElementById("extra-empty");
  if (extraEmpty) extraEmpty.remove();
  for (const key of ["n8n", "penpot", "plausible", "fooocus"]) {
    const app = cfg.apps[key];
    if (!app) continue;
    const meta = APP_META[key];
    const card = element("article", "app-card");
    const { badge, detail } = statusElements(card, app, key);
    const heading = element("div", "card-heading");
    heading.append(element("h3", "", meta.title), badge);
    card.append(element("span", "app-name", meta.name), heading, element("p", "", meta.description), detail);
    const actions = element("div", "card-actions");
    const link = element("a", "btn btn-primary", "Open " + meta.name);
    link.href = safeUrl(app.url);
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const help = element("button", "btn btn-secondary", "Hulp bij starten");
    help.type = "button";
    help.dataset.help = key;
    help.setAttribute("aria-label", meta.name + ": hulp bij starten");
    actions.append(link, help);
    card.append(actions);
    document.getElementById(["plausible", "fooocus"].includes(key) ? "extra-grid" : "app-grid").append(card);
  }
  if (cfg.apps.ollama) {
    const target = document.getElementById("ai-status");
    const { badge, detail } = statusElements(target, cfg.apps.ollama, "ollama");
    target.append(badge, detail);
  }
  const addresses = document.getElementById("address-list");
  for (const [key, app] of Object.entries(cfg.apps)) {
    const item = element("li");
    const link = element("a", "", safeUrl(app.url));
    link.href = safeUrl(app.url);
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    item.append((APP_META[key]?.name || key) + ": ", link);
    addresses.append(item);
  }
}

function renderCli() {
  const list = document.getElementById("cli-list");
  for (const command of CLI_COMMANDS) {
    const item = element("li", "cli-item");
    const text = element("span");
    text.append(command.label, element("br"), element("code", "", command.cmd));
    item.append(text, copyButton(command.cmd, "Kopieer", command.label + ": commando kopiëren"));
    list.append(item);
  }
}

async function refreshStatus() {
  if (refreshBusy) return;
  refreshBusy = true;
  const button = document.getElementById("refresh-btn");
  button.disabled = true;
  button.textContent = "Controleren…";
  try {
    await Promise.all([...document.querySelectorAll("[data-health-url]")].map(async target => {
      const badge = target.querySelector("[data-status]");
      const detail = target.querySelector("[data-status-detail]");
      badge.className = "status checking";
      badge.textContent = "Controleren…";
      detail.textContent = "";
      const status = await checkStatus(target.dataset.healthUrl, fetch, 4000, {
        kind: target.dataset.healthKind,
        model: currentConfig?.models?.ollama,
      });
      badge.className = "status " + status.state;
      badge.textContent = status.label;
      badge.title = status.detail;
      detail.textContent = status.state === "online" ? status.detail : target.dataset.key === "ollama" ? status.detail || "Controleer je AI via de hulpknop hieronder." : status.state === "error" ? "Er is een fout. Bekijk de starthulp of voer pt doctor uit." : "Probeer Openen of bekijk de starthulp.";
    }));
    document.getElementById("updated-at").textContent = "Gecontroleerd om " + new Date().toLocaleTimeString("nl-BE", { hour: "2-digit", minute: "2-digit" });
  } finally {
    refreshBusy = false;
    button.disabled = false;
    button.textContent = "Controleer apps";
  }
}

function showToast(text) {
  const toast = document.getElementById("copy-message");
  clearTimeout(toastTimer);
  toast.textContent = text;
  toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, 5000);
}

function showHelp(key) {
  const meta = APP_META[key];
  if (!meta?.help) return;
  const dialog = document.getElementById("help-dialog");
  document.getElementById("dialog-title").textContent = meta.title;
  const content = document.getElementById("dialog-content");
  content.replaceChildren(element("p", "", meta.help));
  const box = element("div", "command-box");
  box.append(element("code", "", meta.command), copyButton(meta.command, "Kopieer startopdracht"));
  content.append(box, element("p", "", "Open Terminal via ⌘ + spatie, plak met ⌘ + V en druk op Enter."));
  if (key === "ollama") content.append(copyButton("pt doctor", "Kopieer controleopdracht"));
  const app = currentConfig?.apps[key];
  if (app && key !== "ollama") {
    const link = element("a", "btn btn-primary", "Open " + meta.name);
    link.href = safeUrl(app.url);
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    content.append(link);
  }
  if (!dialog.open) dialog.showModal();
}

function manualCopy(value) {
  const dialog = document.getElementById("help-dialog");
  document.getElementById("dialog-title").textContent = "Kopieer de geselecteerde tekst";
  const content = document.getElementById("dialog-content");
  const input = element("textarea", "manual-copy");
  input.value = value;
  input.readOnly = true;
  input.setAttribute("aria-label", "Commando om handmatig te kopiëren");
  content.replaceChildren(element("p", "", "Automatisch kopiëren lukt niet. Druk op ⌘ + C en plak de tekst in Terminal."), input);
  if (!dialog.open) dialog.showModal();
  input.focus();
  input.select();
}

function bindActions() {
  const dialog = document.getElementById("help-dialog");
  document.getElementById("close-help").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
  document.body.addEventListener("click", async event => {
    const help = event.target.closest("[data-help]");
    if (help) { showHelp(help.dataset.help); return; }
    const button = event.target.closest("[data-copy]");
    if (!button) return;
    const value = button.dataset.copy;
    const original = button.textContent;
    button.disabled = true;
    try {
      await navigator.clipboard.writeText(value);
      button.textContent = "Gekopieerd";
      showToast("Gekopieerd. Plak in Terminal en druk op Enter.");
      setTimeout(() => { if (button.textContent === "Gekopieerd") button.textContent = original; }, 2000);
    } catch { manualCopy(value); }
    finally { button.disabled = false; }
  });
}

function init() {
  bindTasks();
  bindActions();
  renderCli();
  const cfg = window.DASHBOARD_CONFIG;
  try {
    if (!cfg?.apps?.dashboard) throw new Error("Missing configuration");
    for (const app of Object.values(cfg.apps)) { safeUrl(app.url); if (app.healthUrl) safeUrl(app.healthUrl); }
    currentConfig = cfg;
    renderApps(cfg);
    document.getElementById("ai-model").textContent = describeModels(cfg);
  } catch {
    document.getElementById("config-error").hidden = false;
    document.getElementById("refresh-btn").disabled = true;
    document.getElementById("ai-status").textContent = "Status niet beschikbaar";
    return;
  }
  refreshStatus();
  document.getElementById("refresh-btn").addEventListener("click", refreshStatus);
  setInterval(() => { if (!document.hidden) refreshStatus(); }, 60000);
}

if (typeof module !== "undefined" && module.exports) module.exports = { checkStatus, safeUrl, CLI_COMMANDS, createCommand, shellQuote, describeModels, inspectOllamaHealth, cycleTask, localFilePath };
if (typeof document !== "undefined") init();
