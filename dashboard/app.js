const APP_META = {
  n8n: {
    icon: "⚡",
    title: "n8n",
    desc: "Workflow automation — koppel apps en AI.",
    replaces: "Zapier / Make",
  },
  penpot: {
    icon: "🎨",
    title: "Penpot",
    desc: "Design tool — open-source Figma-alternatief.",
    replaces: "Figma",
  },
  plausible: {
    icon: "📊",
    title: "Plausible",
    desc: "Privacy-first analytics voor je websites.",
    replaces: "Google Analytics",
  },
  ollama: {
    icon: "🦙",
    title: "Ollama",
    desc: "Lokale LLM API — geen cloud, geen API-kosten.",
    replaces: "ChatGPT API",
  },
  fooocus: {
    icon: "🖼️",
    title: "Fooocus",
    desc: "AI-beeldgeneratie op je GPU.",
    replaces: "Midjourney",
  },
  dashboard: {
    icon: "◆",
    title: "Dashboard",
    desc: "Dit startoverzicht.",
    replaces: null,
  },
};

const CLI_COMMANDS = [
  { label: "Video downloaden", cmd: "pt download <url>" },
  { label: "Transcriberen (Whisper)", cmd: "pt transcribe <bestand>" },
  { label: "Vraag stellen (Ollama)", cmd: 'pt ask "jouw vraag"' },
  { label: "Pipeline (download → samenvatting)", cmd: "pt pipeline <url>" },
  { label: "Services starten", cmd: "pt services up" },
  { label: "Alle URLs tonen", cmd: "pt urls" },
];

function appUrl(host, app) {
  const base = `http://${host}:${app.port}`;
  return app.path ? `${base}${app.path}` : base;
}

async function checkOnline(url) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 4000);
    await fetch(url, { mode: "no-cors", cache: "no-store", signal: ctrl.signal });
    clearTimeout(t);
    return true;
  } catch {
    return false;
  }
}

function renderCards(cfg) {
  const grid = document.getElementById("app-grid");
  grid.innerHTML = "";

  const order = ["n8n", "penpot", "plausible", "ollama", "fooocus", "dashboard"];

  for (const key of order) {
    const app = cfg.apps[key];
    const meta = APP_META[key];
    if (!app || !meta) continue;

    const url = appUrl(cfg.host, app);
    const card = document.createElement("article");
    card.className = "card" + (app.optional ? " optional" : "");
    card.dataset.url = url;
    card.dataset.key = key;

    card.innerHTML = `
      <div class="card-top">
        <div class="card-icon">${meta.icon}</div>
        <span class="badge checking" data-status>…</span>
      </div>
      <h3>${meta.title}${app.optional ? ' <span class="badge optional-tag">optioneel</span>' : ""}</h3>
      <p class="desc">${meta.desc}${meta.replaces ? ` <em>Vervangt ${meta.replaces}.</em>` : ""}</p>
      <p class="url">${url}</p>
      <div class="card-actions">
        <a class="btn btn-primary" href="${url}" target="_blank" rel="noopener">Openen</a>
        <button class="btn btn-copy" type="button" data-copy="${url}" title="URL kopiëren">⎘</button>
      </div>
    `;
    grid.appendChild(card);
  }
}

function renderCli() {
  const list = document.getElementById("cli-list");
  list.innerHTML = CLI_COMMANDS.map(
    (c) => `
    <li class="cli-item">
      <span>${c.label}<br><code>${c.cmd}</code></span>
      <button class="btn btn-copy" type="button" data-copy="${c.cmd}">⎘</button>
    </li>`
  ).join("");
}

async function refreshStatus(cfg) {
  const cards = document.querySelectorAll(".card[data-url]");
  await Promise.all(
    [...cards].map(async (card) => {
      const badge = card.querySelector("[data-status]");
      const url = card.dataset.url;
      badge.className = "badge checking";
      badge.textContent = "…";
      const online = await checkOnline(url);
      badge.className = "badge " + (online ? "online" : "offline");
      badge.textContent = online ? "online" : "offline";
    })
  );
  document.getElementById("updated-at").textContent =
    "Bijgewerkt " + new Date().toLocaleTimeString("nl-NL");
}

function bindCopy() {
  document.body.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-copy]");
    if (!btn) return;
    navigator.clipboard.writeText(btn.dataset.copy).then(() => {
      const orig = btn.textContent;
      btn.textContent = "✓";
      setTimeout(() => { btn.textContent = orig; }, 1200);
    });
  });
}

function init() {
  const cfg = window.DASHBOARD_CONFIG || {
    host: "localhost",
    apps: {
      n8n: { port: 5678, optional: false },
      penpot: { port: 9001, optional: false },
      plausible: { port: 8000, optional: true },
      ollama: { port: 11434, optional: false },
      fooocus: { port: 7865, optional: true },
      dashboard: { port: 8080, optional: false },
    },
  };

  document.getElementById("dash-port").textContent =
    cfg.apps.dashboard?.port ?? 8080;

  renderCards(cfg);
  renderCli();
  bindCopy();
  refreshStatus(cfg);

  document.getElementById("refresh-btn").addEventListener("click", () => refreshStatus(cfg));
  setInterval(() => refreshStatus(cfg), 60000);
}

init();
