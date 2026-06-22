from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel


class ModelVersionIn(BaseModel):
    name: str
    version: str
    parent_id: Optional[int] = None
    stage: str = "staging"
    abstain_threshold: float = 0.70

class ModelVersionOut(ModelVersionIn):
    id: int
    created_at: datetime
    class Config: from_attributes = True


class PredictionIn(BaseModel):
    model_version_id: int
    sample_id: str
    predicted_label: str
    confidence: float
    uncertainty: float = 0.0
    ground_truth: Optional[str] = None

class PredictionOut(BaseModel):
    id: int
    model_version_id: int
    sample_id: str
    predicted_label: str
    confidence: float
    uncertainty: float
    ground_truth: Optional[str]
    correct: Optional[bool]
    status: str
    created_at: datetime
    class Config: from_attributes = True


class ReviewIn(BaseModel):
    ground_truth: str


class DriftAlertOut(BaseModel):
    id: int
    model_version_id: int
    feature: str
    drift_score: float
    threshold: float
    severity: str
    created_at: datetime
    class Config: from_attributes = True


class CalibrationOut(BaseModel):
    ece: float
    n_labeled: int
    bins: List[Dict]

class RiskCoverageOut(BaseModel):
    aurc: float
    points: List[Dict]
