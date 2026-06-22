from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from . import models, schemas


def list_models(db: Session):
    return db.query(models.ModelVersion).order_by(models.ModelVersion.id).all()

def get_model(db: Session, mid: int):
    return db.query(models.ModelVersion).get(mid)

def create_model(db: Session, p: schemas.ModelVersionIn):
    mv = models.ModelVersion(**p.model_dump())
    db.add(mv); db.commit(); db.refresh(mv)
    return mv


def ingest_prediction(db: Session, p: schemas.PredictionIn):
    mv = get_model(db, p.model_version_id)
    tau = mv.abstain_threshold if mv else 0.70
    correct = None
    status = "auto" if p.confidence >= tau else "review"
    if p.ground_truth is not None:
        correct = (p.ground_truth == p.predicted_label)
        status = "resolved" if status == "auto" else status
    pred = models.Prediction(
        model_version_id=p.model_version_id, sample_id=p.sample_id,
        predicted_label=p.predicted_label, confidence=p.confidence,
        uncertainty=p.uncertainty, ground_truth=p.ground_truth,
        correct=correct, status=status,
    )
    db.add(pred); db.commit(); db.refresh(pred)
    return pred


def list_predictions(db: Session, model_version_id: Optional[int], status: Optional[str], limit: int = 200):
    q = db.query(models.Prediction)
    if model_version_id:
        q = q.filter(models.Prediction.model_version_id == model_version_id)
    if status:
        q = q.filter(models.Prediction.status == status)
    return q.order_by(models.Prediction.id.desc()).limit(limit).all()


def resolve_review(db: Session, prediction_id: int, ground_truth: str):
    pred = db.query(models.Prediction).get(prediction_id)
    if not pred:
        return None
    pred.ground_truth = ground_truth
    pred.correct = (ground_truth == pred.predicted_label)
    pred.status = "resolved"
    db.commit(); db.refresh(pred)
    return pred


def labeled_samples(db: Session, model_version_id: Optional[int]) -> List[Tuple[float, bool]]:
    q = db.query(models.Prediction).filter(models.Prediction.correct.isnot(None))
    if model_version_id:
        q = q.filter(models.Prediction.model_version_id == model_version_id)
    return [(p.confidence, bool(p.correct)) for p in q.all()]


def list_drift_alerts(db: Session, model_version_id: Optional[int]):
    q = db.query(models.DriftAlert)
    if model_version_id:
        q = q.filter(models.DriftAlert.model_version_id == model_version_id)
    return q.order_by(models.DriftAlert.id.desc()).limit(100).all()

def create_drift_alert(db: Session, model_version_id: int, drift_score: float, threshold: float = 0.30):
    sev = "critical" if drift_score >= threshold * 1.5 else "warning"
    a = models.DriftAlert(model_version_id=model_version_id, drift_score=drift_score,
                          threshold=threshold, severity=sev)
    db.add(a); db.commit(); db.refresh(a)
    return a
