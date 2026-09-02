# Penpot met Cursor

De oude afzonderlijke penpot-mcp-repository is gearchiveerd. De officiële code staat in https://github.com/penpot/penpot/tree/develop/mcp.

De gekozen Penpot-release is **2.17.2**. Het MCP-package in die release vermeldt **2.17.0**: daarom zijn `PENPOT_VERSION` en `PENPOT_MCP_VERSION` afzonderlijk gepind. Bij upgrades controleer je de officiële compatibiliteit; `pt mcp` weigert verschillende major/minor-reeksen.

1. Installeer Node.js (getest upstream met versie 22) en Docker Desktop wanneer die ontbreken. Op een Mac met Homebrew kan Node via `brew install node@22`; zorg dat `node` en `npx` in je PATH staan.
2. Voer `pt services up design` uit. Open http://localhost:9001 en maak/open een ontwerp.
3. Start `pt mcp` in een apart Terminal-venster. Dit start het officiële `@penpot/mcp`-package en de bijbehorende pluginserver.
4. Open het Plugins-menu in Penpot en voeg `http://localhost:4400/manifest.json` toe. Open de plugin en kies **Connect to MCP server**. Laat de plugin en het ontwerp geopend.
5. Voer bijvoorbeeld `pt cursor-config ~/auraxis` uit. Dit voegt de endpoint http://localhost:4401/mcp toe aan `.cursor/mcp.json`, met behoud van andere servers. Bij een afwijkende bestaande Penpot-config stopt de opdracht zodat die niet stilzwijgend wordt overschreven.
6. Controleer de Penpot-verbinding in Cursor. Test eerst met een eenvoudig ontwerp in een testbestand.

De voorbeeldconfig bevat geen token en geen fictief API-package. MCP communiceert met de geopende Penpot-plugin; enkel een Penpot-container starten is onvoldoende.

Stop met Ctrl-C in het MCP-venster en `pt services down design`. Deze setup is lokaal. Remote samenwerking, TLS en multi-user MCP vallen buiten deze versie.
