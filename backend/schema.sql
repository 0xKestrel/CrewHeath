-- Crew Health Companion: schema v4 (SQLite)
-- Adds diastolic BP, heart rate, core temperature, mission context,
-- hazard reference tables, and a lossless client snapshot.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crew_members (
  id          INTEGER PRIMARY KEY,
  callsign    TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

-- One row per saved reading. Temperature is always stored in degrees C.
CREATE TABLE IF NOT EXISTS vitals_readings (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id     INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  metric      TEXT NOT NULL CHECK (metric IN ('sys','dia','hr','temp','glu','bone')),
  value       REAL,
  source      TEXT NOT NULL DEFAULT 'self' CHECK (source IN ('self','man','sim')),
  recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vitals_lookup ON vitals_readings (crew_id, metric, recorded_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_vitals_uniq ON vitals_readings (crew_id, metric, recorded_at);

CREATE TABLE IF NOT EXISTS journal_entries (
  id          TEXT PRIMARY KEY,
  crew_id     INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  areas       TEXT NOT NULL DEFAULT '[]',
  base        TEXT NOT NULL DEFAULT '[]',
  kind        TEXT NOT NULL DEFAULT '' CHECK (kind IN ('', 'amb', 'pick')),
  ans         TEXT NOT NULL DEFAULT '',
  measure     TEXT NOT NULL DEFAULT '',
  recent      TEXT NOT NULL DEFAULT '',
  task        TEXT NOT NULL DEFAULT '' CHECK (task IN ('', 'note', 'slow', 'block')),
  source      TEXT NOT NULL DEFAULT 'self' CHECK (source IN ('self','man','sim')),
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_journal_crew ON journal_entries (crew_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sleep_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id     INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  sleep_hours REAL NOT NULL,
  alertness   INTEGER NOT NULL CHECK (alertness BETWEEN 1 AND 5),
  recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sleep_crew ON sleep_logs (crew_id, recorded_at ASC);

CREATE TABLE IF NOT EXISTS mood_checkins (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  crew_id     INTEGER NOT NULL REFERENCES crew_members(id) ON DELETE CASCADE,
  stress      INTEGER NOT NULL CHECK (stress BETWEEN 1 AND 10),
  mood        INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 10),
  anxiety     INTEGER NOT NULL CHECK (anxiety BETWEEN 1 AND 10),
  recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mood_crew ON mood_checkins (crew_id, recorded_at DESC);

-- Mission context: drives the communication-delay guidance in the UI.
CREATE TABLE IF NOT EXISTS mission_context (
  crew_id     INTEGER PRIMARY KEY REFERENCES crew_members(id) ON DELETE CASCADE,
  context     TEXT NOT NULL DEFAULT 'iss' CHECK (context IN ('iss','moon','mars')),
  updated_at  TEXT NOT NULL
);

-- Full client JSON, so data the normalized tables don't model (meals,
-- journal follow-ups) survives a restore from the server.
CREATE TABLE IF NOT EXISTS client_snapshots (
  crew_id     INTEGER PRIMARY KEY REFERENCES crew_members(id) ON DELETE CASCADE,
  body        TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- NASA's five spaceflight hazards and the indicators this app links to each.
CREATE TABLE IF NOT EXISTS hazards (
  key         TEXT PRIMARY KEY,
  position    INTEGER NOT NULL,
  name        TEXT NOT NULL,
  summary     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hazard_indicators (
  hazard_key  TEXT NOT NULL REFERENCES hazards(key) ON DELETE CASCADE,
  kind        TEXT NOT NULL CHECK (kind IN ('vital','area','checkin')),
  indicator   TEXT NOT NULL,
  PRIMARY KEY (hazard_key, kind, indicator)
);

INSERT OR IGNORE INTO hazards (key, position, name, summary) VALUES
 ('rad', 1, 'Space radiation', 'Radiation raises long-term health risk. Dose is tracked by dosimeters; this app tracks possible symptoms.'),
 ('grav',2, 'Altered gravity fields', 'Bone and muscle loss, plus fluid shifts that affect blood pressure and heart rate.'),
 ('iso', 3, 'Isolation and confinement', 'Sleep, alertness, mood and stress change in small crews over long missions.'),
 ('dist',4, 'Distance from Earth', 'Communication delay means the crew must act on protocol before help can reply.'),
 ('env', 5, 'Hostile and closed environments', 'Temperature, air quality and a closed habitat affect heart rate, temperature, vision and balance.');

INSERT OR IGNORE INTO hazard_indicators (hazard_key, kind, indicator) VALUES
 ('rad','area','balance'),('rad','area','alert'),
 ('grav','vital','bone'),('grav','vital','sys'),('grav','vital','dia'),('grav','vital','hr'),
 ('grav','area','muscle'),('grav','area','bones'),('grav','area','balance'),
 ('iso','area','alert'),('iso','checkin','sleep'),('iso','checkin','mood'),
 ('dist','checkin','mission_context'),
 ('env','vital','temp'),('env','vital','hr'),('env','vital','glu'),
 ('env','area','vision'),('env','area','balance');
