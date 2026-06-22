# Caliber — Model Reliability Monitor

Caliber is an **uncertainty-aware monitoring platform for safety-critical ML models**.
Instead of tracking accuracy alone, it watches the signals that tell you *when a model
should not be trusted* — calibration, confidence, and drift — and routes low-confidence
predictions to a human before they cause harm.

It is the productized version of the calibration / selective-prediction / robustness ideas
from MedProbCLIP and related work (WACV 2026, AAAI 2025).

**Stack:** React + TypeScript (Vite, Recharts) · FastAPI (Python) · PostgreSQL · Kafka + WebSocket

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

## Architecture

```
 simulator ──(Kafka: inference-events)──▶ FastAPI consumer ──▶ selective-prediction policy ──▶ PostgreSQL
                                                  │
                                                  └──(WebSocket /ws/live)──▶ React dashboard
 React dashboard ──(REST /api/*)──▶ FastAPI: calibration (ECE), risk-coverage (AURC),
                                    review queue, drift alerts, model lineage
```

The Kafka consumer **fails soft**: with no broker, the REST + WebSocket API still runs and the
simulator POSTs predictions directly, so you can demo end-to-end with zero infra, then switch
Kafka on for the streaming path.

## Run it

### Docker (Postgres + Kafka included)
```bash
docker compose up --build      # API at http://localhost:8000  (docs at /docs)
```

### Local, zero infra (SQLite, no Kafka)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m app.seed                       # 2 model versions, 440 predictions, review backlog, drift
uvicorn app.main:app --reload            # http://localhost:8000
python simulator/produce_events.py       # stream live events (REST fallback)

cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

## Key API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/predictions` | ingest an inference event; applies the abstain threshold |
| GET | `/api/calibration?model_version_id=` | ECE + reliability bins |
| GET | `/api/risk-coverage?model_version_id=` | risk-coverage curve + AURC |
| GET | `/api/review-queue` | low-confidence predictions awaiting human review |
| POST | `/api/review/{id}` | resolve a flagged prediction with ground truth |
| GET | `/api/drift-alerts` | drift warnings/criticals |
| GET/POST | `/api/models` | model versions + lineage |
| WS | `/ws/live` | live event stream |

The ECE and risk-coverage math lives in `backend/app/metrics.py`.

## Deploy (get a public URL)

**Backend + database — Render (one blueprint):** In Render, *New → Blueprint* and point at this repo. `render.yaml` provisions the API and a free Postgres, runs the seed, and starts the server with a health check. Optional live streaming: create an Upstash Kafka instance (free) and set `KAFKA_BOOTSTRAP_SERVERS` on the `caliber-api` service — leave it unset to run REST + WebSocket only.

**Frontend — two options:**
- *Vercel:* import the repo, set root directory to `frontend`. `vercel.json` handles the Vite build. Add env vars `VITE_API_URL` (`https://<your-api>.onrender.com`) and `VITE_WS_URL` (`wss://<your-api>.onrender.com/ws/live`).
- *Render static:* the `caliber-web` service in `render.yaml` builds it; after the API is live, set `VITE_API_URL` / `VITE_WS_URL` on that service and redeploy.

The backend already allows cross-origin requests, so the Vercel/Render frontend talks to the Render API directly. See `frontend/.env.example`.

## Make it your own (before it goes on a résumé)

Run it, read `metrics.py` until you can explain ECE and AURC from memory (you already can — it's
your research), push it to your GitHub, and extend one piece yourself: a real drift statistic
(PSI / KL divergence) instead of the simulated score, WebSocket auth, or per-class reliability.
