"""Small, dependency-free message board for a trusted home LAN."""
import argparse
import json
import logging
import os
import tempfile
import threading
import time
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

COLORS = {"white": "#ffffff", "green": "#66ff66", "yellow": "#ffdd66", "pink": "#ff88bb"}
EXPIRIES = {5, 15, 30, 60, 180, 360, 1440}
STATIC = {"/font.js": ("font.js", "text/javascript; charset=utf-8"), "/layout.js": ("layout.js", "text/javascript; charset=utf-8"), "/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}


def validate(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        raise ValueError("Enter a message.")
    text = " ".join(unicodedata.normalize("NFC", payload["text"]).translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."})).split())
    if not 1 <= len(text) <= 120:
        raise ValueError("Use between 1 and 120 characters.")
    if any(not (32 <= ord(c) <= 126 or 160 <= ord(c) <= 255) for c in text):
        raise ValueError("Use letters, numbers and simple punctuation. Swedish letters are supported; emoji are not.")
    color = payload.get("color", "white")
    minutes = payload.get("expires_minutes", 60)
    if not isinstance(color, str) or color not in COLORS:
        raise ValueError("Choose a listed color.")
    if type(minutes) is not int or minutes not in EXPIRIES:
        raise ValueError("Choose a listed expiry time.")
    return text, color, minutes


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.state = {"text": "", "color": "white", "expires_at": None, "updated_at": None}
        if self.path.exists():
            # Fail startup on corruption rather than silently losing a saved message.
            state = json.loads(self.path.read_text())
            if not isinstance(state, dict) or not isinstance(state.get("text"), str) or state.get("color") not in COLORS:
                raise ValueError("Invalid saved message file")
            expiry = state.get("expires_at")
            if expiry is not None and type(expiry) not in (int, float):
                raise ValueError("Invalid saved expiry")
            self.state = state

    def read(self):
        with self.lock:
            state = self.state.copy()
        updated = state.get("updated_at")
        if state["text"] and state["expires_at"] is None:
            deadline = updated + 3600 if type(updated) in (int, float) else 0
            state["expires_at"] = deadline
        expired = state.get("expires_at") is not None and time.time() >= state["expires_at"]
        if expired:
            state["text"] = ""
        state["active"] = bool(state["text"])
        state["expired"] = expired
        state["display_color"] = COLORS[state["color"]]
        return state

    def save(self, text, color="white", minutes=60):
        now = int(time.time())
        state = {"text": text, "color": color, "updated_at": now, "expires_at": now + minutes * 60 if minutes else None}
        with self.lock:
            fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".message-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    json.dump(state, file, ensure_ascii=False)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(name, self.path)
                self.state = state
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        return self.read()


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, allowed_hosts):
        self.store = store
        self.allowed_hosts = set(allowed_hosts)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, fmt, *args):
        # Do not log message contents or query strings.
        logging.info("%s %s", self.command, self.path.split("?")[0])

    def respond(self, status, data, content_type="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, dict) else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def host_allowed(self):
        try:
            host = urlsplit("http://" + self.headers.get("Host", "")).hostname
        except ValueError:
            host = None
        if host not in self.server.allowed_hosts:
            self.respond(403, {"error": "This address is not enabled. Add it to BOARD_ALLOWED_HOSTS on the Pi."})
            return False
        return True

    def do_GET(self):
        if not self.host_allowed():
            return
        path = urlsplit(self.path).path
        if path == "/api/message":
            self.respond(200, self.server.store.read())
        elif path == "/health":
            self.respond(200, {"ok": True})
        elif path in STATIC:
            name, kind = STATIC[path]
            self.respond(200, (Path(__file__).parent / name).read_bytes(), kind)
        else:
            self.respond(404, {"error": "Not found"})

    def do_POST(self):
        if not self.host_allowed():
            return
        # Same-origin JSON writes and an explicit host allowlist protect against
        # cross-site requests and DNS rebinding. This is not user authentication.
        if self.headers.get("Origin") != "http://" + self.headers.get("Host", ""):
            self.respond(403, {"error": "Open the message page on this server to send a message."})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.respond(415, {"error": "Expected JSON"})
            return
        path = urlsplit(self.path).path
        if path not in ("/api/message", "/api/clear"):
            self.respond(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                self.respond(413, {"error": "Request is too large or empty"})
                return
            payload = json.loads(self.rfile.read(size))
            if path == "/api/clear":
                state = self.server.store.save("")
            else:
                state = self.server.store.save(*validate(payload))
            self.respond(200, state)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.respond(400, {"error": "Invalid JSON request."})
        except ValueError as exc:
            self.respond(400, {"error": str(exc)})
        except OSError:
            logging.exception("Could not save message")
            self.respond(500, {"error": "Could not save the message. Please try again."})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--data", default=os.environ.get("BOARD_DATA", "data/message.json"))
    args = parser.parse_args()
    hosts = os.environ.get("BOARD_ALLOWED_HOSTS", "localhost,127.0.0.1,tidbyt-pi.local,192.168.0.127")
    logging.basicConfig(level=logging.INFO)
    server = Server((args.host, args.port), Store(args.data), [h.strip().lower() for h in hosts.split(",")])
    logging.info("Message Board listening on port %s", args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
