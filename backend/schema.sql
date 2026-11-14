-- Crew Health Companion — database schema (SQLite)
-- Normalized tables matching the frontend's data model:
--   D = { vitals: {sys,glu,bone}, src: {...}, log: [...], journal: [...], mood: {s,m,a} }
--
-- History is kept server-side even though the browser only ever holds the
-- latest snapshot: every vitals change and every mood check-in is inserted
-- as a new row, so trends can be queried later (e.g. by a flight surgeon
-- dashboard) even though the current frontend UI doesn't show that history
-- for vitals/mood yet.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crew_members (
  id            INTEGER PRIMARY KEY,
  callsign      TEXT NOT NULL,
  created_at    TEXT NOT NULL
);

-- One row per saved vitals reading. "Current" = latest row per (crew_id, metric).
CREATE TABLE IF NOT EXISTS vitals_readings (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id       INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  metric        TEXT NOT NULL CHECK (metric IN ('sys','glu','bone')),
  value         REAL,                 -- NULL means "cleared / not entered"
  source        TEXT NOT NULL DEFAULT 'self' CHECK (source IN ('self','man','sim')),
  recorded_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vitals_lookup
  ON vitals_readings (crew_id, metric, recorded_at DESC);

-- Evidence journal: one row per symptom entry. id is the client-generated
-- string id (e.g. "ls3k2z9") so the frontend's existing ids keep working.
CREATE TABLE IF NOT EXISTS journal_entries (
  id            TEXT PRIMARY KEY,
  crew_id       INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  text          TEXT NOT NULL,
  areas         TEXT NOT NULL DEFAULT '[]',  -- JSON array of area keys
  base          TEXT NOT NULL DEFAULT '[]',  -- JSON array, used for ambiguous entries
  kind          TEXT NOT NULL DEFAULT '' CHECK (kind IN ('', 'amb', 'pick')),
  ans           TEXT NOT NULL DEFAULT '',
  measure       TEXT NOT NULL DEFAULT '',
  recent        TEXT NOT NULL DEFAULT '',
  task          TEXT NOT NULL DEFAULT '' CHECK (task IN ('', 'note', 'slow', 'block')),
  source        TEXT NOT NULL DEFAULT 'self' CHECK (source IN ('self','man','sim')),
  created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_journal_crew
  ON journal_entries (crew_id, created_at DESC);

-- Daily sleep/alertness check-ins (the frontend's D.log array).
CREATE TABLE IF NOT EXISTS sleep_logs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id       INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  sleep_hours   REAL NOT NULL,
  alertness     INTEGER NOT NULL CHECK (alertness BETWEEN 1 AND 5),
  recorded_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sleep_crew
  ON sleep_logs (crew_id, recorded_at ASC);

-- Mood / stress / anxiety check-ins. "Current" = latest row per crew_id.
CREATE TABLE IF NOT EXISTS mood_checkins (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id       INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  stress        INTEGER NOT NULL CHECK (stress BETWEEN 1 AND 10),
  mood          INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 10),
  anxiety       INTEGER NOT NULL CHECK (anxiety BETWEEN 1 AND 10),
  recorded_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mood_crew
  ON mood_checkins (crew_id, recorded_at DESC);
