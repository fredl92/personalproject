# Personal Toolkit

Lokale transcripties en Nederlandse samenvattingen, met optionele modules voor automatisering, ontwerp, analytics en beeldgeneratie.

**Status:** 1.0.4. Zie [validatie](docs/validation.md) voor wat automatisch getest wordt en wat nog een praktijktest vereist. Lokale modellen zijn geen garantie op correcte samenvattingen of gelijkwaardige kwaliteit aan een clouddienst.

## Begin klein: de lokale kern

Benodigd: macOS op Apple Silicon met Homebrew, of Linux met Python 3.10+, ffmpeg en Ollama. Voor de Mac-installer wordt Homebrew Python 3.12 gebruikt. Docker is niet nodig voor de kern.

```bash
make setup
# In ditzelfde venster werkt `pt` al. Andere vensters: nieuw Terminal-venster,
# of de export PATH-regel die de installer toont.
pt doctor
pt pipeline "/pad/naar/opname met spaties.wav"
pt pipeline "https://www.youtube.com/watch?v=VIDEO_ID"
pt jobs
pt retry JOB_ID
```

`make setup` installeert de Python-pakketten, initialiseert `.env`, zet `pt` in je PATH, start Ollama op macOS en downloadt het ingestelde model. Op Linux moet Ollama vooraf geïnstalleerd en gestart zijn. Fouten stoppen de installatie met een foutcode; er volgt geen onterechte succesmelding. `pt doctor` keurt de kern (Python, ffmpeg, Whisper, Ollama + model). Ontbrekende PATH of Docker is een toelichting, geen kernfout: Docker is alleen nodig voor het dashboard en optionele modules. Onderbroken lokale taken (Ctrl-C of een gestopt proces) worden bij `pt doctor` / `pt jobs` als mislukt gemarkeerd.

Elke pipeline maakt een unieke map `data/jobs/<id>/` met `job.json`, een transcript met tijdsaanduidingen, segmenten in JSON en een Nederlandse `summary.md` (kernpunten, beslissingen, open punten). Lange transcripties worden in delen samengevat en daarna samengevoegd; ontbrekende koppen worden aangevuld. Controleer belangrijke uitspraken steeds in het transcript. Bij een fout of onderbreking blijft reeds geproduceerde uitvoer bewaard. `pt jobs` toont status, stadium en tijd; `pt job` geeft een leesbaar overzicht (`--json` voor machines). `pt retry JOB_ID` hervat vanaf een bewaard transcript of gedownloade audio, zonder die stappen te herhalen. Een lokaal `file://`-pad mag bij `pt pipeline` / `pt transcribe`.

Standaard gebruikt Whisper Nederlands (`WHISPER_LANGUAGE=nl`). Zet de waarde leeg voor automatische herkenning, of `en` voor Engelstalige opnames. Downloads voor de pipeline worden als m4a-audio bewaard. Als YouTube een login vraagt, zet dan `YTDLP_COOKIES_FROM_BROWSER=chrome` (of `safari`, `firefox`, …) in `.env`.

```bash
pt download "https://example.org/video" --audio
pt transcribe "opname.wav"
pt summarize "transcript.txt"
pt ask "Leg obligatieduration eenvoudig uit"
pt jobs
pt job JOB_ID
pt retry JOB_ID
```

## Kies modules wanneer je ze nodig hebt

### Startdashboard

Met Docker Desktop geopend:

```bash
pt init
pt dashboard
# Of: make up en open http://localhost:8080
```

Het dashboard begint met vier taken: samenvatten, uitschrijven, downloaden en een vraag stellen. Vul je vraag, videolink of volledig bestandspad in en klik op **Maak mijn commando** (of ⌘ + Enter). Kopieer de gemaakte opdracht naar Terminal en druk op Enter. De browser voert geen opdrachten uit en bewaart je invoer niet. Bij een bestand gebruik je het volledige pad uit Finder (⌥ + ⌘ + C); er is geen upload. De AI-kaart toont het ingestelde Ollama- en Whisper-model.

Bij elke app vind je **Openen** en gerichte **Hulp bij starten**. Extra tools en technische adressen staan ingeklapt. Kopiëren geeft directe bevestiging, met een handmatige uitweg als de browser het klembord blokkeert. Alleen het dashboard wordt gestart; kies de andere modules hieronder wanneer nodig. `pt dashboard --no-open` start zonder een browser te openen. `DASHBOARD_PORT` wijzigt de poort; de binding blijft beperkt tot localhost. Stop met `pt services down dashboard`.

“Bereikbaar” bevestigt een HTTP-antwoord via het dashboard (localhost-proxy), niet via cross-origin. HTTP 502/504 blijven “Niet bevestigd”. Voor Ollama kan de modellijst “Model klaar” of “Model ontbreekt” tonen; dat zegt niets over antwoordkwaliteit. Sommige apps zonder draaiende container blijven onbevestigd. Gebruik dan Openen, de starthulp of `pt doctor`. De Ollama-kaart verwijst naar de native CLI-server, niet naar de interne Docker-server.

