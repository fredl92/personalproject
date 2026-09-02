# Personal Open-Source Toolkit

A unified setup for the open-source tools from your stack — all self-hosted, no subscriptions.

| Tool | What it replaces | How it runs here |
|------|------------------|------------------|
| **yt-dlp** | Paid downloaders | CLI via `pt download` |
| **Ollama** | ChatGPT API bills | Local LLM on port 11434 |
| **Fooocus** | Midjourney ($30/mo) | GPU app — `make fooocus` |
| **Whisper** | Otter ($20/mo) | CLI via `pt transcribe` |
| **Plausible** | Google Analytics 360 | Docker — `make plausible` |
| **Penpot** | Figma ($45/editor) | Docker — port 9001 |
| **n8n** | Zapier/Make per-task pricing | Docker — port 5678 |

## Quick start

```bash
git clone <this-repo> personal-toolkit && cd personal-toolkit
cp .env.example .env          # edit passwords before exposing to network
make setup                    # installs CLI tools + starts Docker services
```

Or step by step:

```bash
make install                  # yt-dlp, Ollama, faster-whisper
make up                       # n8n + Penpot (requires Docker)
./bin/pt urls                 # show where everything lives
```

## Unified CLI (`pt`)

```bash
./bin/pt download "https://youtube.com/watch?v=..."
./bin/pt transcribe podcast.mp3
./bin/pt ask "Explain this code pattern"
./bin/pt pipeline "https://youtube.com/watch?v=..."   # download → transcribe → summarize
./bin/pt services up
```

## Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| n8n | http://localhost:5678 | Default user/pass in `.env` |
| Penpot | http://localhost:9001 | Register on first visit |
| Plausible | http://localhost:8000 | Run `make plausible` first |
| Ollama API | http://localhost:11434 | Used by n8n AI nodes |
| Fooocus | http://localhost:7865 | Requires NVIDIA GPU |

## n8n + Ollama integration

n8n can call Ollama at `http://host.docker.internal:11434` (configured in `.env`).

Import the starter workflow from `workflows/n8n/download-transcribe-summarize.json` in the n8n UI.

Example Ollama node (HTTP Request):

```
POST http://host.docker.internal:11434/api/generate
{ "model": "llama3.2:3b", "prompt": "...", "stream": false }
```

## Penpot MCP (Cursor)

To connect Penpot designs to Cursor:

1. Start Penpot: `make up`
2. Create an access token in Penpot settings
3. Copy `config/mcp/penpot.cursor.json` into your Cursor MCP config and set `PENPOT_ACCESS_TOKEN`

Repo: [penpot/penpot-mcp](https://github.com/penpot/penpot-mcp)

## Plausible analytics

```bash
make plausible
cd services/plausible && docker compose up -d
```

Add this script to any site you track:

```html
<script defer data-domain="yourdomain.com" src="http://localhost:8000/js/script.js"></script>
```

## Fooocus (image generation)

Requires an NVIDIA GPU with 8 GB+ VRAM:

```bash
make fooocus
cd services/fooocus && python launch.py
```

Open http://localhost:7865

## Requirements

- **Linux or macOS** (Windows via WSL2)
- **Docker + Docker Compose** for n8n and Penpot
- **Python 3.10+** for yt-dlp and Whisper
- **ffmpeg** for media processing
- **NVIDIA GPU** for Fooocus only

## Hardware notes

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB+ (Penpot backend likes 4 GB alone) |
| Disk | 20 GB | 50 GB+ (Ollama models are large) |
| GPU | — | NVIDIA 8 GB+ VRAM for Fooocus |

## Project layout

```
.
├── bin/pt                 # unified CLI
├── docker-compose.yml     # n8n + Penpot
├── scripts/
│   ├── install-cli.sh     # yt-dlp, Ollama, Whisper
│   ├── setup-plausible.sh
│   └── setup-fooocus.sh
├── workflows/n8n/         # importable automation templates
└── config/mcp/            # Cursor MCP configs
```

## License

Configuration and scripts in this repo: MIT. Each upstream project retains its own license.
