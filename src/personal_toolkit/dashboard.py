"""Generate public dashboard settings; never expose secrets or evaluate .env."""
import json
from urllib.parse import urlsplit

from .config import atomic_write


def port(settings, key):
    value = settings.get(key)
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise ValueError(f"{key} must be a port between 1 and 65535.")
    return int(value)


def public_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.query or parsed.fragment or any(c.isspace() for c in value)):
        raise ValueError("Dashboard URLs must be HTTP(S), without credentials, query or fragment.")
    # Accessing .port also rejects malformed and out-of-range ports.
    if parsed.port == 0:
        raise ValueError("Dashboard URLs cannot use port 0.")
    return value.rstrip("/")


def configuration(settings):
    host = settings.get("DASHBOARD_HOST")
    if host not in ("localhost", "127.0.0.1"):
        raise ValueError("DASHBOARD_HOST must be localhost or 127.0.0.1; services bind locally.")
    apps = {}
    for name, key in (("dashboard", "DASHBOARD_PORT"), ("n8n", "N8N_PORT"),
                      ("penpot", "PENPOT_PORT"), ("fooocus", "FOOOCUS_PORT")):
        apps[name] = {"url": f"http://{host}:{port(settings, key)}",
                      "optional": name != "dashboard"}
    apps["n8n"]["healthUrl"] = apps["n8n"]["url"] + "/healthz"
    apps["plausible"] = {"url": public_url(settings.get("PLAUSIBLE_BASE_URL")), "optional": True}
    apps["ollama"] = {"url": public_url(settings.get("OLLAMA_URL")), "optional": False}
    apps["ollama"]["healthUrl"] = apps["ollama"]["url"] + "/api/tags"
    return {"apps": apps}


def render(settings):
    config = configuration(settings)
    # Public, allowlisted values only; nginx must be able to read this file.
    atomic_write(settings.root / "dashboard/config.js",
                 "window.DASHBOARD_CONFIG = " + json.dumps(config, ensure_ascii=True) + ";\n",
                 mode=0o644)
    return config["apps"]["dashboard"]["url"]
