import { useEffect, useState } from "react";
import { api, DriftAlert } from "../api";

export default function DriftAlerts() {
  const [alerts, setAlerts] = useState<DriftAlert[]>([]);
  useEffect(() => { api.driftAlerts().then(setAlerts); }, []);
  if (alerts.length === 0) return <p style={{ color: "#8b949e" }}>No drift alerts.</p>;
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0, lineHeight: 1.9 }}>
      {alerts.map((a) => (
        <li key={a.id}>
          <span style={{ color: a.severity === "critical" ? "#f85149" : "#d29922", fontWeight: 700 }}>
            ● {a.severity}
          </span>{" "}
          drift {a.drift_score.toFixed(2)} (thr {a.threshold.toFixed(2)}) on {a.feature}
        </li>
      ))}
    </ul>
  );
}
