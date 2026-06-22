import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import { api, RiskCoverage } from "../api";

export default function RiskCoverageCurve({ mv }: { mv: number }) {
  const [rc, setRc] = useState<RiskCoverage | null>(null);
  useEffect(() => { api.riskCoverage(mv).then(setRc); }, [mv]);
  if (!rc) return null;
  return (
    <>
      <div style={{ marginBottom: 6 }}>
        AURC <strong>{rc.aurc.toFixed(4)}</strong>
        <span style={{ color: "#8b949e" }}> · lower is better — risk as the model answers more (less abstention)</span>
      </div>
      <ResponsiveContainer width="100%" height={210}>
        <LineChart data={rc.points}>
          <CartesianGrid stroke="#30363d" />
          <XAxis dataKey="coverage" stroke="#8b949e" domain={[0, 1]} type="number"
                 tickFormatter={(v) => v.toFixed(1)} />
          <YAxis dataKey="risk" stroke="#8b949e" domain={[0, "auto"]} />
          <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d" }} />
          <Line type="monotone" dataKey="risk" stroke="#f85149" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}
