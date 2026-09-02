# n8n: video → transcript → Nederlandse samenvatting

1. Installeer/start Docker Desktop. Voer `pt init` en `pt services up automation` uit. De tweede opdracht bouwt de worker, wacht op de diensten en haalt het ingestelde Ollama-model op. Er draait slechts één verwerking tegelijk; maximaal twintig taken kunnen actief/in de wachtrij staan.
2. Open http://localhost:5678 en maak het lokale n8n-eigenaarsaccount aan. De oude `N8N_BASIC_AUTH_*`-instellingen worden niet gebruikt.
3. Maak één **Header Auth**-credential in n8n: naam van de header `X-Toolkit-Token`; waarde: de `WORKER_API_TOKEN` uit jouw lokale `.env`. Deel die waarde niet in chat, GitHub of een workflowexport.
4. Importeer `workflows/n8n/download-transcribe-summarize.json`. Selecteer die credential bij **Submit job** en **Read status**.
5. Vul de video-URL in bij **Video URL** en voer de workflow uit.

De workflow gebruikt HTTP, geen Execute Command-node. De worker heeft yt-dlp, ffmpeg en faster-whisper geïnstalleerd en schrijft naar `data/jobs/`. n8n hoeft geen hostcommando's uit te voeren en krijgt geen toegang tot de modellen of opnamemappen.

Status wordt elke tien seconden opgehaald. Bij succes toont **Result** de samenvatting en de uitvoermap. Bij een mislukte download, transcriptie of modelaanroep toont **Report failure** de fout. Een herstart markeert onafgewerkte taken als onderbroken; bestaande bestanden blijven bewaard. Dien de taak opnieuw in of gebruik het bewaarde transcript met `pt summarize`.

De workflow stopt na vier uur; uitzonderlijk lange verwerkingen kunnen dan nog verder lopen in de worker. Hun status en uitvoer blijven in `data/jobs/<id>/job.json` staan. Stoppen van een module verwijdert geen taken of volumes.

## Handige controles

```bash
pt services status automation
pt services logs automation
pt job JOB_ID
pt services down automation
```

De Docker-Ollama heeft een andere modelopslag dan de native Ollama op je Mac. Verander je `OLLAMA_MODEL`, voer dan opnieuw `pt services up automation` uit om dat model op te halen. Docker gebruikt hier CPU, geen Apple Metal.

Gebruik voor een eerste praktijktest een korte, publiek bereikbare video. Beschikbaarheid/authenticatie van externe videosites is niet gegarandeerd. De CI test een gecontroleerd audiobestand; de kwaliteit van Nederlandse samenvattingen moet je op representatieve opnames controleren.
