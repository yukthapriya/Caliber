"""Populate Caliber with REAL model predictions on a REAL dataset.

Trains two genuine classifiers on a scikit-learn dataset, runs them on a held-out
test set, and POSTs every real (confidence, predicted_label, ground_truth) tuple to
the Caliber API. The dashboard's ECE / AURC / review-queue then reflect measured model
behavior, not seeded numbers.

  - production model : calibrated logistic regression  (well-calibrated)
  - candidate model  : Gaussian naive Bayes            (naturally over-confident)

Usage:
  pip install scikit-learn numpy
  python tools/ingest_real.py                      # dataset=digits, API=http://localhost:8000
  API_URL=https://caliber-api.onrender.com python tools/ingest_real.py --dataset breast_cancer
"""
import os
import json
import argparse
import urllib.request

import numpy as np
from sklearn.datasets import load_digits, load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler

API = os.getenv("API_URL", "http://localhost:8000")


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def train_models(dataset):
    d = load_digits() if dataset == "digits" else load_breast_cancer()
    X, y = d.data, d.target
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.4, random_state=42, stratify=y)
    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = scaler.transform(Xtr), scaler.transform(Xte)

    production = CalibratedClassifierCV(
        LogisticRegression(max_iter=3000), method="isotonic", cv=3).fit(Xtr_s, ytr)
    candidate = GaussianNB().fit(Xtr, ytr)

    return {
        "production": (production, Xte_s, yte),
        "candidate":  (candidate,  Xte,   yte),
    }


def predictions_for(model, X, y):
    proba = model.predict_proba(X)
    pred = proba.argmax(axis=1)
    conf = proba.max(axis=1)
    rows = []
    for i in range(len(y)):
        rows.append({
            "sample_id": f"t{i}",
            "predicted_label": str(int(pred[i])),
            "confidence": float(round(conf[i], 4)),
            "uncertainty": float(round(1.0 - conf[i], 4)),
            "ground_truth": str(int(y[i])),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["digits", "breast_cancer"], default="digits")
    args = ap.parse_args()

    print(f"API: {API}  dataset: {args.dataset}")
    print(_req("GET", "/health"))

    models = train_models(args.dataset)

    prod_mv = _req("POST", "/api/models", {
        "name": f"{args.dataset}-classifier", "version": "calibrated-lr-v1",
        "stage": "production", "abstain_threshold": 0.70})
    cand_mv = _req("POST", "/api/models", {
        "name": f"{args.dataset}-classifier", "version": "gaussiannb-v1",
        "parent_id": prod_mv["id"], "stage": "staging", "abstain_threshold": 0.70})

    for key, mv in [("production", prod_mv), ("candidate", cand_mv)]:
        model, X, y = models[key]
        rows = predictions_for(model, X, y)
        for r in rows:
            _req("POST", "/api/predictions", {**r, "model_version_id": mv["id"]})
        cal = _req("GET", f"/api/calibration?model_version_id={mv['id']}")
        print(f"{key:11s} v{mv['version']:18s} id={mv['id']}  "
              f"posted={len(rows)}  ECE={cal['ece']}  (n_labeled={cal['n_labeled']})")

    print("\nDone. Open the dashboard and select the "
          f"'{args.dataset}-classifier' versions to see real measured calibration.")


if __name__ == "__main__":
    main()