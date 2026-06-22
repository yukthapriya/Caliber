"""Caliber API — uncertainty-aware reliability monitoring for safety-critical models."""
import asyncio
import contextlib
from typing import List, Optional

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models, schemas, crud, metrics
from .ws import manager
from .kafka_consumer import run_consumer

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Caliber — Model Reliability Monitor", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def _startup():
    app.state.consumer_task = asyncio.create_task(run_consumer(manager))

@app.on_event("shutdown")
async def _shutdown():
    task = getattr(app.state, "consumer_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


# ---- Models / lineage ----
@app.get("/api/models", response_model=List[schemas.ModelVersionOut])
def list_models(db: Session = Depends(get_db)):
    return crud.list_models(db)

@app.post("/api/models", response_model=schemas.ModelVersionOut)
def create_model(p: schemas.ModelVersionIn, db: Session = Depends(get_db)):
    return crud.create_model(db, p)


# ---- Prediction ingest + selective prediction ----
@app.post("/api/predictions", response_model=schemas.PredictionOut)
async def ingest(p: schemas.PredictionIn, db: Session = Depends(get_db)):
    pred = crud.ingest_prediction(db, p)
    await manager.broadcast({
        "type": "prediction", "id": pred.id, "model_version_id": pred.model_version_id,
        "confidence": pred.confidence, "uncertainty": pred.uncertainty,
        "status": pred.status, "ts": pred.created_at.isoformat(),
    })
    return pred

@app.get("/api/predictions", response_model=List[schemas.PredictionOut])
def list_predictions(model_version_id: Optional[int] = None, status: Optional[str] = None,
                     db: Session = Depends(get_db)):
    return crud.list_predictions(db, model_version_id, status)


# ---- Human review queue (selective prediction in action) ----
@app.get("/api/review-queue", response_model=List[schemas.PredictionOut])
def review_queue(model_version_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.list_predictions(db, model_version_id, status="review")

@app.post("/api/review/{prediction_id}", response_model=schemas.PredictionOut)
async def resolve(prediction_id: int, body: schemas.ReviewIn, db: Session = Depends(get_db)):
    pred = crud.resolve_review(db, prediction_id, body.ground_truth)
    if not pred:
        raise HTTPException(404, "prediction not found")
    await manager.broadcast({"type": "review_resolved", "id": pred.id})
    return pred


# ---- Calibration (ECE) + risk-coverage (AURC) ----
@app.get("/api/calibration", response_model=schemas.CalibrationOut)
def calibration(model_version_id: Optional[int] = None, db: Session = Depends(get_db)):
    samples = crud.labeled_samples(db, model_version_id)
    ece, bins = metrics.calibration(samples)
    return {"ece": ece, "n_labeled": len(samples), "bins": bins}

@app.get("/api/risk-coverage", response_model=schemas.RiskCoverageOut)
def risk_coverage(model_version_id: Optional[int] = None, db: Session = Depends(get_db)):
    samples = crud.labeled_samples(db, model_version_id)
    points, aurc = metrics.risk_coverage(samples)
    return {"aurc": aurc, "points": points}


# ---- Drift ----
@app.get("/api/drift-alerts", response_model=List[schemas.DriftAlertOut])
def drift_alerts(model_version_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.list_drift_alerts(db, model_version_id)


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)


@app.get("/health")
def health():
    return {"status": "ok"}
