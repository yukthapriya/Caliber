import { ModelVersion } from "../api";

export default function ModelLineage({ models }: { models: ModelVersion[] }) {
  const byId = new Map(models.map((m) => [m.id, m]));
  const stageColor: Record<string, string> = {
    production: "#3fb950", staging: "#d29922", archived: "#6e7681",
  };
  return (
    <ul style={{ lineHeight: 1.9 }}>
      {models.map((m) => (
        <li key={m.id}>
          <strong>{m.name} {m.version}</strong>{" "}
          <span style={{ color: stageColor[m.stage] ?? "#8b949e" }}>[{m.stage}]</span>
          {m.parent_id && byId.get(m.parent_id) &&
            <span style={{ color: "#8b949e" }}> ← from {byId.get(m.parent_id)!.version}</span>}
        </li>
      ))}
    </ul>
  );
}
