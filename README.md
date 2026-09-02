<<<<<<< HEAD
# personalproject

**Self-hosted open-source stack — no subscriptions, full privacy.**

One installer bundles the tools that replace paid services:

| Tool | Replaces | Command / URL |
|------|----------|---------------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Paid downloaders | `pt download <url>` |
| [Ollama](https://ollama.com) | ChatGPT API | `pt ask "..."` · `:11434` |
| [Whisper](https://github.com/openai/whisper) | Otter.ai | `pt transcribe file.mp3` |
| [n8n](https://n8n.io) | Zapier / Make | http://localhost:5678 |
| [Penpot](https://penpot.app) | Figma | http://localhost:9001 |
| [Plausible](https://plausible.io) | Google Analytics | http://localhost:8000 |
| [Fooocus](https://github.com/lllyasviel/Fooocus) | Midjourney | http://localhost:7865 |

## Quick start

### macOS (recommended)

```bash
git clone https://github.com/fredl92/personalproject.git
cd personalproject
make dmg
open dist/Personal-Toolkit-1.0.0.dmg
```

Double-click **PersonalToolkit-Installer** → everything installs to `~/PersonalToolkit`.

### Linux

```bash
git clone https://github.com/fredl92/personalproject.git
cd personalproject
cp .env.example .env
make setup
```

## CLI

```bash
pt download "https://youtube.com/watch?v=..."
pt transcribe podcast.mp3
pt ask "Explain this simply"
pt pipeline "https://youtube.com/watch?v=..."   # download → transcribe → summarize
pt services up                                  # start n8n + Penpot
pt urls
```

## Requirements

- macOS 12+ or Linux (WSL2 on Windows)
- Docker Desktop for n8n and Penpot
- Python 3.10+
- NVIDIA GPU (Fooocus only)

## Project layout

```
personal-toolkit/
├── bin/pt                  Unified CLI
├── docker-compose.yml      n8n + Penpot
├── macos/                  DMG installer (macOS)
├── scripts/                Setup scripts
├── workflows/n8n/          Importable automations
└── config/mcp/             Cursor MCP configs
```

## License

MIT — see [LICENSE](LICENSE). Upstream tools retain their own licenses.
=======
# personalproject
>>>>>>> origin/main
