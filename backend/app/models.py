"""Caliber domain: uncertainty-aware reliability monitoring for safety-critical models.

A deployed model emits Predictions, each carrying a confidence and an uncertainty
estimate. Caliber applies a selective-prediction policy: predictions below the
abstention threshold are routed to a human REVIEW queue instead of being auto-accepted.
Labeled predictions feed calibration (ECE) and risk-coverage (AURC) computations,
and input drift raises DriftAlerts before accuracy visibly degrades.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)            # e.g. MedProbCLIP
    version = Column(String, nullable=False)         # e.g. v1.2.0
    parent_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)
    stage = Column(String, default="staging")        # staging | production | archived
    abstain_threshold = Column(Float, default=0.70)  # selective-prediction cutoff
    created_at = Column(DateTime, default=datetime.utcnow)
    predictions = relationship("Prediction", back_populates="model_version")


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"))
    sample_id = Column(String, index=True)
    predicted_label = Column(String)
    confidence = Column(Float, nullable=False)       # max softmax / 1 - normalized variance
    uncertainty = Column(Float, default=0.0)         # predictive variance (epistemic proxy)
    ground_truth = Column(String, nullable=True)     # filled when labeled / reviewed
    correct = Column(Boolean, nullable=True)         # derived once ground_truth known
    status = Column(String, default="auto")          # auto | review | resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    model_version = relationship("ModelVersion", back_populates="predictions")


class DriftAlert(Base):
    __tablename__ = "drift_alerts"
    id = Column(Integer, primary_key=True, index=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"))
    feature = Column(String, default="input")
    drift_score = Column(Float, nullable=False)
    threshold = Column(Float, default=0.30)
    severity = Column(String, default="warning")     # warning | critical
    created_at = Column(DateTime, default=datetime.utcnow)
