# Crew Health Companion

> **2026 NASA Space Apps Challenge** — *Create Health Monitoring Software for Astronauts on Space Missions*

**Crew Health Companion** is an offline-first, self-assessment and health-monitoring tool designed for astronauts on long-duration spaceflight missions. Built with zero external runtime dependencies, it empowers crew members to log physiological vitals, evaluate symptoms through an interactive anatomical body map, manage mission nutrition schedules, track sleep and behavioral trends, and account for deep-space communication delays when coordinating with ground flight surgeons.

---

## Table of Contents

- [Challenge Context & Problem Statement](#challenge-context--problem-statement)
- [Key Features](#key-features)
- [Mapping to NASA's 5 Hazards of Human Spaceflight](#mapping-to-nasas-5-hazards-of-human-spaceflight)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Data Privacy & Disclaimers](#data-privacy--disclaimers)

---

## Challenge Context & Problem Statement

As human exploration pushes beyond Low Earth Orbit toward the Moon (Artemis) and Mars, crews face prolonged exposure to space radiation, microgravity, isolation, closed habitats, and significant communication delays with Earth. Because real-time ground support is not always possible, astronauts must be equipped to monitor, assess, and act on their own physical and behavioral health.

**Crew Health Companion** addresses this challenge by providing:
- **At-a-glance status interpretation** with color-coded gauges (`Within demo range`, `Review`, `Flagged / Outside range`).
- **Guided self-assessment** that never assumes prior medical expertise, offering step-by-step measurement instructions (e.g., resting blood pressure protocols) and clarifying questions.
- **Autonomous decision support** that respects mission schedules and communication latency without taking unprompted actions.

---

## Key Features

### 1. Mission Dashboard & Actionable Next Steps (`Home`)
- **Smart Triage (`Next Action`):** Dynamically prioritizes what needs attention—whether an unlogged meal with an open schedule gap, an ambiguous symptom needing clarification, or an out-of-range vital sign.
- **Daily Checklist (`Still to do`):** Tracks daily blood pressure, blood sugar, sleep check-ins, and meal logs.
- **Interactive Demo Case:** Includes a one-click **Try demo case** mode pre-populated with a fictional astronaut's telemetry, meal logs, history, and simulated escalation banners.

### 2. Physiological Vitals Monitoring (`Vitals`)
- Tracks key spaceflight indicators: **Blood Pressure (Systolic/Diastolic)**, **Heart Rate**, **Core Body Temperature**, **Blood Sugar (mg/dL)**, and **Bone Density T-score**.
- Visual range gauges with source attribution (`Self-reported`, `Manual measurement`, `Simulated demo data`) and plausibility checks to catch entry errors.
- Built-in **How to measure** step-by-step protocol guides.

### 3. Interactive Body Map & Symptom Check (`Check`)
- **Natural-Language Symptom Parsing:** Crew members describe symptoms in plain text (e.g., *"I keep losing my place on the checklist"*). Ambiguous inputs trigger a single clarifying question rather than guessing a diagnosis.
- **Clickable Anatomical Figure:** Highlights affected regions (**Vision**, **Balance**, **Sleep & Alertness**, **Muscle Strength & Endurance**, **Bones**) and explains the spaceflight physiology behind each system.

### 4. Evidence Journal & Medical Handoff (`Journal`)
- Structured longitudinal tracking for each reported concern: measurements, recent environmental/task changes, operational impact (`I notice it`, `It slows my task`, `I can't do the task`), and timestamped **Follow-up** timelines (`Better`, `About the same`, `Worse`).
- **Plain-Text Flight Surgeon Handoff:** Generates a clean, copyable summary of vitals, recent meals, and active concerns ready for transmission over mission comms.

### 5. Deep-Space Communication Delay & Medical Support Modal
- Calculates expected turnaround times based on **one-way signal delay** and **team review time** (configurable for LEO/ISS, Lunar, or Mars transit scenarios), displaying an exact timeline from transmission to expected reply.

### 6. Adaptive Diet & Schedule Planner (`Diet Plan`)
- Tracks daily meals (`Breakfast`, `Lunch`, `Dinner`) alongside a timeline of mission tasks (exercise, science experiments, station maintenance, ground calls).
- **Non-Intrusive Rescheduling:** When a meal is marked *Missed*, the scheduler finds the earliest free 30-minute gap that maintains a 90-minute buffer from other meals without moving mission tasks—allowing the astronaut to *Accept*, *Keep original*, or *Dismiss*.
- Filters a mission menu by saved dietary restrictions (`No dairy`, `No gluten`, `No nuts`, `No eggs`, `Vegetarian`) and preferences (`Savory`, `Sweet`, `Light`).

### 7. Behavioral Health & Circadian Trends (`Trends`)
- Dual-axis SVG chart plotting **Sleep Hours** against **Alertness (1–5)** to detect hidden fatigue (e.g., steady sleep hours accompanied by dropping alertness).
- Interactive sliders for daily **Stress**, **Mood**, and **Anxiety (1–10)** with supportive prompts when stress or anxiety thresholds are elevated.

### 8. Medical History, Offline Reference Guide & Backup (`History`, `Guide`, `Backup`)
- **Offline Reference Guide:** Built-in summaries sourced from NASA's Human Research Program (SANS, sensorimotor/motion sickness, circadian desynchronization, exercise countermeasures, space radiation, and bone fracture risk).
- **Medical History:** Add dated historical notes or import validated JSON history files with pre-import duplicate detection and preview.
- **Local Persistence & JSON Portability:** Works 100% offline via `localStorage` or backed by a lightweight SQLite API, with full JSON export/restore.

---

## Mapping to NASA's 5 Hazards of Human Spaceflight

The database schema (`schema.sql`) and UI directly map NASA Human Research Program (HRP) hazards to measurable indicators:

| Spaceflight Hazard | Tracked Indicators & App Modules |
| :--- | :--- |
| **Space Radiation** | Dosimeter reference guidance, neurological/balance & alertness symptom tracking |
| **Altered Gravity Fields** | Bone density T-score, blood pressure, heart rate, muscle strength/endurance, balance |
| **Isolation & Confinement** | Daily sleep hours, alertness ratings, stress/mood/anxiety sliders |
| **Distance from Earth** | Mission context (`ISS`, `Moon`, `Mars`), signal-delay reply timeline, autonomous triage |
| **Hostile & Closed Environments** | Core temperature, heart rate, blood glucose, vision (SANS), adaptive nutrition |

---

## Architecture & Tech Stack

- **Frontend:** Vanilla HTML5, CSS3 (custom dark/light "Mission Control" design system with responsive mobile dock & desktop sidebar), and zero-dependency ES6+ JavaScript.
- **Backend (Optional / Full-Stack Mode):** Python 3 standard library (`http.server.ThreadingHTTPServer`, `sqlite3`) — zero `pip` packages required.
- **Database:** SQLite (`crew_health.db`) with normalized tables for vitals history, journal entries, sleep logs, mood check-ins, mission context, NASA hazard mappings, and lossless client state snapshots.

---

## Project Structure

```text
├── frontend/
│   └── index.html        # Complete single-file offline-capable web application
├── backend/              # (or root directory depending on deployment)
│   ├── server.py         # Zero-dependency Python HTTP server & REST API
│   ├── db.py             # SQLite data access layer, migrations & symptom classifier
│   └── schema.sql        # Relational schema + NASA 5 Hazards seed data
└── README.md
```

*(Note: `server.py` resolves `FRONTEND_DIR` as `../frontend` relative to `server.py`. If keeping all files in a single root directory, ensure `index.html` is placed in `frontend/index.html` or update `FRONTEND_DIR` in `server.py`.)*

---

## Getting Started

### Option 1: Static / Standalone Mode (Zero Setup)
Open `index.html` directly in any modern web browser. All data is saved locally in your browser's `localStorage`, and full JSON backup/restore is available under **More → Backup & restore**.

### Option 2: Full-Stack Mode with SQLite Backend
Requires **Python 3.8+** (no external libraries needed).

1. Ensure the directory layout matches:
   ```text
   project-root/
   ├── frontend/index.html
   └── backend/
       ├── server.py
       ├── db.py
       └── schema.sql
   ```
2. Start the server:
   ```bash
   cd backend
   python3 server.py 8000
   ```
3. Open your browser and navigate to:
   ```text
   http://localhost:8000
   ```
   The SQLite database (`crew_health.db`) will be initialized automatically on first run with the NASA hazard reference tables and a default crew profile.

---

## API Reference

When running `server.py`, the following REST endpoints are exposed:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/ping` | Health check and current server UTC timestamp |
| `GET` | `/api/state?crew_id=1` | Retrieve full state (vitals, history, journal, sleep, mood, mission, meals) |
| `PUT` | `/api/state?crew_id=1` | Persist full client state idempotently to SQLite |
| `GET` | `/api/history?metric=hr&limit=30` | Fetch historical time-series points for a specific vital (`sys`, `dia`, `hr`, `temp`, `glu`, `bone`) |
| `GET` | `/api/hazards` | Retrieve NASA's 5 spaceflight hazards and their linked indicators |
| `GET` / `PUT` | `/api/mission` | Get or update mission context (`{"context": "iss" | "moon" | "mars"}`) |
| `POST` | `/api/journal` | Create and auto-classify a new symptom journal entry |
| `PATCH` / `DELETE` | `/api/journal/<id>` | Update metadata or delete a specific journal entry |
| `GET` / `POST` | `/api/backup` & `/api/restore` | Export or restore a complete JSON crew backup |

---

## Data Privacy & Disclaimers

- **Guidance Only, Not a Medical Diagnosis:** Vital sign ranges, dietary menus, and triage prompts included in this application are demonstration placeholders created for the 2026 NASA Space Apps Challenge. On operational missions, flight surgeons and mission medical protocols define clinical thresholds.
- **Local-First Privacy:** No telemetry, health logs, or personal notes are transmitted to external cloud servers or third-party AI APIs.