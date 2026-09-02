# Validatie en beperkingen

## Geautomatiseerd

- Bash/Python/JSON-syntaxis en detectie van mergeconflictmarkeringen.
- Configuratie met bestaande placeholders, idempotente sleutelgeneratie, relatieve paden en bestandstoegang.
- Transcriptie met spaties, aanhalingstekens en Unicode in bestandsnamen, zonder code-interpolatie.
- Lange transcripties, lege audio, ontbrekende/onvolledige modelantwoorden.
- Lokale HTTP-aanroep van Ollama met JSON; asynchrone worker-API met authenticatie en invoercontrole.
- Taakstatus, behoud van gedeeltelijke uitvoer en herkenning van een onderbroken taak na herstart.
- Herinstallatie en DMG-bronselectie met behoud van gebruikersbestanden en uitsluiting van lokale gegevens.
- Samenvoegen van Cursor-configuratie zonder verlies van bestaande servers.
- Dashboardconfiguratie zonder shell-uitvoering of geheime waarden; aangepaste poorten en afzonderlijke start van de dashboardmodule.
- Browserstatus: HTTP-fouten, afgeschermde antwoorden, verbindingsfouten en time-outs worden niet als succesvol weergegeven.
- Dashboardbestanden gaan mee in de installer; gegenereerde lokale dashboardconfiguratie blijft uitgesloten.

Deze regressietests gebruiken modeldoubles; ze meten geen herkenningskwaliteit of modelsnelheid.

## GitHub Actions

De workflow bevat tests op Linux en macOS, een native DMG-build met een pad met spaties, inhoudscontrole, Compose-validatie, een worker-imagebuild en een echte transcriptie/samenvattingssmoketest. De smoketest gebruikt Whisper tiny en het standaardtaalmodel llama3.2:3b; dit is geen kwaliteitsbenchmark. CI mag alleen als geslaagd worden gerapporteerd als de run van de betreffende commit daadwerkelijk groen is.

## Nog op een gebruikersmachine te controleren

- Interactieve eerste installatie en herinstallatie op de eigen M3-Mac, inclusief Homebrew, eventuele OS-meldingen en Docker Desktop.
- Nederlandse transcriptie- en samenvattingskwaliteit, brongetrouwheid, verwerkingstijd en geheugengebruik op representatieve opnames.
- n8n-workflow na het selecteren van lokale credentials, met een echte video-URL.
- Penpot/MCP/Cursor met een geopend ontwerp en verbonden plugin.
- Fooocus/MPS en Plausible als die optionele modules daadwerkelijk worden gebruikt.

Er worden geen echte bank- of klantgegevens in tests gebruikt.
