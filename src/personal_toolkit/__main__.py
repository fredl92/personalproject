import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

from .config import Settings, atomic_write, initialize
from .dashboard import configuration, render as render_dashboard
from .jobs import JobStore
from .pipeline import download, generate, summarize, transcribe


def compose(settings, arguments):
    env = {**os.environ, **settings.values, "TOOLKIT_UID": str(os.getuid()), "TOOLKIT_GID": str(os.getgid())}
    subprocess.run(["docker", "compose", "--project-directory", str(settings.root),
                    "--env-file", str(settings.root / ".env"), *arguments],
                   cwd=settings.root, env=env, check=True)


def model_installed(models, wanted):
    names = []
    if isinstance(models, list):
        for item in models:
            if isinstance(item, dict):
                names.extend([item.get("name") or "", item.get("model") or ""])
            elif isinstance(item, str):
                names.append(item)
    wanted = (wanted or "").strip()
    return bool(wanted) and any(name == wanted for name in names)


def doctor(settings):
    checks = [("Python >= 3.10", sys.version_info >= (3, 10), "Install Python 3.10 or newer."),
              ("yt-dlp", shutil.which("yt-dlp") is not None, "Run make setup to install Python packages."),
              ("ffmpeg", shutil.which("ffmpeg") is not None, "Install ffmpeg (brew or apt), then rerun make setup."),
              ("faster-whisper", importlib.util.find_spec("faster_whisper") is not None,
               "Run make setup to install Python packages.")]
    try:
        with urllib.request.urlopen(settings.get("OLLAMA_URL").rstrip("/") + "/api/tags", timeout=5) as response:
            payload = json.load(response)
        models = payload.get("models", []) if isinstance(payload, dict) else []
        wanted = settings.get("OLLAMA_MODEL")
        checks.append(("Ollama reachable", True, ""))
        checks.append(("Ollama model " + wanted, model_installed(models, wanted),
                       "Start Ollama and run: ollama pull " + wanted))
    except Exception:
        checks.append(("Ollama reachable", False, "Start Ollama (brew services start ollama) and run pt doctor again."))
    for name, passed, hint in checks:
        print(("OK   " if passed else "FAIL ") + name)
        if not passed and hint:
            print("      " + hint)
    print("Docker and Node.js are optional: needed only for automation/design.")
    print("Recent jobs: pt jobs")
    return 0 if all(passed for _, passed, _ in checks) else 1


