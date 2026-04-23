"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { SSEEvent } from "../types";

export interface StreamLine {
  text: string;
  kind: "subdomain" | "error" | "info";
}

export function useScanStream(scanId: string | null) {
  const [lines, setLines] = useState<StreamLine[]>([]);
  const [done, setDone] = useState(false);
  const [total, setTotal] = useState<number | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!scanId) return;

    setLines([]);
    setDone(false);
    setTotal(null);

    const es = new EventSource(api.scans.streamUrl(scanId));
    esRef.current = es;

    es.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as SSEEvent;

      if (event.type === "done") {
        setDone(true);
        setTotal(event.total ?? null);
        es.close();
        return;
      }

      if (event.type === "subdomain" && event.fqdn) {
        const ips = event.ips?.length ? `  →  ${event.ips.join(", ")}` : "";
        const src = event.source ? `  [${event.source}]` : "";
        setLines((prev) => [...prev, { text: `${event.fqdn}${ips}${src}`, kind: "subdomain" }]);
        return;
      }

      if (event.type === "error") {
        setLines((prev) => [...prev, { text: `ERROR: ${event.message ?? "unknown"}`, kind: "error" }]);
        return;
      }
    };

    es.onerror = () => {
      setLines((prev) => [...prev, { text: "Stream connection lost", kind: "error" }]);
      setDone(true);
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [scanId]);

  return { lines, done, total };
}
