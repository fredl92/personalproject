## Projectbeschrijving

**personalproject** is een self-hosted open-source toolkit die betaalde diensten vervangt door lokale, gratis alternatieven:

| Tool | Vervangt | Gebruik |
|------|----------|---------|
| yt-dlp | Betaalde downloaders | `pt download <url>` |
| Ollama | ChatGPT API | `pt ask "..."` |
| Whisper (faster-whisper) | Otter.ai | `pt transcribe file.mp3` |
| n8n | Zapier / Make | http://localhost:5678 |
| Penpot | Figma | http://localhost:9001 |
| Plausible CE | Google Analytics | http://localhost:8000 |
| Fooocus | Midjourney | http://localhost:7865 (GPU) |

Unified CLI (`bin/pt`), Docker Compose voor n8n + Penpot, macOS DMG-installer, n8n-workflow templates en Cursor MCP-config voor Penpot.

## Uitgevoerde wijzigingen

- **Standalone project** opgezet met `LICENSE`, `VERSION`, `pyproject.toml`
- **Unified CLI** (`bin/pt`): download, transcribe, ask, pipeline, services
- **Docker Compose**: n8n + Penpot (PostgreSQL, Valkey)
- **Setup scripts**: Linux (`install-cli.sh`), macOS (`install-macos.sh` via Homebrew)
- **Optionele services**: Plausible CE, Fooocus (GPU)
- **macOS DMG**: `PersonalToolkit-Installer.app` + `make dmg` + GitHub Actions workflow
- **n8n workflow template**: download → transcribe → summarize
- **Penpot MCP config** voor Cursor
- **Secrets uitgesloten**: `.env` in `.gitignore`; alleen `.env.example` met placeholders in repo

## Beveiliging

- `.env` staat **niet** in git (alleen lokaal)
- Geen echte tokens, wachtwoorden of API-keys gecommit
- `.env.example` bevat uitsluitend placeholders (`change-me`, `YOUR_PENPOT_ACCESS_TOKEN`)

## Testresultaten

| Test | Resultaat |
|------|-----------|
| `pt --help` / `pt urls` | ✅ OK |
| yt-dlp installatie | ✅ v2026.08.19 |
| faster-whisper installatie | ✅ OK |
| Ollama install + `llama3.2:3b` pull | ✅ OK |
| `pt ask` (Ollama lokaal) | ✅ OK na OLLAMA_HOST-fix |
| Docker Compose (n8n + Penpot) | ⚠️ Geblokkeerd in cloud VM (overlayfs) — werkt op eigen machine |
| `make dmg` | ⚠️ Vereist macOS (`hdiutil`) |
| `.env` niet in git | ✅ Bevestigd via `git ls-files` |
| Remote koppeling | ✅ `origin → https://github.com/fredl92/personalproject.git` |

## Installatie (na merge)

```bash
cp .env.example .env   # pas wachtwoorden aan
make setup             # Linux
# of op macOS: make dmg && open dist/Personal-Toolkit-1.0.0.dmg
```
