"""
Crew Health Companion — database access layer.

Stdlib-only (sqlite3). Turns the normalized tables in schema.sql into the
exact JSON shape the frontend already works with:

    { vitals: {sys,glu,bone}, src: {sys,glu,bone}, log: [...], journal: [...], mood: {s,m,a} }

and turns that same shape back into rows when the frontend saves.
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crew_health.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
DEMO_CREW_ID = 1  # single-crew demo; see README for how this would extend

VALID_METRICS = ("sys", "glu", "bone")
VALID_SOURCES = ("self", "man", "sim")
VALID_TASKS = ("", "note", "slow", "block")
VALID_KINDS = ("", "amb", "pick")

# ---------------------------------------------------------------------------
# Symptom classification — ported line-for-line from the frontend's JS so a
# journal entry gets the same areas/kind whether it's created online or the
# browser later replays an offline-queued save.
# ---------------------------------------------------------------------------
KEYWORDS = {
    "vision": re.compile(r"blur|vision|\beyes?\b|\bsee\b|seeing|double|squint|\btext\b", re.I),
    "balance": re.compile(r"dizz|balance|orient|spin|vertigo|nause|queas|unsteady", re.I),
    "alert": re.compile(r"sleep|slept|tired|alert|awake|fatigue|drows|concentrat|foggy|exhaust", re.I),
    "muscle": re.compile(r"muscle|weak|strength|endurance|sore|stamina|cramp|\blegs?\b|\barms?\b", re.I),
}
AMBIGUOUS = re.compile(r"checklist|my place|\bread|procedure|screen", re.I)


def classify(text):
    """Mirrors the frontend's classify(t). Returns (areas, is_ambiguous)."""
    areas = [k for k, rx in KEYWORDS.items() if rx.search(text)]
    is_amb = bool(AMBIGUOUS.search(text)) and "alert" not in areas and not (
        "vision" in areas and re.search(r"blur", text, re.I)
    )
    return areas, is_amb


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Connection / schema setup
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    first_time = not os.path.exists(DB_PATH)
    conn = get_conn()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    if first_time:
        conn.execute(
            "INSERT INTO crew_members (id, callsign, created_at) VALUES (?, ?, ?)",
            (DEMO_CREW_ID, "Demo Crew Member", now_iso()),
        )
        conn.commit()
    conn.close()


