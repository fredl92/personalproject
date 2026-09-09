import sys
from pathlib import Path
from personal_toolkit.config import Settings, atomic_write

settings = Settings()
settings.validate(("PLAUSIBLE_SECRET_KEY_BASE",))
destination = Path(sys.argv[1])
path = destination / ".env"
if not path.exists():
    atomic_write(path, "BASE_URL=http://localhost:8000\nSECRET_KEY_BASE=" + settings.get("PLAUSIBLE_SECRET_KEY_BASE") + "\nHTTP_PORT=8000\nDISABLE_REGISTRATION=invite_only\n")
override = destination / "compose.override.yml"
if not override.exists():
    atomic_write(override, 'services:\n  plausible:\n    ports: ["127.0.0.1:8000:8000"]\n')
print("Existing Plausible configuration preserved; new installs are bound to localhost.")