def print_jobs(jobs):
    if not jobs:
        print("No jobs yet. Run: pt pipeline <url-or-file>")
        return
    for job in jobs:
        source = str(job.get("source") or "")
        if len(source) > 80:
            source = source[:77] + "..."
        print(f"{job.get('id', '')[:8]}  {str(job.get('status') or '?'):<10}  {source}")
        if job.get("status") == "failed" and job.get("error"):
            print("           " + str(job["error"]).splitlines()[0][:120])
        elif job.get("status") == "succeeded" and isinstance(job.get("result"), dict) and job["result"].get("summary"):
            print("           " + str(job["result"]["summary"]))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pt", description="Personal Toolkit — lokale transcriptie en Nederlandse samenvattingen")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "doctor", "urls", "install", "mcp", "worker", "model", "dashboard-config"):
        sub.add_parser(command)
    dashboard = sub.add_parser("dashboard", aliases=["dash"], help="Start only the dashboard and open it")
    dashboard.add_argument("--no-open", action="store_true", help="Start without opening a browser")
    config = sub.add_parser("cursor-config", help="Merge the local Penpot MCP endpoint into a project's Cursor config")
    config.add_argument("project", type=Path)
    dl = sub.add_parser("download")
    dl.add_argument("url")
    dl.add_argument("--audio", action="store_true")
    tx = sub.add_parser("transcribe")
    tx.add_argument("file", type=Path)
    pipe = sub.add_parser("pipeline")
    pipe.add_argument("source", help="Video URL or local media file")
    ask = sub.add_parser("ask")
    ask.add_argument("prompt")
    ask.add_argument("model", nargs="?")
    summ = sub.add_parser("summarize")
    summ.add_argument("transcript", type=Path)
    listing = sub.add_parser("jobs", help="List recent download/transcript jobs")
    listing.add_argument("-n", "--limit", type=int, default=20)
    status = sub.add_parser("job")
    status.add_argument("id")
    svc = sub.add_parser("services")
    svc.add_argument("action", choices=("up", "down", "logs", "status"), default="status", nargs="?")
    svc.add_argument("module", choices=("dashboard", "automation", "design"), nargs="?")
    args = parser.parse_args(argv)
    settings = Settings()
    try:
        if args.command == "init":
            changes = initialize(settings.root)
            print("Configuration ready; generated/repaired keys: " + (", ".join(changes) or "none"))
            print("Existing custom values preserved. Secret values were not printed.")
        elif args.command == "model":
            print(settings.get("OLLAMA_MODEL"))
        elif args.command == "install":
            subprocess.run(["bash", str(settings.root / "scripts/install-cli.sh")], check=True)
        elif args.command == "doctor":
            return doctor(settings)
        elif args.command == "urls":
            apps = configuration(settings)["apps"]
            print("Dashboard (pt dashboard): " + apps["dashboard"]["url"])
            print(f"n8n (automation): http://localhost:{settings.get('N8N_PORT')}")
            print(f"Penpot (design): http://localhost:{settings.get('PENPOT_PORT')}")
            print("Penpot MCP (pt mcp): http://localhost:4401/mcp")
            print("Plausible (optional): " + apps["plausible"]["url"])
            print("Ollama (native CLI): " + apps["ollama"]["url"])
            print("Fooocus (optional): " + apps["fooocus"]["url"])
        elif args.command == "dashboard-config":
            print("Dashboard configuration ready: " + render_dashboard(settings))
        elif args.command in ("dashboard", "dash"):
            settings.validate()
            url = render_dashboard(settings)
            compose(settings, ["--profile", "dashboard", "up", "-d", "--wait", "--wait-timeout", "60"])
            print("Startdashboard: " + url)
            if not args.no_open:
                import webbrowser
                if not webbrowser.open(url):
                    print("Open the URL above in your browser.")
        elif args.command == "download":
            print(download(args.url, settings.path("DOWNLOAD_DIR"), audio=args.audio, settings=settings))
        elif args.command == "transcribe":
            source = args.file.expanduser()
            target = settings.path("TRANSCRIPTS_DIR") / (source.stem + "-" + uuid.uuid4().hex[:8] + ".txt")
            transcribe(source, target, settings)
            print(target)
        elif args.command == "summarize":
            transcript = args.transcript.expanduser()
            result = summarize(transcript.read_text(encoding="utf-8"), settings)
            target = transcript.with_name(transcript.stem + "-summary.md")
            atomic_write(target, result + "\n")
            print(result + "\n\nSaved: " + str(target))
        elif args.command == "ask":
            if args.model:
                settings.values["OLLAMA_MODEL"] = args.model
            print(generate(args.prompt, settings, "Beantwoord deze vraag in het Nederlands.",
                           system="Je bent een behulpzame assistent. Benoem onzekerheid en verzin geen feiten."))
        elif args.command == "pipeline":
            jobs = JobStore(settings.path("JOBS_DIR"))
            job = jobs.create(args.source)
            print("Job: " + job["id"], flush=True)
            result = jobs.execute(job["id"], settings, report=lambda stage: print(stage + "...", flush=True))
            if result["status"] == "failed":
                raise RuntimeError(result["error"])
            print(result["result"]["summary_text"])
            print("Saved: " + str(jobs.folder(job["id"])))
        elif args.command == "jobs":
            print_jobs(JobStore(settings.path("JOBS_DIR")).list(args.limit))
        elif args.command == "job":
            print(json.dumps(JobStore(settings.path("JOBS_DIR")).get(args.id), ensure_ascii=False, indent=2))
        elif args.command == "services":
            settings.validate()
            if args.action == "up" and not args.module:
                raise ValueError("Choose a module: pt services up dashboard, automation OR design")
            profile = args.module or "*"
            for key in ("JOBS_DIR", "WHISPER_CACHE_DIR"):
                settings.path(key).mkdir(parents=True, exist_ok=True)
            if args.action == "up":
                if args.module == "dashboard":
                    render_dashboard(settings)
                compose(settings, ["--profile", profile, "up", "-d", "--build", "--wait", "--wait-timeout", "180"])
                if args.module == "automation":
                    compose(settings, ["exec", "-T", "ollama", "ollama", "pull", settings.get("OLLAMA_MODEL")])
            else:
                services = {"dashboard": ["dashboard"], "automation": ["n8n", "pipeline-worker", "ollama"],
                            "design": ["penpot-frontend", "penpot-backend", "penpot-exporter", "penpot-postgres", "penpot-valkey"]}
                action = {"down": ["stop"], "logs": ["logs", "-f"], "status": ["ps", "-a"]}[args.action]
                compose(settings, ["--profile", profile, *action, *services.get(args.module, [])])
        elif args.command == "mcp":
            version = settings.get("PENPOT_MCP_VERSION")
            import re
            if not re.fullmatch(r"\d+\.\d+\.\d+", version):
                raise ValueError("Set PENPOT_MCP_VERSION to an exact release, e.g. 2.17.0.")
            if version.split(".")[:2] != settings.get("PENPOT_VERSION").split(".")[:2]:
                raise ValueError("Penpot and MCP release series differ; review docs/design.md before upgrading.")
            subprocess.run(["npx", "-y", "@penpot/mcp@" + version], check=True)
        elif args.command == "cursor-config":
            path = args.project.expanduser().resolve() / ".cursor/mcp.json"
            existing = json.loads(path.read_text()) if path.exists() else {}
            servers = existing.setdefault("mcpServers", {})
            endpoint = {"url": "http://localhost:4401/mcp"}
            if "penpot" in servers and servers["penpot"] != endpoint:
                raise ValueError("An existing Penpot configuration differs; review it before replacement.")
            servers["penpot"] = endpoint
            atomic_write(path, json.dumps(existing, indent=2) + "\n")
            print(f"Configured {path}. Run pt mcp and connect the Penpot plugin (see docs/design.md).")
        elif args.command == "worker":
            from .worker import serve
            serve(settings)
        return 0
    except (ValueError, RuntimeError, OSError, ImportError, subprocess.SubprocessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
