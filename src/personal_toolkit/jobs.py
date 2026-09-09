import datetime
import json
import os
import re
import threading
import uuid
from pathlib import Path

from .config import atomic_write
from .pipeline import run_pipeline


def pid_running(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class JobStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def folder(self, job_id):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("Invalid job ID")
        return self.directory / job_id

    def resolve(self, job_id):
        job_id = str(job_id).strip().lower()
        if re.fullmatch(r"[a-f0-9]{32}", job_id):
            return job_id
        if re.fullmatch(r"[a-f0-9]{8,31}", job_id):
            matches = [path.parent.name for path in self.directory.glob("*/job.json")
                       if path.parent.name.startswith(job_id) and re.fullmatch(r"[a-f0-9]{32}", path.parent.name)]
            if len(matches) == 1:
                return matches[0]
            if not matches:
                raise FileNotFoundError("Job not found")
            raise ValueError("Ambiguous job ID prefix; use more characters.")
        raise ValueError("Invalid job ID")

    def get(self, job_id):
        with self.lock:
            return json.loads((self.folder(self.resolve(job_id)) / "job.json").read_text(encoding="utf-8"))

    def list(self, limit=20):
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise ValueError("Job list limit must be a number.") from None
        if not 1 <= limit <= 100:
            raise ValueError("Job list limit must be between 1 and 100.")
        items = []
        with self.lock:
            for path in self.directory.glob("*/job.json"):
                if not re.fullmatch(r"[a-f0-9]{32}", path.parent.name):
                    continue
                try:
                    items.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue
        items.sort(key=lambda job: job.get("updated_at") or "", reverse=True)
        return items[:limit]

    def update(self, job_id, **changes):
        with self.lock:
            path = self.folder(job_id) / "job.json"
            data = self.get(job_id) if path.exists() else {"id": job_id}
            data.update(changes, updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
            return data

    def create(self, source, owner="local"):
        return self.update(uuid.uuid4().hex, source=str(source), owner=owner, status="queued", stage="queued")

    def recover(self, owner=None, *, stale=False):
        """Mark unfinished jobs as failed. Worker startup uses stale=False.

        CLI uses owner='local' and stale=True so a still-running pipeline is left alone.
        Corrupt job.json files are skipped.
        """
        interrupted = []
        for path in self.directory.glob("*/job.json"):
            name = path.parent.name
            if not re.fullmatch(r"[a-f0-9]{32}", name):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or data.get("status") not in ("queued", "running"):
                continue
            if owner is not None and data.get("owner") != owner:
                continue
            if stale and pid_running(data.get("pid")):
                continue
            job_id = data.get("id") if isinstance(data.get("id"), str) and re.fullmatch(r"[a-f0-9]{32}", data.get("id")) else name
            interrupted.append(self.update(
                job_id, status="failed", pid=None,
                error="Interrupted before completion; existing output was preserved. Resume with: pt retry " + job_id[:8]))
        return interrupted

    def retry(self, job_id, settings, runner=run_pipeline, report=None):
        job = self.get(job_id)
        job_id = job["id"]
        status = job.get("status")
        if status == "succeeded":
            raise ValueError("Job already succeeded. Output is in " + str(self.folder(job_id)))
        if status == "running" and pid_running(job.get("pid")):
            raise ValueError("Job is still running. Wait for it to finish, or stop that process first.")
        return self.execute(job_id, settings, runner=runner, report=report)

    def execute(self, job_id, settings, runner=run_pipeline, report=None):
        job = self.get(job_id)
        job_id = job["id"]
        try:
            self.update(job_id, status="running", pid=os.getpid(), error=None)

            def progress(stage):
                if report:
                    report(stage)
                self.update(job_id, stage=stage)

            result = runner(job["source"], self.folder(job_id), settings, progress)
            return self.update(job_id, status="succeeded", stage="complete", result=result, pid=None, error=None)
        except Exception as error:
            return self.update(job_id, status="failed", pid=None, error=str(error)[:1000])
        except KeyboardInterrupt:
            self.update(job_id, status="failed", pid=None,
                        error="Interrupted (Ctrl-C). Existing output was preserved. Resume with: pt retry " + job_id[:8])
            raise


def artifacts(folder):
    folder = Path(folder)
    present = {name: (folder / name).is_file() for name in ("transcript.txt", "transcript.json", "summary.md")}
    media_dir = folder / "media"
    present["media"] = media_dir.is_dir() and any(path.is_file() for path in media_dir.iterdir())
    return present
