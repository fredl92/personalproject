import datetime
import json
import re
import threading
import uuid
from pathlib import Path

from .config import atomic_write
from .pipeline import run_pipeline


class JobStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def folder(self, job_id):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("Invalid job ID")
        return self.directory / job_id

    def get(self, job_id):
        with self.lock:
            return json.loads((self.folder(job_id) / "job.json").read_text(encoding="utf-8"))

    def update(self, job_id, **changes):
        with self.lock:
            path = self.folder(job_id) / "job.json"
            data = self.get(job_id) if path.exists() else {"id": job_id}
            data.update(changes, updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
            return data

    def create(self, source, owner="local"):
        return self.update(uuid.uuid4().hex, source=str(source), owner=owner, status="queued", stage="queued")

    def recover(self, owner=None):
        for path in self.directory.glob("*/job.json"):
            data = self.get(path.parent.name)
            if data["status"] in ("queued", "running") and (owner is None or data.get("owner") == owner):
                self.update(data["id"], status="failed", error="Worker restarted before completion; submit again. Existing output was preserved.")

    def execute(self, job_id, settings, runner=run_pipeline):
        try:
            job = self.get(job_id)
            self.update(job_id, status="running")
            result = runner(job["source"], self.folder(job_id), settings,
                            lambda stage: self.update(job_id, stage=stage))
            return self.update(job_id, status="succeeded", stage="complete", result=result)
        except Exception as error:
            return self.update(job_id, status="failed", error=str(error)[:1000])
