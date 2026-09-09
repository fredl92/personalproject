# Validatie en beperkingen

## Geautomatiseerd

- Bash/Python/JSON-syntaxis en detectie van mergeconflictmarkeringen.
- Configuratie met bestaande placeholders, idempotente sleutelgeneratie, relatieve paden en bestandstoegang.
- Transcriptie met spaties, aanhalingstekens en Unicode in bestandsnamen, zonder code-interpolatie. Standaardtaal Nederlands, met auto-detectie wanneer `WHISPER_LANGUAGE` leeg is.
- Whisper-cache in `WHISPER_CACHE_DIR` (ook in de automation-worker). `WHISPER_DEVICE=cuda` wordt op macOS geweigerd; er is geen Metal-GPU-pad.
- Lange transcripties, lege audio, ontbrekende/onvolledige modelantwoorden. Tijdelijke Ollama-netwerkfouten worden beperkt opnieuw geprobeerd; HTTP-clientfouten niet.
- Downloadfouten tonen de laatste yt-dlp-regel in plaats van alleen een exitcode. Audio-extractie naar m4a; optionele, toegelaten browsercookies.
- Taakstatus, overzicht via `pt jobs` (stadium en tijd), leesbare `pt job` (met `--json`), ID-prefix, behoud van gedeeltelijke uitvoer en herkenning van een onderbroken lokale taak (Ctrl-C of dood proces). `pt retry` hervat vanaf transcript of bruikbare media; lege, corrupte of `.part`-bestanden worden niet hergebruikt. Twee processen kunnen dezelfde taak niet tegelijk hervatten. Worker-herstart blijft onafgewerkte worker-taken falen; corrupte `job.json` laat de worker niet crashen.
- Samenvattingen: vaste Nederlandse koppen, lege bullets worden `geen`, aparte samenvoeginstructie bij lange opnames, HTTP 500 van Ollama wordt beperkt opnieuw geprobeerd. Lange Whisper/Ollama-runs tonen tussentijdse stadia of een heartbeat. Lokale `file://`-paden voor pipeline/transcriptie.
- Lokale HTTP-aanroep van Ollama met JSON; asynchrone worker-API met authenticatie en invoercontrole.
- Herinstallatie en DMG-bronselectie met behoud van gebruikersbestanden en uitsluiting van lokale gegevens, inclusief gegenereerde dashboard-proxyconfig.
- Samenvoegen van Cursor-configuratie zonder verlies van bestaande servers.
- Dashboardconfiguratie zonder shell-uitvoering of geheime waarden; publieke modelnamen; aangepaste poorten en afzonderlijke start van de dashboardmodule.
- Statuscontroles via same-origin nginx-proxy naar localhost (geen secrets). HTTP-fouten, 502/504, afgeschermde antwoorden, verbindingsfouten en time-outs worden niet als succesvol weergegeven. Een Ollama-modellijst kan “Model klaar” of “Model ontbreekt” tonen; dat is geen kwaliteitsclaim.
- Taakcommando's: echte shell-parsing van vragen en bestandsnamen met quotes, spaties, Unicode en shelltekens; videolinks met queryparameters, audioselectie, thuismappen en ongeldige invoer. PATH-registratie zonder bestaande shellconfig te overschrijven.
- `pt doctor`: onderscheid tussen Ollama uit versus model ontbreekt; PATH- en Docker-hints zonder de kern ten onrechte af te keuren.
- Plausible-voorbereiding bindt aan localhost en drukt geen geheimen af. Dashboardbestanden gaan mee in de installer; gegenereerde lokale dashboardconfiguratie blijft uitgesloten.

Deze regressietests gebruiken modeldoubles; ze meten geen herkenningskwaliteit of modelsnelheid.

## GitHub Actions

De workflow bevat tests op Linux en macOS, een native DMG-build met een pad met spaties, inhoudscontrole, Compose-validatie, een worker-imagebuild en een echte transcriptie/samenvattingssmoketest. De smoketest gebruikt Whisper tiny en het standaardtaalmodel llama3.2:3b; dit is geen kwaliteitsbenchmark. Het apt-installeren van testdependenties probeert storende third-party Chrome/Microsoft-bronnen te omzeilen als `apt-get update` faalt. CI mag alleen als geslaagd worden gerapporteerd als de run van de betreffende commit daadwerkelijk groen is.

## Praktijktest op je M3-Mac

Doe dit op een echte machine na installatie of upgrade. CI vervangt deze stappen niet.

1. **Installer / PATH.** Na `make setup` of de DMG-installer: in het installatievenster `pt doctor` (moet de kern op OK zetten). Open daarna een **nieuw** Terminal-venster en voer `which pt` en `pt doctor` uit. Verwacht: `pt` wijst naar `~/PersonalToolkit/bin/pt` (of je clonemap). Zo niet: de `export PATH=…`-regel uit de installer-uitvoer plakken, of een nieuw venster na het sourcen van `~/.zshrc`.
2. **Ollama versus Docker.** `pt doctor` moet “Ollama reachable” en het ingestelde model tonen. Dat is de **native** CLI-server, niet de Ollama-container van automation. Docker mag als NOTE ontbreken; de kern werkt dan nog. Voor het dashboard: Docker Desktop starten, daarna `pt dashboard`.
3. **Korte pipeline.** `pt pipeline "/pad/naar/korte-opname.wav"` (Nederlandse spraak, een minuut is genoeg). Verwacht: map `data/jobs/<id>/` met `transcript.txt`, `transcript.json` en `summary.md` met de koppen Kernpunten / Beslissingen / Open punten. Controleer of kernpunten kloppen; lokale modellen zijn geen garantie. Let op duur en geheugen; Terminal mag `transcribing …` / `summarizing 1/1` en eventueel een Ollama-heartbeat op stderr tonen. Eerste Whisper-run downloadt gewichten naar `data/whisper-cache/`. Optioneel: onderbreek met Ctrl-C tijdens samenvatten, daarna `pt jobs` en `pt retry <id>` — transcriptie mag niet overnieuw. Tweede optionele check: onderbreek tijdens downloaden; `pt retry` mag geen lege/corrupte media hergebruiken.
4. **Dashboard.** `pt dashboard` → http://localhost:8080. Maak een commando (vraag met apostrof, pad met spaties) en plak het in Terminal. Op Linux: padhulp zonder Finder-sneltoets; Ctrl+Enter maakt het commando. AI-kaart: bij draaiende Ollama bij voorkeur “Model klaar”, niet alleen een groene aanname. Start n8n/Penpot niet per ongeluk via Openen als die containers uit staan; verwacht “Niet bevestigd” of een foutpagina, geen crash van het dashboard.
5. **n8n (optioneel).** Volg [automation.md](automation.md) met een korte publieke video-URL en de Header Auth-credential uit jouw `.env`. Geen echte klant- of bankdata. CI importeert de workflow maar voert geen echte download van YouTube uit.
6. **Penpot/MCP (optioneel).** Volg [design.md](design.md) met een testdocument en de plugin. `pt cursor-config` op een wegwerpproject.
7. **Plausible/Fooocus (optioneel).** Alleen als je die modules wilt gebruiken; zie [optional.md](optional.md). Geen echte productiesite of cloudaccount in deze test.

Er worden geen echte bank- of klantgegevens in tests gebruikt.
