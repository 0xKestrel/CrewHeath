#!/usr/bin/env python3
"""
Crew Health Companion — backend API + static file server.

Zero third-party dependencies: only the Python standard library
(http.server, sqlite3, json). Run with:

    python3 server.py [port]

Then open http://localhost:8000 (or whatever port you passed) in a browser.
The same server answers both the API (/api/...) and the frontend page,
so there's nothing to configure and no cross-origin requests to worry about.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend"))
DEFAULT_PORT = 8000

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "CrewHealth/1.0"

    # ---- small helpers -------------------------------------------------
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        # Same-origin in normal use (server serves the frontend too), but
        # harmless to allow in case the page is opened from a different
        # port during development.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _crew_id(self, qs):
        try:
            return int(qs.get("crew_id", ["1"])[0])
        except ValueError:
            return 1

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---- static file serving for anything outside /api/ ----------------
    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        safe_path = os.path.normpath(path).lstrip("/\\")
        full_path = os.path.normpath(os.path.join(FRONTEND_DIR, safe_path))
        if not full_path.startswith(FRONTEND_DIR):
            self.send_error(403, "Forbidden")
            return
        if not os.path.isfile(full_path):
            self.send_error(404, "Not found")
            return
        ext = os.path.splitext(full_path)[1]
        with open(full_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- HTTP verbs ------------------------------------------------------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path

        if path == "/api/ping":
            return self._send_json(200, {"ok": True, "time": db.now_iso()})

        if path == "/api/state":
            crew_id = self._crew_id(qs)
            conn = db.get_conn()
            try:
                db.ensure_crew(conn, crew_id)
                conn.commit()
                state = db.get_state(conn, crew_id)
            finally:
                conn.close()
            return self._send_json(200, state)

        if path == "/api/backup":
            crew_id = self._crew_id(qs)
            conn = db.get_conn()
            try:
                state = db.get_state(conn, crew_id)
            finally:
                conn.close()
            body = json.dumps(state, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="crew-health-backup-crew{crew_id}.json"')
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return

        if path.startswith("/api/"):
            return self._send_json(404, {"error": "No such endpoint"})

        return self._serve_static(path)

    def do_PUT(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path != "/api/state":
            return self._send_json(404, {"error": "No such endpoint"})
        crew_id = self._crew_id(qs)
        data = self._read_json_body()
        if data is None:
            return self._send_json(400, {"error": "Body must be JSON"})
        conn = db.get_conn()
        try:
            state = db.put_state(conn, crew_id, data)
        finally:
            conn.close()
        return self._send_json(200, state)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path

        if path == "/api/journal":
            crew_id = self._crew_id(qs)
            data = self._read_json_body()
            text = (data or {}).get("text", "").strip() if data is not None else ""
            if not text:
                return self._send_json(400, {"error": "text is required"})
            conn = db.get_conn()
            try:
                entry = db.add_journal_entry(conn, crew_id, text)
            finally:
                conn.close()
            return self._send_json(201, entry)

        if path == "/api/restore":
            crew_id = self._crew_id(qs)
            data = self._read_json_body()
            if data is None:
                return self._send_json(400, {"error": "Body must be JSON"})
            conn = db.get_conn()
            try:
                # restoring replaces everything for this crew member
                conn.execute("DELETE FROM journal_entries WHERE crew_id=?", (crew_id,))
                conn.execute("DELETE FROM sleep_logs WHERE crew_id=?", (crew_id,))
                conn.execute("DELETE FROM mood_checkins WHERE crew_id=?", (crew_id,))
                conn.execute("DELETE FROM vitals_readings WHERE crew_id=?", (crew_id,))
                conn.commit()
                state = db.put_state(conn, crew_id, data)
            finally:
                conn.close()
            return self._send_json(200, state)

        return self._send_json(404, {"error": "No such endpoint"})

    def do_PATCH(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        parts = [p for p in parsed.path.split("/") if p]
        # /api/journal/<id>
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "journal":
            crew_id = self._crew_id(qs)
            entry_id = parts[2]
            patch = self._read_json_body()
            if patch is None:
                return self._send_json(400, {"error": "Body must be JSON"})
            conn = db.get_conn()
            try:
                state = db.get_state(conn, crew_id)
                entry = next((e for e in state["journal"] if e["id"] == entry_id), None)
                if not entry:
                    conn.close()
                    return self._send_json(404, {"error": "No such journal entry"})
                allowed = {"measure", "recent", "task", "src", "ans", "areas"}
                for k, v in patch.items():
                    if k in allowed:
                        entry[k] = v
                conn.execute(
                    """UPDATE journal_entries SET measure=?, recent=?, task=?, source=?, ans=?, areas=?
                       WHERE crew_id=? AND id=?""",
                    (entry["measure"], entry["recent"], entry["task"], entry["src"], entry["ans"],
                     json.dumps(entry["areas"]), crew_id, entry_id),
                )
                conn.commit()
                updated = db.get_state(conn, crew_id)
            finally:
                conn.close()
            return self._send_json(200, updated)

        return self._send_json(404, {"error": "No such endpoint"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "journal":
            crew_id = self._crew_id(qs)
            entry_id = parts[2]
            conn = db.get_conn()
            try:
                db.delete_journal_entry(conn, crew_id, entry_id)
                state = db.get_state(conn, crew_id)
            finally:
                conn.close()
            return self._send_json(200, state)

        return self._send_json(404, {"error": "No such endpoint"})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    db.init_db()
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Crew Health Companion running at http://localhost:{port}")
    print(f"Database file: {db.DB_PATH}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
