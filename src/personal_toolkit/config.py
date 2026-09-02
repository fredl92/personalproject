"""Configuration is data, never executable shell code."""
import os
import re
import secrets
import tempfile
from pathlib import Path

SECRET_KEYS = ("N8N_ENCRYPTION_KEY", "PENPOT_SECRET_KEY", "WORKER_API_TOKEN",
               "PENPOT_DATABASE_PASSWORD", "PLAUSIBLE_SECRET_KEY_BASE")
DEFAULTS = {
    "DASHBOARD_HOST": "localhost", "DASHBOARD_PORT": "8080", "FOOOCUS_PORT": "7865",
    "PLAUSIBLE_BASE_URL": "http://localhost:8000",
    "N8N_VERSION": "2.37.7", "PENPOT_VERSION": "2.17.2", "PENPOT_MCP_VERSION": "2.17.0", "OLLAMA_VERSION": "0.33.2",
    "N8N_PORT": "5678", "PENPOT_PORT": "9001", "OLLAMA_MODEL": "llama3.2:3b",
    "OLLAMA_URL": "http://127.0.0.1:11434", "WHISPER_MODEL": "base",
    "WHISPER_DEVICE": "cpu", "WHISPER_COMPUTE_TYPE": "int8",
    "DOWNLOAD_DIR": "./downloads", "TRANSCRIPTS_DIR": "./transcripts",
    "JOBS_DIR": "./data/jobs", "WHISPER_CACHE_DIR": "./data/whisper-cache", "TZ": "Europe/Brussels",
}


def read_env(path):
    values = {}
    if not path.exists():
        return values
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"Invalid configuration on {path.name}:{number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def atomic_write(path, text, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(text)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def placeholder(value):
    normalized = value.lower().replace("-", "").replace("_", "")
    return not value or "changeme" in normalized or "yourtoken" in normalized


class Settings:
    def __init__(self, root=None, environ=None):
        env = os.environ if environ is None else environ
        self.root = Path(root or env.get("PERSONAL_TOOLKIT_HOME") or
                         Path(__file__).resolve().parents[2]).resolve()
        self.values = {**DEFAULTS, **read_env(self.root / ".env")}
        for key in set(self.values) | set(SECRET_KEYS):
            if key in env:
                self.values[key] = env[key]

    def get(self, key):
        return self.values.get(key, "")

    def path(self, key):
        value = Path(self.get(key)).expanduser()
        return value.resolve() if value.is_absolute() else (self.root / value).resolve()

    def validate(self, keys=SECRET_KEYS):
        invalid = [key for key in keys if placeholder(self.get(key)) or len(self.get(key)) < 32]
        if invalid:
            raise ValueError("Missing or placeholder secrets: " + ", ".join(invalid) +
                             ". Run pt init before starting services.")


def initialize(root):
    """Repair placeholders, preserving real secrets and existing user settings."""
    root = Path(root)
    path = root / ".env"
    source = path if path.exists() else root / ".env.example"
    text = source.read_text(encoding="utf-8")
    values = read_env(source)
    changed = []
    for key in SECRET_KEYS:
        if placeholder(values.get(key, "")):
            value = secrets.token_hex(32)
            pattern = rf"^{re.escape(key)}=.*$"
            text = re.sub(pattern, f"{key}={value}", text, flags=re.MULTILINE) if key in values else text.rstrip() + f"\n{key}={value}\n"
            changed.append(key)
    for key, value in DEFAULTS.items():
        if key not in values:
            text = text.rstrip() + f"\n{key}={value}\n"
    atomic_write(path, text)
    return changed
