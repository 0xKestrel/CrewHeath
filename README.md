# Crew Health Companion — full stack

Three tiers, wired together and tested:

- **Frontend** — `frontend/index.html`. Your existing v3 build (body map, evidence
  journal, trends chart, handoff summary, offline guide, backup/restore), unchanged
  except for its data layer, which now syncs with the server.
- **Backend** — `backend/server.py`. A REST API, zero third-party dependencies.
- **Database** — `backend/schema.sql`, a normalized SQLite schema, created automatically
  as `backend/crew_health.db` on first run.

## Run it

Requires only Python 3 (no `pip install`, no Node, no Docker):

```bash
cd backend
python3 server.py
```

Open **http://localhost:8000**. That's the whole setup — the same server answers
the API and serves the page, so there's no separate frontend process and no
cross-origin configuration.

Pass a different port if 8000 is taken: `python3 server.py 8080`.

## Why this stack

This environment can't run `pip install` or `npm install`, so every piece here
uses only what ships with Python itself: `http.server` for the web server,
`sqlite3` for the database, `json` and `re` for everything else. That turned out
to be a reasonable choice regardless of that constraint — it means the whole
backend is two readable files, with nothing to install anywhere it eventually runs.

## Architecture

```
frontend/index.html  ──fetch()──►  backend/server.py  ──sqlite3──►  backend/crew_health.db
     (your UI,                      (REST API +                    (5 normalized tables,
      unchanged)                   static file host)                 see schema.sql)
```

**Sync model.** The frontend keeps its original `localStorage` cache for instant,
offline-capable reads and writes — nothing about how it *feels* to use changes.
On top of that:

- Every `save()` now also pushes the full state to `PUT /api/state` (debounced
  400ms, so dragging a mood slider doesn't fire a request per pixel).
- On load, the page pulls `GET /api/state`. If the server already has data,
  the server wins (that's what makes "my phone got reset / I'm on a new
  device" actually recoverable). If the server is empty but this browser has
  cached data, the browser's copy seeds the server instead — so the very
  first run on a brand-new backend doesn't wipe anything.
- If the network call fails, the page falls back to the local cache silently
  and shows **● Offline (local only)** in the top bar; the next successful
  save flushes everything queued since then.
- A 15-second background poll (paused while the tab is hidden) picks up
  changes made from another tab or device without a manual reload.
- **Demo mode is intentionally local-only.** Clicking "Try demo case" never
  touches the network or the database — it's a sandbox, exactly as before.

## Database schema

| Table | Purpose | Notable choice |
|---|---|---|
| `crew_members` | One row per astronaut. The app currently always uses `id=1`, but every table already has `crew_id`, so adding a second crew member needs no schema change — only a login/selection screen on the frontend. | — |
| `vitals_readings` | Every blood pressure / blood sugar / bone T-score reading. | The frontend only ever shows the *latest* value, but the server keeps every change as a new row — so there's already a real history to chart later, even though no UI reads it yet. A new row is only inserted when the value or source actually changed. |
| `journal_entries` | The evidence journal: text, classified areas, the clarifying answer, measurement, what changed, task impact, source. | Primary key is the same id the frontend already generates, so entries can be upserted idempotently. |
| `sleep_logs` | The daily sleep-hours / alertness check-ins behind the Trends chart. | No stable per-entry id exists on the client, so this table is fully resynced from the array each save — same result, no duplicates. |
| `mood_checkins` | Stress / mood / anxiety sliders. | Same change-only-inserts pattern as vitals. |

Full column definitions and constraints are in `backend/schema.sql`.

## REST API

All endpoints take `?crew_id=1` (default `1` if omitted). Bodies and responses
are JSON.

| Method & path | What it does |
|---|---|
| `GET /api/ping` | Health check. |
| `GET /api/state` | Returns the full current state in the shape the frontend expects. |
| `PUT /api/state` | Replaces vitals/journal/log/mood from a full state object — what the frontend calls on every save. History-aware (see above), not a destructive overwrite. |
| `POST /api/journal` | `{"text": "..."}` → classifies the symptom text with the same rules as the frontend's JS and inserts one journal entry. For other clients (e.g. a future mobile app) that want to add one entry without resending everything. |
| `PATCH /api/journal/<id>` | Partial update to one entry's `ans`, `areas`, `measure`, `recent`, `task`, or `src`. |
| `DELETE /api/journal/<id>` | Removes one entry. |
| `GET /api/backup` | Downloads the current state as a JSON file, generated straight from the database — independent of any one browser's local backup. |
| `POST /api/restore` | Replaces all of a crew member's data from a JSON payload shaped like `GET /api/state`'s response. |

The frontend itself only uses `GET/PUT /api/state` for simplicity and
reliability; the granular journal endpoints are tested and ready for a second
client (a flight-surgeon dashboard, a mobile app) that shouldn't have to
resend the whole state to log one symptom.

## What was tested

Every endpoint was exercised directly (not just read through) before
delivery: a full `PUT`/`GET` round trip; all three journal-classification
cases (an ambiguous phrase, a clear vision match, a clear muscle match)
checked against the server's output; `PATCH` and `DELETE` on a real entry,
confirmed against the updated state; the backup endpoint's download headers;
malformed-JSON input confirmed to return `400` without crashing the server;
two crew members confirmed fully isolated from each other; and a full
server kill-and-restart against the same database file, confirmed to come
back with every value intact.

## Honest limitations

- **Single demo user.** The schema supports many crew members; the app UI
  does not yet have a way to choose or log in as one. Everything currently
  reads/writes `crew_id=1`.
- **No authentication.** Anyone who can reach the server can read or change
  the data. Fine for a local demo; not fine for anything with real health
  data.
- **No HTTPS.** `http.server` serves plain HTTP. A real deployment needs TLS
  in front of it (a reverse proxy, or a managed host).
- **SQLite, not a server database.** Perfect for one server process on one
  machine; a true multi-server NASA deployment would move this to Postgres
  with the same schema shape and swap `sqlite3` calls for a driver.
- **Vitals/mood ranges are still placeholders**, inherited from the existing
  frontend. They need review by flight surgeons and NASA Human Research
  Program sources before anyone relies on them for a real decision.
- **No camera input**, by your earlier request.
- **Cross-device sync is poll-based**, not instant (15-second interval). A
  production version would use WebSockets or server-sent events for the
  flight-surgeon-views-it-live case.

## Next steps, in order of what unlocks the most

1. A login/crew-selection screen, so `crew_id` isn't hardcoded.
2. Move from SQLite to Postgres if this needs to run across more than one
   server process at once.
3. Put the server behind HTTPS and add authentication.
4. Replace the placeholder vitals ranges and journal advice with content
   reviewed by flight surgeons and NASA HRP sources.
