import { useEffect, useState } from "react";
import { api, Prediction } from "../api";

export default function ReviewQueue() {
  const [items, setItems] = useState<Prediction[]>([]);
  const load = () => api.reviewQueue().then((r) => setItems(r.slice(0, 12)));
  useEffect(() => { load(); }, []);

  const resolve = async (id: number, label: string) => {
    await api.resolve(id, label);
    load();
  };

  if (items.length === 0) return <p style={{ color: "#8b949e" }}>Review queue empty.</p>;
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
      <thead>
        <tr style={{ textAlign: "left", color: "#8b949e" }}>
          <th style={{ padding: 6 }}>Sample</th><th>Predicted</th><th>Confidence</th><th>Uncertainty</th><th>Resolve</th>
        </tr>
      </thead>
      <tbody>
        {items.map((p) => (
          <tr key={p.id} style={{ borderTop: "1px solid #30363d" }}>
            <td style={{ padding: 6 }}>{p.sample_id}</td>
            <td>{p.predicted_label}</td>
            <td style={{ color: "#d29922" }}>{p.confidence.toFixed(3)}</td>
            <td>{p.uncertainty.toFixed(3)}</td>
            <td>
              <button onClick={() => resolve(p.id, p.predicted_label)} style={btn("#238636")}>confirm</button>
              <button onClick={() => resolve(p.id, "neg")} style={btn("#6e7681")}>correct</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const btn = (bg: string): React.CSSProperties => ({
  background: bg, color: "#fff", border: "none", borderRadius: 6,
  padding: "4px 10px", marginRight: 6, cursor: "pointer", fontSize: 13,
});
