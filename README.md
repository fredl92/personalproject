# Personal Toolkit

Lokale transcripties en Nederlandse samenvattingen, met optionele modules voor automatisering, ontwerp, analytics en beeldgeneratie.

**Status:** herstelversie 1.0.1. Zie [validatie](docs/validation.md) voor wat automatisch getest wordt en wat nog een praktijktest vereist. Lokale modellen zijn geen garantie op correcte samenvattingen of gelijkwaardige kwaliteit aan een clouddienst.

## Begin klein: de lokale kern

Benodigd: macOS op Apple Silicon met Homebrew, of Linux met Python 3.10+, ffmpeg en Ollama. Voor de Mac-installer wordt Homebrew Python 3.12 gebruikt. Docker is niet nodig voor de kern.

```bash
make setup
# Open daarna een nieuw Terminal-venster op macOS.
pt doctor
pt pipeline "/pad/naar/opname met spaties.wav"
pt pipeline "https://www.youtube.com/watch?v=VIDEO_ID"
```

`make setup` installeert de Python-pakketten, initialiseert `.env`, start Ollama op macOS en downloadt het ingestelde model. Op Linux moet Ollama vooraf geïnstalleerd en gestart zijn. Fouten stoppen de installatie met een foutcode; er volgt geen onterechte succesmelding.

Elke pipeline maakt een unieke map `data/jobs/<id>/` met `job.json`, een transcript met tijdsaanduidingen, segmenten in JSON en een Nederlandse `summary.md`. Lange transcripties worden in delen samengevat en daarna samengevoegd. Controleer belangrijke uitspraken steeds in het transcript. Bij een fout blijft reeds geproduceerde uitvoer bewaard.

```bash
pt download "https://example.org/video" --audio
pt transcribe "opname.wav"
pt summarize "transcript.txt"
pt ask "Leg obligatieduration eenvoudig uit"
pt job JOB_ID
```

## Kies modules wanneer je ze nodig hebt

| Module | Start | Stop | Opmerking |
|---|---|---|---|
| Automatisering | `pt services up automation` | `pt services down automation` | Docker: n8n, verwerkingsdienst en aparte Ollama |
| Ontwerp | `pt services up design`, daarna `pt mcp` | `pt services down design`; Ctrl-C voor MCP | Docker + Node.js; Penpot-plugin verbinden |
| Analytics | `make plausible` en volg uitvoer | `docker compose stop` in `services/plausible` | Alleen nuttig voor een website die je wilt meten |
| Beeldgeneratie | `make fooocus` en volg uitvoer | Sluit het gestart proces | Experimentele Apple-Silicon-route; beperkte upstreamontwikkeling |

De Docker-automatisering gebruikt CPU-modellen met eigen opslag. Op een M3-Mac is de native Ollama-kern de aanbevolen eerste route: Docker geeft deze Ollama-container geen Metal-versnelling. Zet zware modules uit wanneer je ze niet gebruikt. Geen licentiekosten betekent niet geen opslag-, energie- of onderhoudskosten.

Voor de Docker-modules: installeer en open Docker Desktop, voer `pt init` uit en start de gekozen module. Alle gepubliceerde poorten zijn beperkt tot localhost. Worker en container-Ollama hebben geen gepubliceerde poort. [n8n instellen](docs/automation.md) · [Penpot en Cursor](docs/design.md).

## macOS DMG

```bash
make dmg
open dist/Personal-Toolkit-1.0.1.dmg
```

Open de installer op de DMG. De toepassing kopieert bronbestanden naar `~/PersonalToolkit` en opent de kerninstallatie in Terminal. Bestaande `.env`, virtuele omgeving, downloads, transcripties, modellen, `services/` en andere gebruikersbestanden blijven behouden. De DMG bevat uitsluitend toegelaten bronbestanden en geen lokale gegevens. Er is geen Apple-signering/notarisatie; de macOS-CI test de bouw en inhoud, niet een interactieve installatie op jouw eigen Mac.

## Configuratie en bestaande installaties

`pt init` maakt `.env` met persoonlijke sleutels. Een vooraf gekopieerde `.env.example` wordt eveneens gecontroleerd en placeholders worden vervangen. Geldige bestaande sleutels en aangepaste instellingen blijven behouden. `.env` wordt als gegevens gelezen, zonder shell-uitvoering. Paden zijn relatief aan de toolkitmap.

**Als je al n8n/Penpot gebruikte:** maak eerst een back-up van `.env` en de Docker-volumes. De oorspronkelijke prototypeconfig gebruikte een vast Penpot-databasewachtwoord. Een nieuw `.env`-wachtwoord wijzigt geen bestaand PostgreSQL-account. Migreer dat account en de bijbehorende configuratie samen; verwijder het volume niet als oplossing. Roteer een bestaande n8n-encryptiesleutel nooit zonder een credentialmigratie. De toolkit verwijdert geen Docker-volumes.

`WHISPER_MODEL`, `OLLAMA_MODEL` en de gepinde dienstversies staan in `.env`. `faster-whisper` draait in deze kern op CPU; GPU-versnelling op Apple Silicon is hiervoor niet geïmplementeerd. Penpot en zijn MCP hebben afzonderlijke, bij elkaar passende versie-instellingen.

## Ontwikkeling

```bash
make check
make test
```

De tests gebruiken gesimuleerde modelantwoorden en lokale HTTP-servers. GitHub Actions voert ook een macOS-DMG-controle en Docker-smoketest met echte modellen uit. Kijk naar de status van de concrete commit; de aanwezigheid van een workflow betekent niet dat die al geslaagd is.

Gebruik featurebranches en een pull request. De pushhelpers herschrijven geen branchhistoriek.

## Licenties

De eigen toolkitcode is MIT. Upstreamtools en modellen hebben hun eigen licenties en gebruiksvoorwaarden. n8n is fair-code; de MIT-licentie van deze repository vervangt die voorwaarden niet.
