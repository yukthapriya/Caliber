# Caliber — Model Reliability Monitor

Caliber is an **uncertainty-aware monitoring platform for safety-critical ML models**.
Instead of tracking accuracy alone, it watches the signals that tell you *when a model
should not be trusted* — calibration, confidence, and drift — and routes low-confidence
predictions to a human before they cause harm.

It is the productized version of the calibration, selective-prediction, and robustness ideas
from my research on reliable vision-language models (MedProbCLIP, WACV 2026; AAAI 2025).

- **Live API:** https://caliber-api.onrender.com (interactive docs at `/docs`)
- **Stack:** React + TypeScript (Vite, Recharts) · FastAPI (Python) · PostgreSQL · Kafka + WebSocket

---

## Why it exists

Modern classifiers attach a confidence score to every prediction, but those scores are often
miscalibrated: a model can report 0.9 confidence while being right only 60 percent of the time.
In low-stakes settings that is a nuisance. In safety-critical ones — medical imaging, manufacturing
quality inspection — a confident wrong answer is worse than no answer at all, because nothing
signals that a human should step in.

Caliber treats uncertainty as a first-class monitoring target. It continuously answers three
questions about a model in production: is it calibrated (do its confidence scores match its real
accuracy), how much risk does it remove when it abstains on its least-confident cases, and is the
incoming data drifting away from what it was trained on. When confidence drops below a per-model
threshold, Caliber does not just record the event — it withholds the prediction and sends it to a
human review queue.

---

## What it monitors

