"""Local web server: 127.0.0.1 only, a per-launch token on every API call, and no data leaving the machine."""

from email import message_from_bytes, policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import tempfile
import threading
import traceback
from urllib.parse import parse_qs, unquote, urlsplit

from .analysis import load_catalogue
from .rendering import safe_text
from .tracker import FieldErrors
from .webapi import ApiError, AppService

WEB_ROOT = Path(__file__).with_name("web")
MAX_BODY = 10 * 1024 * 1024
DEFAULT_PORT = 8765
PORT_ATTEMPTS = 25
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml",
         ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
TOKEN_TAG = re.compile(r'<meta\s+name="cd-token"\s+content="[^"]*"\s*/?>', re.I)
COOKIE = "cd_session"
LANDING = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
    "<title>Career Discovery</title></head>"
    '<body style="font-family:system-ui,sans-serif;max-width:34rem;margin:4rem auto;padding:0 1rem;line-height:1.5">'
    "<h1>Open Career Discovery from its starter window</h1>"
    "<p>This page needs the link that the starter window printed (it begins with http://127.0.0.1: and ends with ?launch=...). "
    "That link works once. If it was used or lost, close the starter window and start Career Discovery again.</p>"
    '<h1 lang="de">Career Discovery aus dem Starterfenster öffnen</h1>'
    '<p lang="de">Diese Seite braucht den Link, den das Starterfenster ausgegeben hat (er beginnt mit http://127.0.0.1: und endet mit '
    "?launch=...). Der Link funktioniert nur einmal. Ist er verbraucht oder verloren, schließ das Starterfenster und "
    "starte Career Discovery neu.</p></body></html>"
).encode("utf-8")
METHODS = ("GET", "POST", "PUT", "DELETE")


class Download:
    def __init__(self, data, content_type, filename):
        self.data, self.content_type, self.filename = data, content_type, filename


def flag(query, name):
    return query.get(name, ["0"])[0].lower() in {"1", "true", "yes"}


def first(query, name, default=None):
    return query.get(name, [default])[0]


