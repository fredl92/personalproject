.PHONY: help setup install up down logs status urls download transcribe ask pipeline plausible fooocus dmg

help:
	@echo "Personal Open-Source Toolkit"
	@echo ""
	@echo "  make setup      Full first-time setup"
	@echo "  make install    Install CLI tools only (yt-dlp, Ollama, Whisper)"
	@echo "  make dmg        Build macOS installer DMG"
	@echo "  make up         Start Docker services (n8n, Penpot)"
	@echo "  make down       Stop Docker services"
	@echo "  make logs       Follow service logs"
	@echo "  make status     Show service status"
	@echo "  make urls       Show service URLs"
	@echo "  make plausible  Set up Plausible analytics"
	@echo "  make fooocus    Set up Fooocus (GPU required)"

setup:
	bash scripts/setup-all.sh

install:
	bash scripts/install-cli.sh

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

status:
	docker compose ps

urls:
	./bin/pt urls

download:
	./bin/pt download $(URL)

transcribe:
	./bin/pt transcribe $(FILE)

ask:
	./bin/pt ask "$(PROMPT)"

pipeline:
	./bin/pt pipeline $(URL)

plausible:
	bash scripts/setup-plausible.sh

fooocus:
	bash scripts/setup-fooocus.sh

dmg:
	bash macos/build-dmg.sh
