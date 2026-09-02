"""Authenticated container-internal async API; no published host port."""
import hmac
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .jobs import JobStore
from .pipeline import validate_url


def make_server(settings, host="0.0.0.0", port=8765):
    settings.validate(("WORKER_API_TOKEN",))
    jobs = JobStore(settings.path("JOBS_DIR"))
    jobs.recover(owner="worker")
    executor = ThreadPoolExecutor(max_workers=1)
    capacity = threading.BoundedSemaphore(20)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, data):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            if not hmac.compare_digest(self.headers.get("X-Toolkit-Token", ""), settings.get("WORKER_API_TOKEN")):
                self.respond(401, {"error": "Authentication required"})
                return False
            return True

        def do_GET(self):
            if self.path == "/health":
                return self.respond(200, {"status": "ok"})
            if not self.authorized():
                return
            if not self.path.startswith("/jobs/"):
                return self.respond(404, {"error": "Not found"})
            try:
                self.respond(200, jobs.get(self.path.removeprefix("/jobs/")))
            except (ValueError, FileNotFoundError):
                self.respond(404, {"error": "Job not found"})

        def do_POST(self):
            if not self.authorized():
                return
            if self.path != "/jobs":
                return self.respond(404, {"error": "Not found"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    return self.respond(413, {"error": "Body must be 1–8192 bytes"})
                self.connection.settimeout(10)
                data = json.loads(self.rfile.read(size))
                url = validate_url(data["url"])
            except (ValueError, KeyError, TypeError, TimeoutError):
                return self.respond(400, {"error": "Expected JSON with a valid http(s) url"})
            if not capacity.acquire(blocking=False):
                return self.respond(429, {"error": "Queue is full; retry later"})
            try:
                job = jobs.create(url, owner="worker")
                future = executor.submit(jobs.execute, job["id"], settings)
                future.add_done_callback(lambda _: capacity.release())
            except Exception:
                capacity.release()
                return self.respond(500, {"error": "Could not create job"})
            self.respond(202, job)

    server = ThreadingHTTPServer((host, port), Handler)
    server.executor = executor
    return server


def serve(settings):
    server = make_server(settings)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.executor.shutdown(wait=True)
