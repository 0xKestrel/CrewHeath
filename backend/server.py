#!/usr/bin/env python3
"""
Crew Health Companion: backend API + static file server (stdlib only).

    python3 server.py [port]

API
  GET    /api/ping
  GET    /api/state?crew_id=1
  PUT    /api/state?crew_id=1            full client state (vitals, hist, journal, mission...)
  GET    /api/history?metric=hr&limit=30 history for one vital
  GET    /api/hazards                    the five hazards and their linked indicators
  GET    /api/mission  /  PUT /api/mission   {"context":"iss|moon|mars"}
  GET    /api/backup   /  POST /api/restore
  POST   /api/journal  /  PATCH,DELETE /api/journal/<id>
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
MAX_BODY = 5 * 1024 * 1024

MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}


class Handler(BaseHTTPRequestHandler):
    server_version = "CrewHealth/2.0"

    def _send_json(self, status, payload, extra=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        if length > MAX_BODY:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _crew(self, qs):
        try:
            n = int(qs.get("crew_id", ["1"])[0])
            return n if n > 0 else 1
        except ValueError:
            return 1

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _static(self, path):
        if path == "/":
            path = "/index.html"
        full = os.path.normpath(os.path.join(FRONTEND_DIR, os.path.normpath(path).lstrip("/\\")))
        if full != FRONTEND_DIR and not full.startswith(FRONTEND_DIR + os.sep):
            return self.send_error(403, "Forbidden")
        if not os.path.isfile(full):
            return self.send_error(404, "Not found")
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(os.path.splitext(full)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        qs, path = parse_qs(u.query), u.path
        if path == "/api/ping":
            return self._send_json(200, {"ok": True, "time": db.now_iso()})
        if not path.startswith("/api/"):
            return self._static(path)

        crew = self._crew(qs)
        conn = db.get_conn()
        try:
            if path == "/api/state":
                db.ensure_crew(conn, crew)
                conn.commit()
                return self._send_json(200, db.get_state(conn, crew))
            if path == "/api/backup":
                return self._send_json(200, db.get_state(conn, crew), {
                    "Content-Disposition": f'attachment; filename="crew-health-backup-crew{crew}.json"'})
            if path == "/api/history":
                metric = (qs.get("metric", [""])[0])
                if metric not in db.VALID_METRICS:
                    return self._send_json(400, {"error": "metric must be one of " + ", ".join(db.VALID_METRICS)})
                try:
                    limit = max(1, min(500, int(qs.get("limit", [db.HIST_LIMIT])[0])))
                except ValueError:
                    limit = db.HIST_LIMIT
                return self._send_json(200, {"metric": metric, "points": db.get_history(conn, crew, metric, limit)})
            if path == "/api/hazards":
                return self._send_json(200, {"hazards": db.get_hazards(conn)})
            if path == "/api/mission":
                return self._send_json(200, {"context": db.get_mission(conn, crew)})
        finally:
            conn.close()
        return self._send_json(404, {"error": "No such endpoint"})

    def do_PUT(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path not in ("/api/state", "/api/mission"):
            return self._send_json(404, {"error": "No such endpoint"})
        data = self._body()
        if not isinstance(data, dict):
            return self._send_json(400, {"error": "Body must be a JSON object"})
        crew = self._crew(qs)
        conn = db.get_conn()
        try:
            if u.path == "/api/mission":
                try:
                    return self._send_json(200, {"context": db.set_mission(conn, crew, data.get("context"))})
                except ValueError as e:
                    return self._send_json(400, {"error": str(e)})
            return self._send_json(200, db.put_state(conn, crew, data))
        finally:
            conn.close()

    def do_POST(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        crew = self._crew(qs)
        data = self._body()
        if u.path == "/api/journal":
            text = str((data or {}).get("text", "")).strip() if isinstance(data, dict) else ""
            if not text:
                return self._send_json(400, {"error": "text is required"})
            conn = db.get_conn()
            try:
                return self._send_json(201, db.add_journal_entry(conn, crew, text))
            finally:
                conn.close()
        if u.path == "/api/restore":
            if not isinstance(data, dict):
                return self._send_json(400, {"error": "Body must be a JSON object"})
            conn = db.get_conn()
            try:
                for table in ("journal_entries", "sleep_logs", "mood_checkins", "vitals_readings"):
                    conn.execute(f"DELETE FROM {table} WHERE crew_id = ?", (crew,))
                conn.commit()
                return self._send_json(200, db.put_state(conn, crew, data))
            finally:
                conn.close()
        return self._send_json(404, {"error": "No such endpoint"})

    def do_PATCH(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        parts = [p for p in u.path.split("/") if p]
        if not (len(parts) == 3 and parts[:2] == ["api", "journal"]):
            return self._send_json(404, {"error": "No such endpoint"})
        patch = self._body()
        if not isinstance(patch, dict):
            return self._send_json(400, {"error": "Body must be a JSON object"})
        crew, eid = self._crew(qs), parts[2]
        conn = db.get_conn()
        try:
            entry = next((e for e in db.get_state(conn, crew)["journal"] if e["id"] == eid), None)
            if not entry:
                return self._send_json(404, {"error": "No such journal entry"})
            for k in ("measure", "recent", "task", "src", "ans", "areas"):
                if k in patch:
                    entry[k] = patch[k]
            if entry["task"] not in db.VALID_TASKS or entry["src"] not in db.VALID_SOURCES \
                    or not isinstance(entry["areas"], list):
                return self._send_json(400, {"error": "Invalid task, src or areas"})
            conn.execute(
                "UPDATE journal_entries SET measure=?, recent=?, task=?, source=?, ans=?, areas=? WHERE crew_id=? AND id=?",
                (str(entry["measure"]), str(entry["recent"]), entry["task"], entry["src"], str(entry["ans"]),
                 json.dumps([a for a in entry["areas"] if isinstance(a, str)]), crew, eid),
            )
            conn.commit()
            return self._send_json(200, db.get_state(conn, crew))
        finally:
            conn.close()

    def do_DELETE(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        parts = [p for p in u.path.split("/") if p]
        if len(parts) == 3 and parts[:2] == ["api", "journal"]:
            crew = self._crew(qs)
            conn = db.get_conn()
            try:
                db.delete_journal_entry(conn, crew, parts[2])
                return self._send_json(200, db.get_state(conn, crew))
            finally:
                conn.close()
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
