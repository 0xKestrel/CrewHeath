"""
Crew Health Companion: database access layer (stdlib only).

State shape shared with the frontend:
  { vitals:{sys,dia,hr,temp,glu,bone}, src:{...}, hist:{metric:[{t,v}]},
    log:[...], journal:[...], mood:{s,m,a}, mission:"iss|moon|mars", meals:{log:[]} }
"""

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crew_health.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
DEMO_CREW_ID = 1
HIST_LIMIT = 30

VALID_METRICS = ("sys", "dia", "hr", "temp", "glu", "bone")
VALID_SOURCES = ("self", "man", "sim")
VALID_TASKS = ("", "note", "slow", "block")
VALID_KINDS = ("", "amb", "pick")
VALID_MISSIONS = ("iss", "moon", "mars")

KEYWORDS = {
    "vision": re.compile(r"blur|vision|\beyes?\b|\bsee\b|seeing|double|squint|\btext\b", re.I),
    "balance": re.compile(r"dizz|balance|orient|spin|vertigo|nause|queas|unsteady", re.I),
    "alert": re.compile(r"sleep|slept|tired|alert|awake|fatigue|drows|concentrat|foggy|exhaust", re.I),
    "muscle": re.compile(r"muscle|weak|strength|endurance|sore|stamina|cramp|\blegs?\b|\barms?\b", re.I),
}
AMBIGUOUS = re.compile(r"checklist|my place|\bread|procedure|screen", re.I)