De openbare `dashboard/config.js` wordt uit toegelaten instellingen opgebouwd, zonder sleutels of shell-uitvoering. Na configuratiewijzigingen voer je opnieuw `pt dashboard` uit. Een ontbrekend configuratiebestand wordt zichtbaar gemeld.

| Module | Start | Stop | Opmerking |
|---|---|---|---|
| Dashboard | `pt dashboard` | `pt services down dashboard` | Docker; start geen modellen of andere apps |
| Automatisering | `pt services up automation` | `pt services down automation` | Docker: n8n, verwerkingsdienst en aparte Ollama |
| Ontwerp | `pt services up design`, daarna `pt mcp` | `pt services down design`; Ctrl-C voor MCP | Docker + Node.js; Penpot-plugin verbinden |
| Analytics | `make plausible` en volg uitvoer | `docker compose stop` in `services/plausible` | Alleen nuttig voor een website die je wilt meten |
| Beeldgeneratie | `make fooocus` en volg uitvoer | Sluit het gestart proces | Experimentele Apple-Silicon-route; beperkte upstreamontwikkeling |

De Docker-automatisering gebruikt CPU-modellen met eigen opslag. Op een M3-Mac is de native Ollama-kern de aanbevolen eerste route: Docker geeft deze Ollama-container geen Metal-versnelling. Zet zware modules uit wanneer je ze niet gebruikt. Geen licentiekosten betekent niet geen opslag-, energie- of onderhoudskosten.

Voor de Docker-modules: installeer en open Docker Desktop, voer `pt init` uit en start de gekozen module. Alle gepubliceerde poorten zijn beperkt tot localhost. Worker en container-Ollama hebben geen gepubliceerde poort. [n8n instellen](docs/automation.md) · [Penpot en Cursor](docs/design.md) · [Plausible en Fooocus](docs/optional.md).

## macOS DMG

```bash
make dmg
open dist/Personal-Toolkit-1.0.4.dmg
```

Open de installer op de DMG. De toepassing kopieert bronbestanden naar `~/PersonalToolkit` en opent de kerninstallatie in Terminal. Bestaande `.env`, virtuele omgeving, downloads, transcripties, modellen, `services/` en andere gebruikersbestanden blijven behouden. De DMG bevat uitsluitend toegelaten bronbestanden en geen lokale gegevens. Er is geen Apple-signering/notarisatie; de macOS-CI test de bouw en inhoud, niet een interactieve installatie op jouw eigen Mac.

## Configuratie en bestaande installaties

`pt init` maakt `.env` met persoonlijke sleutels. Een vooraf gekopieerde `.env.example` wordt eveneens gecontroleerd en placeholders worden vervangen. Geldige bestaande sleutels en aangepaste instellingen blijven behouden. `.env` wordt als gegevens gelezen, zonder shell-uitvoering. Paden zijn relatief aan de toolkitmap.

**Als je al n8n/Penpot gebruikte:** maak eerst een back-up van `.env` en de Docker-volumes. De oorspronkelijke prototypeconfig gebruikte een vast Penpot-databasewachtwoord. Een nieuw `.env`-wachtwoord wijzigt geen bestaand PostgreSQL-account. Migreer dat account en de bijbehorende configuratie samen; verwijder het volume niet als oplossing. Roteer een bestaande n8n-encryptiesleutel nooit zonder een credentialmigratie. De toolkit verwijdert geen Docker-volumes.

`WHISPER_MODEL`, `WHISPER_LANGUAGE`, `OLLAMA_MODEL` en de gepinde dienstversies staan in `.env`. `faster-whisper` draait op CPU (`WHISPER_DEVICE=cpu`, `WHISPER_COMPUTE_TYPE=int8`). Op Apple Silicon gebruikt CTranslate2 Accelerate; een Metal-GPU-pad bestaat in deze kern niet — zet `cuda` niet op een Mac. Gewichten landen in `WHISPER_CACHE_DIR` (`data/whisper-cache/`), ook in de Docker-worker. Optioneel: `WHISPER_CPU_THREADS` (1–32) als de automatische threadkeuze tegenvallt. Penpot en zijn MCP hebben afzonderlijke, bij elkaar passende versie-instellingen.

## Ontwikkeling

```bash
make check
make test
make test-dashboard # Node.js 22+ voor de dashboardtests
```

De tests gebruiken gesimuleerde modelantwoorden en lokale HTTP-servers. GitHub Actions voert ook een macOS-DMG-controle en Docker-smoketest met echte modellen uit. Kijk naar de status van de concrete commit; de aanwezigheid van een workflow betekent niet dat die al geslaagd is.

Gebruik featurebranches en een pull request. De pushhelpers herschrijven geen branchhistoriek.

## Licenties

De eigen toolkitcode is MIT. Upstreamtools en modellen hebben hun eigen licenties en gebruiksvoorwaarden. n8n is fair-code; de MIT-licentie van deze repository vervangt die voorwaarden niet.
