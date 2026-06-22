"""Reliability metrics — the same ones from the MedProbCLIP / calibration papers.

- Expected Calibration Error (ECE) + reliability-diagram bins
- Risk-Coverage curve + Area Under the Risk-Coverage Curve (AURC) for selective prediction
"""
from typing import List, Tuple, Dict


def calibration(samples: List[Tuple[float, bool]], n_bins: int = 10):
    """samples: (confidence, correct). Returns (ece, reliability_bins)."""
    bins: List[List[Tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for conf, correct in samples:
        idx = min(n_bins - 1, int(conf * n_bins))
        bins[idx].append((conf, correct))

    total = len(samples) or 1
    ece = 0.0
    reliability: List[Dict] = []
    for i, b in enumerate(bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        if b:
            avg_conf = sum(c for c, _ in b) / len(b)
            acc = sum(1 for _, ok in b if ok) / len(b)
            ece += (len(b) / total) * abs(avg_conf - acc)
        else:
            avg_conf = acc = None
        reliability.append({
            "bin_lo": round(lo, 2), "bin_hi": round(hi, 2),
            "confidence": None if avg_conf is None else round(avg_conf, 4),
            "accuracy": None if acc is None else round(acc, 4),
            "count": len(b),
        })
    return round(ece, 4), reliability


def risk_coverage(samples: List[Tuple[float, bool]]):
    """Sort by confidence desc; sweep coverage and report risk = error rate among answered.
    Returns (curve_points, aurc)."""
    if not samples:
        return [], 0.0
    ordered = sorted(samples, key=lambda s: -s[0])
    n = len(ordered)
    points, errors = [], 0
    for k, (_, correct) in enumerate(ordered, start=1):
        if not correct:
            errors += 1
        points.append({"coverage": round(k / n, 4), "risk": round(errors / k, 4)})

    # AURC via trapezoidal integration of risk over coverage
    aurc = 0.0
    for a, b in zip(points, points[1:]):
        aurc += (b["coverage"] - a["coverage"]) * (a["risk"] + b["risk"]) / 2
    return points, round(aurc, 4)
