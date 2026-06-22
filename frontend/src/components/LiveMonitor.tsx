import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import { useLiveStream } from "../useLiveStream";

export default function LiveMonitor() {
  const events = useLiveStream(80);
  const preds = events.filter((e) => e.type === "prediction" && typeof e.confidence === "number");
  const flagged = preds.filter((e) => e.status === "review").length;
  const rate = preds.length ? Math.round((100 * flagged) / preds.length) : 0;
  const series = useMemo(() => preds.map((e, i) => ({ i, confidence: e.confidence })), [preds]);

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Real-time inference monitoring <span style={{ color: "#8b949e", fontWeight: 400, fontSize: 14 }}>(live via WebSocket / Kafka)</span></h2>
      <div style={{ display: "flex", gap: 24, marginBottom: 8 }}>
        <Stat label="live predictions" value={preds.length} />
        <Stat label="flagged for review" value={flagged} color="#d29922" />
        <Stat label="abstention rate" value={`${rate}%`} color="#d29922" />
      </div>
      {series.length === 0
        ? <p style={{ color: "#8b949e" }}>Waiting for live events… run the simulator to stream inference confidence.</p>
        : <ResponsiveContainer width="100%" height={170}>
            <LineChart data={series}>
              <CartesianGrid stroke="#30363d" />
              <XAxis dataKey="i" stroke="#8b949e" />
              <YAxis stroke="#8b949e" domain={[0, 1]} />
              <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d" }} />
              <Line type="monotone" dataKey="confidence" stroke="#1f6feb" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>}
    </>
  );
}

function Stat({ label, value, color = "#e6edf3" }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 12, color: "#8b949e" }}>{label}</div>
    </div>
  );
}
