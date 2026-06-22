import { useEffect, useRef, useState } from "react";

export interface LiveEvent { type?: string; status?: string; confidence?: number; ts?: string; }

export function useLiveStream(max = 80) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const ref = useRef<WebSocket | null>(null);
  useEffect(() => {
    const url = (import.meta.env.VITE_WS_URL as string) ??
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/live`;
    const ws = new WebSocket(url); ref.current = ws;
    ws.onmessage = (e) => {
      const ev = JSON.parse(e.data) as LiveEvent;
      setEvents((p) => [...p, ev].slice(-max));
    };
    const ping = setInterval(() => ws.readyState === 1 && ws.send("ping"), 15000);
    return () => { clearInterval(ping); ws.close(); };
  }, [max]);
  return events;
}
