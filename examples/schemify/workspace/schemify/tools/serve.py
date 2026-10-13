#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Serve a schemify workspace's website on this computer, and receive its feedback.

The website (schemify/index.html) also works opened straight from disk; served,
it gains one-click "Send to your agent" and live progress. The server listens on
127.0.0.1 only, serves the workspace folder, and accepts two kinds of write:
POST /api/inbox, which saves the page's feedback as a JSON file in
schemify/inbox/pending/ for the agent to process, and POST /api/presence, which
records whether the page is connected to QuaC (state/presence.json: a few
words and flags, never data) so the agent's `data-check` knows whether to ask
the page for a re-check. Nothing else is writable.

Usage (agent):   uv run <skill-dir>/scripts/serve.py start  --ws schemify
                 uv run <skill-dir>/scripts/serve.py status --ws schemify
                 uv run <skill-dir>/scripts/serve.py stop   --ws schemify
Usage (people):  python3 schemify/tools/serve.py          (runs until Ctrl-C)
Fallback:        any `python3` 3.9+ runs this file; it needs no packages.

start/status/stop print one JSON object to stdout. Exit codes: 0 ok,
1 error (JSON carries "error" and "hint"). `run` (the default) serves in
the foreground and logs to stderr.

Security: requests must name this server in their Host header (defeats DNS
rebinding); every POST must come from this server's own origin and carry
the per-run token the page reads from GET /api/session — a page on another
site can neither read the token (no CORS headers are ever sent) nor post
without it.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HOST = "127.0.0.1"
# Ports 8700-8899: unassigned by IANA for common services and above the
# 1024 privileged range. Each workspace prefers one stable port (hashed from its
# path) so the browser keeps the same origin -- and the same saved drafts --
# from one session to the next.
PORT_BASE, PORT_SPAN, PORT_TRIES = 8700, 200, 20
MAX_POST_BYTES = 25 * 1024 * 1024        # findings files for wide schemas run to a few MB
MAX_PRESENCE_BYTES = 4096
IDLE_HOURS_DEFAULT = 24.0                # an open tab polls every few seconds, so this only
                                         # fires a day after the last tab closed
