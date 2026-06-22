"""Seed a realistic reliability scenario: a calibrated-ish production model plus a
miscalibrated candidate, labeled predictions (for ECE / AURC), a review backlog of
low-confidence cases, and a couple of drift alerts.  Run: python -m app.seed"""
import random
from .database import Base, engine, SessionLocal
from . import models, crud, schemas

Base.metadata.create_all(bind=engine)
random.seed(42)


def _emit(db, mv, n, miscalib=False, labeled_frac=0.8):
    for i in range(n):
        # Confidence; a miscalibrated model is over-confident relative to accuracy.
        conf = random.uniform(0.45, 0.99)
        true_acc = conf - (0.18 if miscalib else 0.03)        # gap drives ECE
        correct = random.random() < max(0.0, min(1.0, true_acc))
        gt = "pos" if correct else "neg"
        pred_label = "pos"
        labeled = random.random() < labeled_frac
        crud.ingest_prediction(db, schemas.PredictionIn(
            model_version_id=mv.id, sample_id=f"s{mv.id}-{i}",
            predicted_label=pred_label, confidence=round(conf, 3),
            uncertainty=round(1 - conf, 3),
            ground_truth=(gt if labeled else None),
        ))


def seed():
    db = SessionLocal()
    if db.query(models.ModelVersion).count() > 0:
        print("Already seeded."); return

    prod = crud.create_model(db, schemas.ModelVersionIn(
        name="MedProbCLIP", version="v1.1.0", stage="production", abstain_threshold=0.70))
    cand = crud.create_model(db, schemas.ModelVersionIn(
        name="MedProbCLIP", version="v1.2.0", parent_id=prod.id,
        stage="staging", abstain_threshold=0.70))

    _emit(db, prod, 220, miscalib=False)
    _emit(db, cand, 220, miscalib=True)     # candidate is over-confident -> higher ECE

    crud.create_drift_alert(db, cand.id, drift_score=0.34)
    crud.create_drift_alert(db, cand.id, drift_score=0.52)

    rq = crud.list_predictions(db, None, status="review")
    print(f"Seeded 2 model versions, 440 predictions, {len(rq)} in review queue, 2 drift alerts.")


if __name__ == "__main__":
    seed()