- **Calibration (ECE)** — reliability diagram of confidence vs. empirical accuracy, with an
  Expected Calibration Error score. Over-confident models surface immediately
  (the seeded candidate scores ECE ~0.17 vs the production model's ~0.04).
- **Risk–coverage / AURC** — as the model answers more (abstains less), how does error rate rise?
  Area Under the Risk-Coverage Curve summarizes selective-prediction quality.
- **Selective prediction + human review** — predictions below a per-model **abstain threshold**
  are routed to a review queue instead of auto-accepted; a reviewer resolves them, which feeds
  calibration back.
- **Drift detection** — input drift raises warning/critical alerts before accuracy visibly degrades.
- **Model versioning & lineage** — registry with stage (production/staging/archived) and parent links.
- **Real-time monitoring** — live inference events stream through Kafka to a WebSocket, so the
  dashboard updates as predictions arrive.

## Architecture

```
 simulator ──(Kafka: inference-events)──▶ FastAPI consumer ──▶ selective-prediction policy ──▶ PostgreSQL
                                                  │
                                                  └──(WebSocket /ws/live)──▶ React dashboard
 React dashboard ──(REST /api/*)──▶ FastAPI: calibration (ECE), risk-coverage (AURC),
                                    review queue, drift alerts, model lineage
```

Every prediction — whether it arrives over Kafka or over REST — passes through the same policy:
look up the target model's abstain threshold, and if the prediction's confidence is below it, set
its status to `review` instead of `auto`. Only labeled predictions (those with ground truth) feed
the calibration and risk-coverage computations, since accuracy cannot be measured without a label.

The Kafka consumer **fails soft**: with no broker, the REST + WebSocket API still runs and the
simulator POSTs predictions directly, so you can demo end-to-end with zero infra, then switch
Kafka on for the streaming path by setting one environment variable.

## The metrics

All metric code lives in `backend/app/metrics.py` and runs server-side on the stored predictions,
so the numbers the dashboard shows are computed, not hard-coded.

**Expected Calibration Error (ECE).** Labeled predictions are sorted into `M = 10` equal-width
confidence bins. For each bin the average confidence and empirical accuracy are compared, weighted
by the share of samples in that bin:

```
ECE = sum_b ( |b| / N ) * | accuracy(b) - confidence(b) |
```

A perfectly calibrated model has accuracy equal to confidence in every bin, so ECE is 0. The
reliability diagram plots accuracy per bin against the ideal diagonal so the gap is visible.

**Risk–coverage and AURC.** Labeled predictions are sorted by confidence, highest first, and a
coverage level *k* is swept from 1 to *N*. At each step coverage is `k / N` (the fraction the model
chooses to answer) and risk is the error rate among those *k* most-confident answers. The Area Under
the Risk-Coverage Curve, computed by trapezoidal integration, gives one number where lower is better.

**Selective prediction.** Each model version carries an `abstain_threshold`. Any prediction whose
confidence falls below it is withheld and queued for human review rather than auto-accepted — the
mechanism that turns a calibration measurement into a safety control.

**Drift.** Input drift is reported as a drift score against a threshold. Scores at or above the
threshold raise a warning; scores at or above 1.5x the threshold raise a critical alert.

## Data model

| Table | Purpose | Key fields |
|---|---|---|
| `model_versions` | model registry and lineage | `name`, `version`, `parent_id`, `stage`, `abstain_threshold` |
| `predictions` | every inference event | `confidence`, `uncertainty`, `predicted_label`, `ground_truth`, `correct`, `status` (`auto` / `review` / `resolved`) |
| `drift_alerts` | drift warnings and criticals | `feature`, `drift_score`, `threshold`, `severity` |

## Key API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/predictions` | ingest an inference event; applies the abstain threshold |
| GET | `/api/predictions` | list predictions, filterable by model and status |
| GET | `/api/calibration?model_version_id=` | ECE + reliability bins |
| GET | `/api/risk-coverage?model_version_id=` | risk-coverage curve + AURC |
| GET | `/api/review-queue` | low-confidence predictions awaiting human review |
| POST | `/api/review/{id}` | resolve a flagged prediction with ground truth |
| GET | `/api/drift-alerts` | drift warnings/criticals |
| GET/POST | `/api/models` | model versions + lineage |
| WS | `/ws/live` | live event stream |

## Run it

### Local, zero infra (SQLite, no Kafka)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m app.seed                       # 2 model versions, 440 predictions, review backlog, drift
uvicorn app.main:app --reload            # http://localhost:8000

python simulator/produce_events.py       # separate terminal: stream live events (REST fallback)

cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

The seed creates a well-calibrated production model (ECE ~0.04) alongside an intentionally
over-confident candidate (ECE ~0.17), so the calibration gap is visible immediately. To reset the
local database, delete `backend/caliber.db` and run the seed again.

### Docker (Postgres + Kafka included)
```bash
docker compose up --build      # API at http://localhost:8000  (docs at /docs)
```

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./caliber.db` | Postgres connection string in production; the `postgres://` scheme is normalized for SQLAlchemy automatically |
| `KAFKA_BOOTSTRAP_SERVERS` | unset | enables the live Kafka consumer; unset runs REST + WebSocket only |
| `KAFKA_TOPIC` | `inference-events` | topic the consumer and simulator use |
| `VITE_API_URL` | `""` (dev proxy) | backend base URL for the deployed frontend |
| `VITE_WS_URL` | derived from host | WebSocket URL for the deployed frontend |

## Deploy (get a public URL)

**Backend + database — Render (one blueprint):** In Render, *New → Blueprint* and point at this repo.
`render.yaml` provisions the API and a free Postgres, runs the seed, and starts the server with a
health check. Python is pinned to 3.12 (`backend/runtime.txt` and `PYTHON_VERSION`) so pip pulls
prebuilt wheels instead of compiling native dependencies. Optional live streaming: create a managed
Kafka instance and set `KAFKA_BOOTSTRAP_SERVERS` on the `caliber-api` service — leave it unset to run
REST + WebSocket only.

**Frontend — two options:**
- *Vercel:* import the repo, set root directory to `frontend`. `vercel.json` handles the Vite build.
  Add env vars `VITE_API_URL` (`https://<your-api>.onrender.com`) and `VITE_WS_URL`
  (`wss://<your-api>.onrender.com/ws/live`).
- *Render static:* the `caliber-web` service in `render.yaml` builds it; after the API is live, set
  `VITE_API_URL` / `VITE_WS_URL` on that service and redeploy.

The backend allows cross-origin requests, so the Vercel/Render frontend talks to the Render API
directly. See `frontend/.env.example`.

## Project structure

```
caliber/
  backend/
    app/
      main.py            FastAPI app: REST endpoints + WebSocket
      models.py          SQLAlchemy schema (model versions, predictions, drift alerts)
      metrics.py         ECE and risk-coverage / AURC
      crud.py            data access + selective-prediction routing
      kafka_consumer.py  fail-soft Kafka ingest, broadcast to WebSocket
      schemas.py         request/response models
      seed.py            demo scenario
      database.py        engine + Postgres scheme normalization
      ws.py              WebSocket connection manager
    simulator/
      produce_events.py  streams live inference events (Kafka or REST fallback)
  frontend/
    src/
      App.tsx            dashboard layout and model selector
      api.ts             typed API client
      useLiveStream.ts   WebSocket hook
      components/        calibration diagram, risk-coverage curve, review queue,
                         drift alerts, live monitor, model lineage
  render.yaml            Render blueprint (API + Postgres + static frontend)
  docker-compose.yml     full local stack with Postgres and Kafka
```

## Design decisions

- **Fail-soft streaming.** The Kafka consumer and the simulator both degrade gracefully to the REST
  path, so the project is demoable with zero infrastructure and identical code in production.
- **Labels gate the metrics.** ECE and risk-coverage are computed only over predictions that have
  ground truth, so unlabeled live traffic never distorts the reliability numbers.
- **Database portability.** SQLite for local runs, Postgres in production, with the connection-string
  scheme normalized so managed databases connect without code changes.
- **Selective prediction as a control, not a chart.** The abstain threshold actively routes traffic
  to a review queue rather than only being displayed, which makes the tool a safety mechanism instead
  of a passive dashboard.

## Limitations and future work

- The drift score is currently supplied by the event stream; the natural next step is to compute it
  from a population-stability index or KL divergence over incoming feature statistics.
- The WebSocket endpoint is unauthenticated; production use needs auth and per-tenant isolation.
- Schema changes rely on `create_all`; a real migration tool (Alembic) would make versioned upgrades safe.
- Calibration is global per model; per-class reliability and temperature scaling would extend it
  toward production calibration workflows.