START_WAIT_SECONDS = 8.0
NO_STORE = {".html", ".js", ".css", ".json", ".svg", ".md", ".csv"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def out(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(error: str, hint: str) -> None:
    out({"ok": False, "error": error, "hint": hint}, 1)


# ---------------------------------------------------------------- workspace

def is_workspace(p: Path) -> bool:
    return (p / "state" / "project.json").is_file()


def find_workspace(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser().resolve()
        if is_workspace(p):
            return p
        if is_workspace(p / "schemify"):
            return p / "schemify"
        fail(f"No schemify workspace at {arg}.",
             "Pass the folder that holds state/project.json, usually ./schemify.")
    here = Path(__file__).resolve().parent
    if here.name == "tools" and is_workspace(here.parent):
        return here.parent                    # the copy inside a workspace serves its own
    cwd = Path.cwd().resolve()
    for base in [cwd, *list(cwd.parents)[:4]]:
        if is_workspace(base):
            return base
        found = sorted(d.parent.parent for d in base.glob("schemify*/state/project.json"))
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            fail("Several schemify workspaces here: " + ", ".join(str(f) for f in found),
                 "Pass --ws with the one to serve.")
    fail("No schemify workspace found from here.",
         "Run this from the folder that contains schemify/, or pass --ws.")
    raise AssertionError


def project(ws: Path) -> dict:
    try:
        return json.loads((ws / "state" / "project.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def info_path(ws: Path) -> Path:
    return ws / "state" / "server.json"


def preferred_port(ws: Path) -> int:
    return PORT_BASE + zlib.crc32(str(ws).encode("utf-8")) % PORT_SPAN


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, port))
            return True
        except OSError:
            return False


def probe(port: int, timeout: float = 1.5) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/session", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def running(ws: Path) -> dict | None:
    """The live server for this workspace, or None (stale info is removed)."""
    p = info_path(ws)
    try:
        info = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    sess = probe(int(info.get("port", 0)))
    if sess and sess.get("workspace") == project(ws).get("id") and sess.get("root") == str(ws):
        return info
    if not pid_alive(int(info.get("pid", 0))):
        try:
            p.unlink()
        except OSError:
            pass
    return None


# ---------------------------------------------------------------- the server

class State:
    def __init__(self, ws: Path, port: int, idle_hours: float):
        self.ws = ws
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self.last_seen = time.monotonic()
        self.idle_seconds = idle_hours * 3600
        self.allowed_hosts = {f"{HOST}:{port}", f"localhost:{port}"}
        self.allowed_origins = {f"http://{h}" for h in self.allowed_hosts}
        self.lock = threading.Lock()


def make_handler(st: State):
    root = st.ws.resolve()
    pending = root / "inbox" / "pending"

    class Handler(BaseHTTPRequestHandler):
        server_version = "schemify-serve"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # quiet, timestamped
            sys.stderr.write(f"{now_iso()} {self.address_string()} {fmt % args}\n")

        # -- helpers
        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code: int, payload: dict):
            self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8",
                       {"Cache-Control": "no-store"})

        def _host_ok(self) -> bool:
            return (self.headers.get("Host") or "") in st.allowed_hosts

        def _touch(self):
            with st.lock:
                st.last_seen = time.monotonic()

        # -- verbs
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"ok": False, "error": "unexpected Host header"})
            self._touch()
            path = unquote(urlsplit(self.path).path)
            if path == "/api/session":
                proj = project(root)
                return self._json(200, {
                    "ok": True, "token": st.token, "workspace": proj.get("id"),
                    "study": proj.get("study"), "mode": proj.get("mode"), "root": str(root),
                    "pending": len(list(pending.glob("*.json"))) if pending.is_dir() else 0,
                })
            if path.startswith("/api/"):
                return self._json(404, {"ok": False, "error": "no such endpoint"})
            if path.endswith("/"):
                path += "index.html"
            target = (root / path.lstrip("/")).resolve()
            if root not in target.parents and target != root:
                return self._json(403, {"ok": False, "error": "outside the workspace"})
            if target == info_path(root).resolve() or not target.is_file():
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            extra = {"Cache-Control": "no-store"} if target.suffix in NO_STORE else {}
            try:
                body = target.read_bytes()
            except OSError:
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            self._send(200, body, ctype, extra)

        def do_POST(self):
            if not self._host_ok():
                return self._json(403, {"ok": False, "error": "unexpected Host header"})
            self._touch()
            endpoint = urlsplit(self.path).path
            if endpoint not in ("/api/inbox", "/api/presence"):
                return self._json(404, {"ok": False, "error": "no such endpoint"})
            origin = self.headers.get("Origin")
            if origin is not None and origin not in st.allowed_origins:
                return self._json(403, {"ok": False, "error": "cross-origin post refused"})
            if not secrets.compare_digest(self.headers.get("X-Schemify-Token") or "", st.token):
                return self._json(403, {"ok": False, "error": "missing or stale token; reload the page"})
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self._json(415, {"ok": False, "error": "JSON only"})
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                length = -1
            limit = MAX_POST_BYTES if endpoint == "/api/inbox" else MAX_PRESENCE_BYTES
            if length <= 0 or length > limit:
                return self._json(413, {"ok": False, "error": f"body must be 1..{limit} bytes"})
            try:
                doc = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return self._json(400, {"ok": False, "error": f"not JSON: {exc}"})
            if endpoint == "/api/presence":
                return self._presence(doc)
            if not isinstance(doc, dict) or not isinstance(doc.get("items"), list) or not doc["items"]:
                return self._json(400, {"ok": False, "error": "expected {\"items\": [...]} with at least one item"})
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            sub_id = f"{stamp}-{secrets.token_hex(3)}"
            doc["id"] = sub_id
            doc["receivedAt"] = now_iso()
            pending.mkdir(parents=True, exist_ok=True)
            tmp = pending / f".{sub_id}.tmp"
            tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, pending / f"{sub_id}.json")
            self._json(200, {"ok": True, "id": sub_id, "receivedAt": doc["receivedAt"]})

        def _presence(self, doc):
            quac = doc.get("quac") if isinstance(doc, dict) else None
            if not isinstance(quac, dict):
                return self._json(400, {"ok": False, "error": "expected {\"quac\": {...}}"})
            keep = {"connected": bool(quac.get("connected")), "datasetLoaded": bool(quac.get("datasetLoaded"))}
            for k in ("dataset", "status", "request", "detail"):         # short words, never data
                if isinstance(quac.get(k), str):
                    keep[k] = quac[k][:300]
            state_dir = root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            tmp = state_dir / ".presence.json.tmp"
            tmp.write_text(json.dumps({"at": now_iso(), "quac": keep}, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, state_dir / "presence.json")
            self._json(200, {"ok": True})

    return Handler


def serve_forever(ws: Path, port: int, idle_hours: float) -> None:
    st = State(ws, port, idle_hours)
    httpd = ThreadingHTTPServer((HOST, port), make_handler(st))
    httpd.daemon_threads = True
    url = f"http://{HOST}:{port}/"
    info = {"pid": os.getpid(), "port": port, "url": url, "startedAt": now_iso(), "root": str(ws)}
    tmp = info_path(ws).with_suffix(".tmp")
    tmp.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, info_path(ws))

    def watchdog():
        while True:
            time.sleep(60)
            with st.lock:
                idle = time.monotonic() - st.last_seen
            if idle > st.idle_seconds:
                sys.stderr.write(f"{now_iso()} idle for {idle / 3600:.1f} h; stopping\n")
                httpd.shutdown()
                return

    threading.Thread(target=watchdog, daemon=True).start()

    def bye(*_):
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, bye)
    sys.stderr.write(f"schemify website for {project(ws).get('study') or ws.name}: {url}\n"
                     f"Leave this running while you use the website; Ctrl-C stops it.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        try:
            cur = json.loads(info_path(ws).read_text(encoding="utf-8"))
            if cur.get("pid") == os.getpid():
                info_path(ws).unlink()
        except (OSError, json.JSONDecodeError):
            pass


def choose_port(ws: Path, requested: int | None) -> int:
    if requested:
        if not port_free(requested):
            fail(f"Port {requested} is in use.", "Omit --port to let the server pick a free one.")
        return requested
    first = preferred_port(ws)
    for i in range(PORT_TRIES):
        port = PORT_BASE + (first - PORT_BASE + i) % PORT_SPAN
        if port_free(port):
            return port
    fail("No free port between 8700 and 8899.", "Stop another schemify server (serve.py stop) and retry.")
    raise AssertionError


# ---------------------------------------------------------------- commands

def cmd_run(ws: Path, a) -> None:
    live = running(ws)
    if live:
        sys.stderr.write(f"Already running: {live['url']}\n")
        return
    serve_forever(ws, choose_port(ws, a.port), a.idle_hours)


def cmd_start(ws: Path, a) -> None:
    live = running(ws)
    if live:
        out({"ok": True, "url": live["url"], "port": live["port"], "pid": live["pid"], "already": True})
    port = choose_port(ws, a.port)
    log = ws / "state" / "server.log"
    try:
        if log.exists() and log.stat().st_size > 1_000_000:
            log.replace(log.with_suffix(".log.1"))
    except OSError:
        pass
    cmd = [sys.executable, str(Path(__file__).resolve()), "run", "--ws", str(ws),
           "--port", str(port), "--idle-hours", str(a.idle_hours)]
    kwargs: dict = {"stdin": subprocess.DEVNULL, "cwd": str(ws)}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    with open(log, "a", encoding="utf-8") as fh:
        proc = subprocess.Popen(cmd, stdout=fh, stderr=fh, **kwargs)
    deadline = time.monotonic() + START_WAIT_SECONDS
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        sess = probe(port, timeout=0.5)
        if sess and sess.get("root") == str(ws):
            out({"ok": True, "url": f"http://{HOST}:{port}/", "port": port, "pid": proc.pid, "already": False})
        time.sleep(0.2)
    fail(f"The website server did not start (see {log}).",
         "The page still works opened from disk: open schemify/index.html. "
         "If this harness blocks background processes, ask the user to run: python3 schemify/tools/serve.py")


def cmd_stop(ws: Path, a) -> None:
    live = running(ws)
    if not live:
        out({"ok": True, "stopped": False, "note": "not running"})
    try:
        os.kill(int(live["pid"]), signal.SIGTERM)
    except OSError as exc:
        fail(f"Could not stop pid {live['pid']}: {exc}", "Stop it from the terminal that started it.")
    for _ in range(25):
        if not pid_alive(int(live["pid"])):
            break
        time.sleep(0.2)
    out({"ok": True, "stopped": True, "url": live["url"]})


def cmd_status(ws: Path, a) -> None:
    live = running(ws)
    if live:
        out({"ok": True, "running": True, "url": live["url"], "port": live["port"], "pid": live["pid"]})
    out({"ok": True, "running": False, "file": str(ws / "index.html"),
         "hint": "Start it with: serve.py start --ws " + str(ws)})


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", default="run", choices=["run", "start", "stop", "status"])
    p.add_argument("--ws", help="workspace folder (default: found from here)")
    p.add_argument("--port", type=int, help="port to use (default: a stable port for this workspace)")
    p.add_argument("--idle-hours", type=float, default=IDLE_HOURS_DEFAULT,
                   help=f"stop after this long with no requests (default {IDLE_HOURS_DEFAULT:g})")
    a = p.parse_args()
    ws = find_workspace(a.ws)
    {"run": cmd_run, "start": cmd_start, "stop": cmd_stop, "status": cmd_status}[a.command](ws, a)


if __name__ == "__main__":
    main()