def classify(text):
    """Mirror of the frontend classify(). Returns (areas, is_ambiguous)."""
    areas = [k for k, rx in KEYWORDS.items() if rx.search(text)]
    is_amb = bool(AMBIGUOUS.search(text)) and "alert" not in areas and not (
        "vision" in areas and re.search(r"blur", text, re.I)
    )
    return areas, is_amb


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _new_id():
    return format(int(time.time() * 1000), "x")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_vitals(conn):
    """Older databases only allow metrics sys/glu/bone. Rebuild that table once."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vitals_readings'").fetchone()
    if row and "'hr'" not in row["sql"]:
        conn.execute("DROP INDEX IF EXISTS idx_vitals_lookup")
        conn.execute("ALTER TABLE vitals_readings RENAME TO vitals_old")
        return True
    return False


def init_db():
    conn = get_conn()
    migrating = _migrate_vitals(conn)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    if migrating:
        conn.execute(
            """INSERT OR IGNORE INTO vitals_readings (crew_id, metric, value, source, recorded_at)
               SELECT crew_id, metric, value, source, recorded_at FROM vitals_old"""
        )
        conn.execute("DROP TABLE vitals_old")
    if not conn.execute("SELECT 1 FROM crew_members WHERE id = ?", (DEMO_CREW_ID,)).fetchone():
        conn.execute(
            "INSERT INTO crew_members (id, callsign, created_at) VALUES (?, ?, ?)",
            (DEMO_CREW_ID, "Demo Crew Member", now_iso()),
        )
    conn.commit()
    conn.close()


def ensure_crew(conn, crew_id):
    if not conn.execute("SELECT 1 FROM crew_members WHERE id = ?", (crew_id,)).fetchone():
        conn.execute(
            "INSERT INTO crew_members (id, callsign, created_at) VALUES (?, ?, ?)",
            (crew_id, f"Crew {crew_id}", now_iso()),
        )


def _num(v):
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(round(float(v), 4))


# ---------------------------------------------------------------- read
def get_history(conn, crew_id, metric, limit=HIST_LIMIT):
    rows = conn.execute(
        """SELECT recorded_at, value FROM vitals_readings
           WHERE crew_id = ? AND metric = ? AND value IS NOT NULL
           ORDER BY recorded_at DESC, id DESC LIMIT ?""",
        (crew_id, metric, limit),
    ).fetchall()
    return [{"t": r["recorded_at"], "v": r["value"]} for r in reversed(rows)]


def get_mission(conn, crew_id):
    row = conn.execute("SELECT context FROM mission_context WHERE crew_id = ?", (crew_id,)).fetchone()
    return row["context"] if row else "iss"


def set_mission(conn, crew_id, context):
    if context not in VALID_MISSIONS:
        raise ValueError("context must be one of " + ", ".join(VALID_MISSIONS))
    ensure_crew(conn, crew_id)
    conn.execute(
        """INSERT INTO mission_context (crew_id, context, updated_at) VALUES (?,?,?)
           ON CONFLICT(crew_id) DO UPDATE SET context=excluded.context, updated_at=excluded.updated_at""",
        (crew_id, context, now_iso()),
    )
    conn.commit()
    return context


def get_hazards(conn):
    out = []
    for h in conn.execute("SELECT key, position, name, summary FROM hazards ORDER BY position"):
        ind = {"vital": [], "area": [], "checkin": []}
        for r in conn.execute("SELECT kind, indicator FROM hazard_indicators WHERE hazard_key = ?", (h["key"],)):
            ind[r["kind"]].append(r["indicator"])
        out.append({"key": h["key"], "position": h["position"], "name": h["name"],
                    "summary": h["summary"], "indicators": ind})
    return out


def _snapshot(conn, crew_id):
    row = conn.execute("SELECT body FROM client_snapshots WHERE crew_id = ?", (crew_id,)).fetchone()
    try:
        return json.loads(row["body"]) if row else {}
    except ValueError:
        return {}


def get_state(conn, crew_id):
    vitals = {m: "" for m in VALID_METRICS}
    src = {m: "self" for m in VALID_METRICS}
    for metric in VALID_METRICS:
        row = conn.execute(
            """SELECT value, source FROM vitals_readings WHERE crew_id = ? AND metric = ?
               ORDER BY recorded_at DESC, id DESC LIMIT 1""",
            (crew_id, metric),
        ).fetchone()
        if row:
            vitals[metric] = _num(row["value"])
            src[metric] = row["source"]
    hist = {m: get_history(conn, crew_id, m) for m in VALID_METRICS}

    snap = _snapshot(conn, crew_id)
    followups = {str(e.get("id")): e.get("followups") or [] for e in snap.get("journal", []) if isinstance(e, dict)}
    journal = []
    for row in conn.execute(
        "SELECT * FROM journal_entries WHERE crew_id = ? ORDER BY created_at DESC, rowid DESC", (crew_id,)
    ):
        journal.append({
            "id": row["id"], "t": row["created_at"], "text": row["text"],
            "areas": json.loads(row["areas"]), "base": json.loads(row["base"]),
            "kind": row["kind"], "ans": row["ans"], "measure": row["measure"],
            "recent": row["recent"], "task": row["task"], "src": row["source"],
            "followups": followups.get(row["id"], []),
        })

    log = [
        {"t": r["recorded_at"], "sleep": r["sleep_hours"], "alert": r["alertness"]}
        for r in conn.execute(
            "SELECT recorded_at, sleep_hours, alertness FROM sleep_logs WHERE crew_id = ? ORDER BY recorded_at ASC, id ASC",
            (crew_id,),
        )
    ]
    m = conn.execute(
        "SELECT stress, mood, anxiety FROM mood_checkins WHERE crew_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
        (crew_id,),
    ).fetchone()
    mood = {"s": m["stress"], "m": m["mood"], "a": m["anxiety"]} if m else {"s": 5, "m": 6, "a": 4}

    meals = snap.get("meals") if isinstance(snap.get("meals"), dict) else {"log": []}
    return {"vitals": vitals, "src": src, "hist": hist, "log": log, "journal": journal,
            "mood": mood, "mission": get_mission(conn, crew_id), "meals": meals}


# ---------------------------------------------------------------- write
def put_state(conn, crew_id, data):
    ensure_crew(conn, crew_id)
    ts = now_iso()
    vitals = data.get("vitals") or {}
    src = data.get("src") or {}
    hist = data.get("hist") if isinstance(data.get("hist"), dict) else {}

    for metric in VALID_METRICS:
        source = src.get(metric) if src.get(metric) in VALID_SOURCES else "self"
        # 1) replay client history; the unique index makes this idempotent
        for pt in (hist.get(metric) or [])[-HIST_LIMIT:]:
            try:
                v, t = float(pt.get("v")), str(pt.get("t") or "")
            except (TypeError, ValueError, AttributeError):
                continue
            if t:
                conn.execute(
                    "INSERT OR IGNORE INTO vitals_readings (crew_id, metric, value, source, recorded_at) VALUES (?,?,?,?,?)",
                    (crew_id, metric, v, source, t),
                )
        # 2) fall back to a change-only row when the client sent no history for it
        raw = vitals.get(metric, "")
        try:
            value = None if raw in ("", None) else float(raw)
        except (TypeError, ValueError):
            value = None
        latest = conn.execute(
            """SELECT value, source FROM vitals_readings WHERE crew_id = ? AND metric = ?
               ORDER BY recorded_at DESC, id DESC LIMIT 1""",
            (crew_id, metric),
        ).fetchone()
        if (latest is None and value is not None) or (
            latest is not None and (latest["value"] != value or latest["source"] != source)
        ):
            conn.execute(
                "INSERT OR IGNORE INTO vitals_readings (crew_id, metric, value, source, recorded_at) VALUES (?,?,?,?,?)",
                (crew_id, metric, value, source, ts),
            )

    keep = []
    for e in data.get("journal") or []:
        eid = str(e.get("id") or "")
        if not eid:
            continue
        keep.append(eid)
        areas = [a for a in (e.get("areas") or []) if isinstance(a, str)]
        base = [a for a in (e.get("base") or []) if isinstance(a, str)]
        kind = e.get("kind") if e.get("kind") in VALID_KINDS else ""
        task = e.get("task") if e.get("task") in VALID_TASKS else ""
        source = e.get("src") if e.get("src") in VALID_SOURCES else "self"
        conn.execute(
            """INSERT INTO journal_entries
                 (id, crew_id, text, areas, base, kind, ans, measure, recent, task, source, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 text=excluded.text, areas=excluded.areas, base=excluded.base, kind=excluded.kind,
                 ans=excluded.ans, measure=excluded.measure, recent=excluded.recent,
                 task=excluded.task, source=excluded.source""",
            (eid, crew_id, str(e.get("text") or ""), json.dumps(areas), json.dumps(base), kind,
             str(e.get("ans") or ""), str(e.get("measure") or ""), str(e.get("recent") or ""),
             task, source, str(e.get("t") or ts)),
        )
    if keep:
        conn.execute(
            f"DELETE FROM journal_entries WHERE crew_id = ? AND id NOT IN ({','.join('?' for _ in keep)})",
            (crew_id, *keep),
        )
    else:
        conn.execute("DELETE FROM journal_entries WHERE crew_id = ?", (crew_id,))

    conn.execute("DELETE FROM sleep_logs WHERE crew_id = ?", (crew_id,))
    for entry in data.get("log") or []:
        try:
            sleep_hours, alertness = float(entry.get("sleep")), int(entry.get("alert"))
        except (TypeError, ValueError, AttributeError):
            continue
        if 1 <= alertness <= 5:
            conn.execute(
                "INSERT INTO sleep_logs (crew_id, sleep_hours, alertness, recorded_at) VALUES (?,?,?,?)",
                (crew_id, sleep_hours, alertness, str(entry.get("t") or ts)),
            )

    mood = data.get("mood") or {}
    try:
        s, m, a = int(mood.get("s", 5)), int(mood.get("m", 6)), int(mood.get("a", 4))
    except (TypeError, ValueError):
        s, m, a = 5, 6, 4
    s, m, a = (max(1, min(10, x)) for x in (s, m, a))
    last = conn.execute(
        "SELECT stress, mood, anxiety FROM mood_checkins WHERE crew_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
        (crew_id,),
    ).fetchone()
    if not last or (last["stress"], last["mood"], last["anxiety"]) != (s, m, a):
        conn.execute(
            "INSERT INTO mood_checkins (crew_id, stress, mood, anxiety, recorded_at) VALUES (?,?,?,?,?)",
            (crew_id, s, m, a, ts),
        )

    if data.get("mission") in VALID_MISSIONS:
        conn.execute(
            """INSERT INTO mission_context (crew_id, context, updated_at) VALUES (?,?,?)
               ON CONFLICT(crew_id) DO UPDATE SET context=excluded.context, updated_at=excluded.updated_at""",
            (crew_id, data["mission"], ts),
        )

    conn.execute(
        """INSERT INTO client_snapshots (crew_id, body, updated_at) VALUES (?,?,?)
           ON CONFLICT(crew_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at""",
        (crew_id, json.dumps({"journal": data.get("journal") or [], "meals": data.get("meals") or {"log": []}}), ts),
    )
    conn.commit()
    return get_state(conn, crew_id)


def add_journal_entry(conn, crew_id, text):
    ensure_crew(conn, crew_id)
    areas, is_amb = classify(text)
    base = [a for a in areas if a not in ("vision", "alert")]
    entry = {
        "id": _new_id(), "t": now_iso(), "text": text,
        "areas": base if is_amb else areas, "base": base if is_amb else [],
        "kind": "amb" if is_amb else ("pick" if not areas else ""),
        "ans": "", "measure": "", "recent": "", "task": "", "src": "self", "followups": [],
    }
    conn.execute(
        """INSERT INTO journal_entries
             (id, crew_id, text, areas, base, kind, ans, measure, recent, task, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (entry["id"], crew_id, text, json.dumps(entry["areas"]), json.dumps(entry["base"]),
         entry["kind"], "", "", "", "", "self", entry["t"]),
    )
    conn.commit()
    return entry


def delete_journal_entry(conn, crew_id, entry_id):
    conn.execute("DELETE FROM journal_entries WHERE crew_id = ? AND id = ?", (crew_id, entry_id))
    conn.commit()
