# Optionele modules: Plausible en Fooocus

Deze modules horen niet bij de lokale kern (`pt pipeline`, `pt doctor`). Ze starten **niet** automatisch: `make plausible` / `make fooocus` bereidt alleen voor. Laat ze uit staan tot je ze nodig hebt; na een test stop je ze weer. Ze vragen extra downloads en, voor Plausible, Docker. CI gebruikt geen echte accounts, API-tokens of websites. Open ze niet via het dashboard als de container niet draait — verwacht dan “Niet bevestigd”.

## Plausible (websitebezoek)

Alleen nuttig als je zelf een website beheert die je lokaal wilt meten. Dit is geen algemene “analytics-knop” voor de toolkit.

```bash
pt init
make plausible
```

De opdracht kloont de gepinde community-edition (tag in `scripts/setup-plausible.sh`), schrijft een lokale `.env` met `SECRET_KEY_BASE` uit jouw toolkit-`.env`, en bindt de UI op `127.0.0.1:8000`. Bestaande Plausible-config in `services/plausible` wordt niet overschreven.

Daarna, alleen wanneer je de dienst nodig hebt:

```bash
cd "$HOME/PersonalToolkit/services/plausible" && docker compose up -d
```

Open http://localhost:8000 en maak daar het lokale account aan. Zet geen meetcode op een site die je niet beheert. Stop met `docker compose stop` in dezelfde map.

De toolkit-CI start Plausible niet en maakt geen account. Een praktijktest is: Docker Desktop open, `make plausible`, stack starten, lokale UI bereikbaar, geen poort op `0.0.0.0`.

## Fooocus (beeldgeneratie)

Experimenteel. Upstream krijgt weinig onderhoud. De installer ondersteunt Apple Silicon (MPS) of Linux met NVIDIA; CPU-only is niet automatisch.

```bash
make fooocus
```

Daarna de startopdracht die Terminal toont (`entry_with_update.py` in `services/fooocus`). Er worden extra gewichten gedownload. Bestaande checkouts en modellen blijven bewaard; de script reset geen git-repo.

De Fooocus-UI luistert op poort `FOOOCUS_PORT` (standaard 7865), lokaal. Snelheid en kwaliteit op een M3 moet je zelf beoordelen. Dit is geen vervanging voor een clouddienst en geen onderdeel van `pt doctor`.

Fooocus heeft een eigen licentie; de MIT-licentie van deze toolkit vervangt die niet.

## Wat CI wel en niet dekt

Geautomatiseerde tests controleren dat een nieuwe Plausible-config aan localhost bindt en geheimen niet naar stdout schrijft. Er is geen live Fooocus/MPS-run en geen echte Plausible-site. Zie [validatie](validation.md).