def parse_multipart(body, content_type):
    message = message_from_bytes(b"Content-Type: " + content_type.encode("latin-1", "replace")
                                 + b"\r\nMIME-Version: 1.0\r\n\r\n" + body, policy=policy.HTTP)
    if not message.is_multipart():
        raise ApiError(400, "bad_upload", "The upload could not be read.")
    fields, files = {}, {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        data = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename is not None:
            files[name] = (filename, data)
        else:
            fields[name] = data.decode("utf-8", errors="replace")
    return fields, files


def one_file(files, label):
    if "file" not in files or not files["file"][1]:
        raise ApiError(422, "invalid", f"Choose a {label} file to upload.", {"file": "Required."})
    return files["file"]


class Request:
    def __init__(self, query, body, files):
        self.query, self.body, self.files = query, body, files


def routes(service):
    def cv(r):
        name, data = one_file(r.files, "CV")
        return service.profile_from_cv(name, data)

    def import_jobs(r):
        if r.files:
            data = one_file(r.files, "CSV")[1]
            keep = str(r.body.get("keep_description", "")).lower() in {"1", "true", "yes"}
        else:
            if not isinstance(r.body.get("csv"), str):
                raise ApiError(422, "invalid", "Send a CSV file or a csv text field.", {"csv": "Required."})
            data, keep = r.body["csv"].encode("utf-8"), r.body.get("keep_description") is True
        return service.import_csv(data, keep)

    def matches(r):
        try:
            limit = int(first(r.query, "limit", 50))
        except ValueError:
            raise ApiError(422, "invalid", "The limit must be a whole number.") from None
        return service.matches(first(r.query, "mode", "task"), limit, flag(r.query, "excluded"),
                               flag(r.query, "hide_language_conflicts"), first(r.query, "q", ""), flag(r.query, "duties"))

    def compare(r):
        return service.compare_applications(r.query.get("key", []))

    def export(r):
        text = json.dumps(service.export_all(), ensure_ascii=False, indent=2)
        return Download(text.encode("utf-8"), "application/json; charset=utf-8", "career-discovery-data.json")

    def applications_csv(r):
        return Download(service.applications_csv(), "text/csv; charset=utf-8", "my-applications.csv")

    def remove_application(r):
        return service.remove_application(first(r.query, "job_key", ""))

    return {
        ("GET", "/api/state"): lambda r: service.state(),
        ("POST", "/api/profile/cv"): cv,
        ("POST", "/api/profile/new"): lambda r: service.new_profile(r.body.get("replace") is True),
        ("GET", "/api/profile"): lambda r: service.get_profile(),
        ("PUT", "/api/profile"): lambda r: service.update_details(r.body),
        ("POST", "/api/profile/evidence"): lambda r: service.change_evidence(r.body),
        ("POST", "/api/profile/confirm"): lambda r: service.confirm_profile(),
        ("GET", "/api/families"): lambda r: service.families(),
        ("POST", "/api/jobs/refresh"): lambda r: service.start_refresh(r.body.get("group", "standard")),
        ("GET", "/api/jobs/refresh"): lambda r: service.refresh_status(),
        ("POST", "/api/jobs/import"): import_jobs,
        ("GET", "/api/matches"): matches,
        ("POST", "/api/matches/recheck"): lambda r: service.recheck(r.body.get("job_key", "")),
        ("POST", "/api/feedback"): lambda r: service.add_feedback(r.body),
        ("GET", "/api/feedback"): lambda r: service.list_feedback(),
        ("GET", "/api/applications"): lambda r: service.list_applications(),
        ("POST", "/api/applications"): lambda r: service.save_application(r.body),
        ("DELETE", "/api/applications"): remove_application,
        ("GET", "/api/applications/export.csv"): applications_csv,
        ("GET", "/api/applications/compare"): compare,
        ("GET", "/api/summary"): lambda r: service.summary(),
        ("POST", "/api/summary/seen"): lambda r: service.mark_seen(),
        ("GET", "/api/export"): export,
        ("POST", "/api/data/delete"): lambda r: service.delete_all(r.body.get("confirm")),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "CareerDiscovery"
    sys_version = ""
    timeout = 30

    def log_message(self, *_):
        pass

    def send(self, status, body, content_type, cache="no-store", extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, status, value):
        self.send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def fail(self, status, code, message, fields=None, close=False):
        if close:
            self.close_connection = True
        error = {"code": code, "message": message}
        if fields:
            error["fields"] = fields
        self.send_json(status, {"error": error})

    def do_everything(self):
        try:
            self.dispatch()
        except ApiError as exc:
            self.fail(exc.status, exc.code, exc.message, exc.fields)
        except TimeoutError:
            self.close_connection = True
        except FieldErrors as exc:
            self.fail(422, "invalid", "Some details need fixing before they can be saved.", exc.fields)
        except ValueError as exc:
            self.fail(422, "invalid", safe_text(str(exc)) or "That input is not valid.")
        except (KeyError, TypeError, AttributeError):
            self.fail(400, "bad_request", "The request is missing a field or has a field of the wrong type.")
        except (OSError, sqlite3.Error):
            traceback.print_exc()
            self.fail(500, "storage_error", "The app could not read or write its data folder. Check that it is not full or locked.")
        except Exception:
            traceback.print_exc()
            self.fail(500, "internal_error", "Something went wrong inside the app. Your data is unchanged. Try again.")

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_PATCH = do_OPTIONS = do_everything

    def check_origin(self):
        if (self.headers.get("Host") or "").lower() not in self.server.allowed_hosts:
            raise ApiError(403, "bad_host", "This address is not allowed. Open the app from the link it printed.")
        origin = self.headers.get("Origin")
        if origin is not None and origin.lower() not in self.server.allowed_origins:
            raise ApiError(403, "bad_origin", "Requests from other websites are not allowed.")

    def has_session(self):
        for header in self.headers.get_all("Cookie") or []:
            for item in header.split(";"):
                name, _, value = item.strip().partition("=")
                if name == COOKIE and secrets.compare_digest(value.encode("utf-8"), self.server.session.encode("utf-8")):
                    return True
        return False

    def launch(self, query):
        given = first(query, "launch", "")
        if given and self.server.spend_launch_secret(given):
            self.send(303, b"", "text/plain; charset=utf-8", extra={
                "Location": "/", "Set-Cookie": f"{COOKIE}={self.server.session}; HttpOnly; SameSite=Strict; Path=/"})
            return True
        return False

    def dispatch(self):
        self.check_origin()
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        if not path.startswith("/api/"):
            if path in {"/", "/index.html"} and self.command in {"GET", "HEAD"}:
                if self.launch(parse_qs(parts.query)):
                    return
                if not self.has_session():
                    return self.send(200, LANDING, TYPES[".html"])
            return self.static(path)
        if not self.has_session():
            self.close_connection = True
            raise ApiError(401, "unauthorized", "This request did not come from a window opened with the app's launch link.")
        token = self.headers.get("X-CD-Token") or ""
        if not secrets.compare_digest(token.encode("utf-8"), self.server.token.encode("utf-8")):
            self.close_connection = True
            raise ApiError(401, "unauthorized", "This request did not carry the app's launch token. Reload the page.")
        if self.command == "HEAD" or self.command not in METHODS:
            raise ApiError(405, "method_not_allowed", "That method is not supported.")
        body, files = self.read_body()
        if path == "/api/shutdown" and self.command == "POST":
            self.send_json(200, {"stopping": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        handler = self.server.routes.get((self.command, path))
        if handler is None:
            known = {p for _, p in self.server.routes}
            if path in known:
                raise ApiError(405, "method_not_allowed", "That method is not supported here.")
            raise ApiError(404, "not_found", "There is no such endpoint.")
        result = handler(Request(parse_qs(parts.query), body, files))
        if isinstance(result, Download):
            disposition = f'attachment; filename="{result.filename}"'
            self.send(200, result.data, result.content_type, extra={"Content-Disposition": disposition})
        else:
            self.send_json(200, result)

    def read_body(self):
        if self.headers.get("Transfer-Encoding"):
            raise ApiError(411, "length_required", "Send the body with a Content-Length.")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "bad_request", "The Content-Length is not a number.") from None
        if length < 0:
            raise ApiError(400, "bad_request", "The Content-Length is not valid.")
        if length > MAX_BODY:
            self.close_connection = True
            raise ApiError(413, "too_large", "That upload is larger than 10 MB.")
        if not length:
            return {}, {}
        kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if kind not in {"application/json", "multipart/form-data"}:
            self.close_connection = True
            raise ApiError(415, "unsupported_type", "Send JSON or a multipart form.")
        raw = self.rfile.read(length)
        if kind == "multipart/form-data":
            fields, files = parse_multipart(raw, self.headers["Content-Type"])
            return fields, files
        try:
            value = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise ApiError(400, "bad_json", "The request body is not valid JSON.") from None
        if not isinstance(value, dict):
            raise ApiError(400, "bad_json", "The request body must be a JSON object.")
        return value, {}

    def static(self, path):
        if self.command not in {"GET", "HEAD"}:
            raise ApiError(405, "method_not_allowed", "That method is not supported.")
        name = path.lstrip("/") or "index.html"
        target = (WEB_ROOT / name).resolve() if "\x00" not in name and "\\" not in name else None
        if (target is None or not target.is_relative_to(WEB_ROOT.resolve()) or not target.is_file()
                or any(part.startswith(".") for part in Path(name).parts)):
            raise ApiError(404, "not_found", "There is no such page.")
        data = target.read_bytes()
        kind = TYPES.get(target.suffix.lower(), "application/octet-stream")
        if target.name == "index.html" and target.parent == WEB_ROOT.resolve():
            page = data.decode("utf-8")
            tag = f'<meta name="cd-token" content="{self.server.token}">'
            page = TOKEN_TAG.sub(tag, page) if TOKEN_TAG.search(page) else page.replace("</head>", tag + "</head>", 1)
            return self.send(200, page.encode("utf-8"), kind)
        self.send(200, data, kind, cache="no-cache")


class AppServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, service):
        super().__init__(address, Handler)
        port = self.server_address[1]
        self.service, self.token, self.routes = service, secrets.token_urlsafe(32), routes(service)
        self.session, self.launch_secret = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self.launch_lock = threading.Lock()
        self.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.allowed_origins = {f"http://{host}" for host in self.allowed_hosts}

    def spend_launch_secret(self, given):
        with self.launch_lock:
            secret = self.launch_secret
            if secret is None or not secrets.compare_digest(given.encode("utf-8"), secret.encode("utf-8")):
                return False
            self.launch_secret = None
            return True


def make_server(service, port=0):
    if port == 0:
        return AppServer(("127.0.0.1", 0), service)
    last = None
    for candidate in range(port, min(port + PORT_ATTEMPTS, 65536)):
        try:
            return AppServer(("127.0.0.1", candidate), service)
        except OSError as exc:
            last = exc
    raise OSError(f"No free port found from {port} to {port + PORT_ATTEMPTS - 1}.") from last


def default_data_dir():
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Career Discovery"
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local") / "Career Discovery"
    return Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") / "career-discovery"


def smoke(server, url):
    from http.cookiejar import CookieJar
    from urllib.request import HTTPCookieProcessor, Request as Get, build_opener

    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    page = opener.open(f"{url}?launch={server.launch_secret}", timeout=10).read().decode("utf-8")
    if f'content="{server.token}"' not in page:
        raise SystemExit("Smoke test failed: the page did not carry the launch token.")
    state = opener.open(Get(url + "api/state", headers={"X-CD-Token": server.token}), timeout=10)
    if json.loads(state.read().decode("utf-8")).get("data_dir") is None:
        raise SystemExit("Smoke test failed: the state call returned no data folder.")
    print("OK")


def run_app(args, catalogue_path=None):
    scratch = tempfile.TemporaryDirectory() if args.smoke and not args.app_state else None
    root = Path(scratch.name) if scratch else Path(args.app_state) if args.app_state else default_data_dir()
    service = AppService(root, catalogue=load_catalogue(catalogue_path))
    server = make_server(service, args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        if args.smoke:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                smoke(server, url)
            finally:
                server.shutdown()
                thread.join(5)
            return
        launch = f"{url}?launch={server.launch_secret}"
        print("Career Discovery is running. Your browser opens it now. If it does not, open this link in your browser.")
        print(f"The link works once. To get a new one, close this window and start Career Discovery again:\n{launch}")
        print(f"Your data is kept in {service.root}")
        print("Press Ctrl+C in this window to stop it.", flush=True)
        if not args.no_browser:
            import webbrowser
            webbrowser.open(launch)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            print("\nStopped.")
    finally:
        server.server_close()
        if scratch:
            scratch.cleanup()
