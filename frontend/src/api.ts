const BASE = import.meta.env.VITE_API_URL ?? "";

export interface ModelVersion { id: number; name: string; version: string;
  parent_id: number | null; stage: string; abstain_threshold: number; }
export interface Prediction { id: number; model_version_id: number; sample_id: string;
  predicted_label: string; confidence: number; uncertainty: number;
  ground_truth: string | null; correct: boolean | null; status: string; created_at: string; }
export interface Bin { bin_lo: number; bin_hi: number; confidence: number | null;
  accuracy: number | null; count: number; }
export interface Calibration { ece: number; n_labeled: number; bins: Bin[]; }
export interface RiskCoverage { aurc: number; points: { coverage: number; risk: number }[]; }
export interface DriftAlert { id: number; model_version_id: number; feature: string;
  drift_score: number; threshold: number; severity: string; created_at: string; }

async function get<T>(p: string): Promise<T> {
  const r = await fetch(`${BASE}${p}`);
  if (!r.ok) throw new Error(`${p} -> ${r.status}`);
  return r.json();
}
async function post<T>(p: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${p}`, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${p} -> ${r.status}`);
  return r.json();
}

export const api = {
  models: () => get<ModelVersion[]>("/api/models"),
  calibration: (mv: number) => get<Calibration>(`/api/calibration?model_version_id=${mv}`),
  riskCoverage: (mv: number) => get<RiskCoverage>(`/api/risk-coverage?model_version_id=${mv}`),
  reviewQueue: () => get<Prediction[]>("/api/review-queue"),
  resolve: (id: number, ground_truth: string) => post<Prediction>(`/api/review/${id}`, { ground_truth }),
  driftAlerts: () => get<DriftAlert[]>("/api/drift-alerts"),
};