def ensure_crew(conn, crew_id):
    row = conn.execute("SELECT id FROM crew_members WHERE id = ?", (crew_id,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO crew_members (id, callsign, created_at) VALUES (?, ?, ?)",
            (crew_id, f"Crew {crew_id}", now_iso()),
        )


# ---------------------------------------------------------------------------
# Read: assemble the frontend's D object from normalized rows
# ---------------------------------------------------------------------------
def get_state(conn, crew_id):
    vitals = {"sys": "", "glu": "", "bone": ""}
    src = {"sys": "self", "glu": "self", "bone": "self"}
    for metric in VALID_METRICS:
        row = conn.execute(
            """SELECT value, source FROM vitals_readings
               WHERE crew_id = ? AND metric = ?
               ORDER BY recorded_at DESC, id DESC LIMIT 1""",
            (crew_id, metric),
        ).fetchone()
        if row:
            vitals[metric] = "" if row["value"] is None else _num(row["value"])
            src[metric] = row["source"]

    journal = []
    for row in conn.execute(
        "SELECT * FROM journal_entries WHERE crew_id = ? ORDER BY created_at DESC, rowid DESC",
        (crew_id,),
    ):
        journal.append({
            "id": row["id"],
            "t": row["created_at"],
            "text": row["text"],
            "areas": json.loads(row["areas"]),
            "base": json.loads(row["base"]),
            "kind": row["kind"],
            "ans": row["ans"],
            "measure": row["measure"],
            "recent": row["recent"],
            "task": row["task"],
            "src": row["source"],
        })

    log = [
        {"t": row["recorded_at"], "sleep": row["sleep_hours"], "alert": row["alertness"]}
        for row in conn.execute(
            "SELECT recorded_at, sleep_hours, alertness FROM sleep_logs WHERE crew_id = ? ORDER BY recorded_at ASC, id ASC",
            (crew_id,),
        )
    ]

    mood_row = conn.execute(
        "SELECT stress, mood, anxiety FROM mood_checkins WHERE crew_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
        (crew_id,),
    ).fetchone()
    mood = {"s": mood_row["stress"], "m": mood_row["mood"], "a": mood_row["anxiety"]} if mood_row else {"s": 5, "m": 6, "a": 4}

    return {"vitals": vitals, "src": src, "log": log, "journal": journal, "mood": mood}


def _num(v):
    """Render a stored REAL as the frontend expects: '120' not '120.0'."""
    if v is None:
        return ""
    if float(v).is_integer():
        return str(int(v))
    return str(v)


# ---------------------------------------------------------------------------
# Write: decompose an incoming D object into the normalized tables.
#
# Vitals/mood only grow a new history row when the value actually changed,
# so dragging a slider back and forth doesn't flood the table. Journal is a
# true upsert-by-id plus delete-what's-missing, because the frontend already
# manages that list (add/edit/delete) and always sends the full list back.
# Sleep log entries have no id in the frontend, so the whole log array is
# resynced (idempotent: same array in -> same rows out).
# ---------------------------------------------------------------------------
def put_state(conn, crew_id, data):
    ensure_crew(conn, crew_id)
    ts = now_iso()

    # --- vitals: insert a new row only on change ---
    vitals = data.get("vitals") or {}
    src = data.get("src") or {}
    for metric in VALID_METRICS:
        raw = vitals.get(metric, "")
        value = None
        if raw not in ("", None):
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = None
        source = src.get(metric) if src.get(metric) in VALID_SOURCES else "self"

        latest = conn.execute(
            """SELECT value, source FROM vitals_readings
               WHERE crew_id = ? AND metric = ? ORDER BY recorded_at DESC, id DESC LIMIT 1""",
            (crew_id, metric),
        ).fetchone()
        changed = (latest is None) or (latest["value"] != value) or (latest["source"] != source)
        if changed and not (latest is None and value is None):
            conn.execute(
                "INSERT INTO vitals_readings (crew_id, metric, value, source, recorded_at) VALUES (?,?,?,?,?)",
                (crew_id, metric, value, source, ts),
            )

    # --- journal: upsert by id, delete anything no longer present ---
    incoming = data.get("journal") or []
    keep_ids = []
    for e in incoming:
        eid = str(e.get("id") or "")
        if not eid:
            continue
        keep_ids.append(eid)
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
                 text=excluded.text, areas=excluded.areas, base=excluded.base,
                 kind=excluded.kind, ans=excluded.ans, measure=excluded.measure,
                 recent=excluded.recent, task=excluded.task, source=excluded.source""",
            (eid, crew_id, str(e.get("text") or ""), json.dumps(areas), json.dumps(base),
             kind, str(e.get("ans") or ""), str(e.get("measure") or ""), str(e.get("recent") or ""),
             task, source, str(e.get("t") or ts)),
        )
    if keep_ids:
        placeholders = ",".join("?" for _ in keep_ids)
        conn.execute(
            f"DELETE FROM journal_entries WHERE crew_id = ? AND id NOT IN ({placeholders})",
            (crew_id, *keep_ids),
        )
    else:
        conn.execute("DELETE FROM journal_entries WHERE crew_id = ?", (crew_id,))

    # --- sleep log: resync the whole array (no stable ids on the client) ---
    incoming_log = data.get("log") or []
    conn.execute("DELETE FROM sleep_logs WHERE crew_id = ?", (crew_id,))
    for entry in incoming_log:
        try:
            sleep_hours = float(entry.get("sleep"))
            alertness = int(entry.get("alert"))
        except (TypeError, ValueError):
            continue
        if not (1 <= alertness <= 5):
            continue
        conn.execute(
            "INSERT INTO sleep_logs (crew_id, sleep_hours, alertness, recorded_at) VALUES (?,?,?,?)",
            (crew_id, sleep_hours, alertness, str(entry.get("t") or ts)),
        )

    # --- mood: insert a new row only on change ---
    mood = data.get("mood") or {}
    try:
        s, m, a = int(mood.get("s", 5)), int(mood.get("m", 6)), int(mood.get("a", 4))
    except (TypeError, ValueError):
        s, m, a = 5, 6, 4
    s, m, a = max(1, min(10, s)), max(1, min(10, m)), max(1, min(10, a))
    latest_mood = conn.execute(
        "SELECT stress, mood, anxiety FROM mood_checkins WHERE crew_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
        (crew_id,),
    ).fetchone()
    if not latest_mood or (latest_mood["stress"], latest_mood["mood"], latest_mood["anxiety"]) != (s, m, a):
        conn.execute(
            "INSERT INTO mood_checkins (crew_id, stress, mood, anxiety, recorded_at) VALUES (?,?,?,?,?)",
            (crew_id, s, m, a, ts),
        )

    conn.commit()
    return get_state(conn, crew_id)


def add_journal_entry(conn, crew_id, text):
    """Server-side equivalent of the frontend's addEntry(): classify and insert."""
    ensure_crew(conn, crew_id)
    areas, is_amb = classify(text)
    base = [a for a in areas if a not in ("vision", "alert")]
    entry = {
        "id": _new_id(),
        "t": now_iso(),
        "text": text,
        "areas": base if is_amb else areas,
        "base": base if is_amb else [],
        "kind": "amb" if is_amb else ("pick" if not areas else ""),
        "ans": "", "measure": "", "recent": "", "task": "", "src": "self",
    }
    conn.execute(
        """INSERT INTO journal_entries
             (id, crew_id, text, areas, base, kind, ans, measure, recent, task, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (entry["id"], crew_id, entry["text"], json.dumps(entry["areas"]), json.dumps(entry["base"]),
         entry["kind"], entry["ans"], entry["measure"], entry["recent"], entry["task"], entry["src"], entry["t"]),
    )
    conn.commit()
    return entry


def delete_journal_entry(conn, crew_id, entry_id):
    conn.execute("DELETE FROM journal_entries WHERE crew_id = ? AND id = ?", (crew_id, entry_id))
    conn.commit()


def _new_id():
    import time
    return format(int(time.time() * 1000), "x")
