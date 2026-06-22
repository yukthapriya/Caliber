import { useEffect, useState } from "react";
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import { api, Calibration } from "../api";

export default function CalibrationDiagram({ mv }: { mv: number }) {
  const [cal, setCal] = useState<Calibration | null>(null);
  useEffect(() => { api.calibration(mv).then(setCal); }, [mv]);
  if (!cal) return null;
  const data = cal.bins.map((b) => ({
    bin: `${b.bin_lo.toFixed(1)}`, accuracy: b.accuracy ?? null,
    ideal: (b.bin_lo + b.bin_hi) / 2, count: b.count,
  }));
  const eceColor = cal.ece <= 0.05 ? "#3fb950" : cal.ece <= 0.10 ? "#d29922" : "#f85149";
  return (
    <>
      <div style={{ marginBottom: 6 }}>
        ECE <strong style={{ color: eceColor }}>{cal.ece.toFixed(4)}</strong>
        <span style={{ color: "#8b949e" }}> · {cal.n_labeled} labeled · perfect calibration = diagonal</span>
      </div>
      <ResponsiveContainer width="100%" height={210}>
        <ComposedChart data={data}>
          <CartesianGrid stroke="#30363d" />
          <XAxis dataKey="bin" stroke="#8b949e" />
          <YAxis stroke="#8b949e" domain={[0, 1]} />
          <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d" }} />
          <Bar dataKey="accuracy" fill="#1f6feb" />
          <Line dataKey="ideal" stroke="#8b949e" strokeDasharray="4 4" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}
