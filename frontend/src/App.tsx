import { useEffect, useState } from "react";
import { api, ModelVersion } from "./api";
import LiveMonitor from "./components/LiveMonitor";
import CalibrationDiagram from "./components/CalibrationDiagram";
import RiskCoverageCurve from "./components/RiskCoverageCurve";
import ReviewQueue from "./components/ReviewQueue";
import DriftAlerts from "./components/DriftAlerts";
import ModelLineage from "./components/ModelLineage";

const card: React.CSSProperties = {
  background: "#161b22", border: "1px solid #30363d", borderRadius: 10, padding: 16, marginBottom: 16,
};

export default function App() {
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [mv, setMv] = useState<number | null>(null);

  useEffect(() => {
    api.models().then((m) => { setModels(m); if (m[0]) setMv(m[0].id); });
  }, []);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 2 }}>Caliber <span style={{ color: "#8b949e", fontWeight: 400, fontSize: 18 }}>· model reliability monitor</span></h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Calibration (ECE) · risk–coverage (AURC) · selective prediction &amp; human review · drift detection
      </p>

      <div style={{ ...card, display: "flex", gap: 12, alignItems: "center" }}>
        <strong>Model version:</strong>
        <select value={mv ?? ""} onChange={(e) => setMv(Number(e.target.value))}
                style={{ background: "#0e1117", color: "#e6edf3", border: "1px solid #30363d", padding: 6, borderRadius: 6 }}>
          {models.map((m) => (
            <option key={m.id} value={m.id}>{m.name} {m.version} [{m.stage}] · abstain&lt;{m.abstain_threshold}</option>
          ))}
        </select>
      </div>

      <div style={card}><LiveMonitor /></div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={card}>
          <h3 style={{ marginTop: 0 }}>Calibration (reliability diagram)</h3>
          {mv && <CalibrationDiagram mv={mv} />}
        </div>
        <div style={card}>
          <h3 style={{ marginTop: 0 }}>Risk–coverage (selective prediction)</h3>
          {mv && <RiskCoverageCurve mv={mv} />}
        </div>
      </div>

      <div style={card}>
        <h2 style={{ marginTop: 0 }}>Human review queue <span style={{ color: "#8b949e", fontWeight: 400, fontSize: 14 }}>— low-confidence predictions the model abstained on</span></h2>
        <ReviewQueue />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={card}><h3 style={{ marginTop: 0 }}>Drift alerts</h3><DriftAlerts /></div>
        <div style={card}><h3 style={{ marginTop: 0 }}>Model versions &amp; lineage</h3><ModelLineage models={models} /></div>
      </div>
    </div>
  );
}
