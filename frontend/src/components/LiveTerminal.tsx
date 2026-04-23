"use client";

import { useEffect, useRef } from "react";
import { useScanStream } from "@/lib/hooks/useScanStream";

interface Props {
  scanId: string;
}

export default function LiveTerminal({ scanId }: Props) {
  const { lines, done, total } = useScanStream(scanId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="rounded-lg border border-border bg-zinc-950 p-4 font-mono text-xs">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-border/50">
        <span className="text-muted-foreground">
          scan <span className="text-foreground">{scanId.slice(0, 8)}…</span>
        </span>
        {done ? (
          <span className="text-green-400">✓ complete — {total ?? "?"} subdomains</span>
        ) : (
          <span className="flex items-center gap-1.5 text-yellow-400">
            <span className="h-2 w-2 rounded-full bg-yellow-400 animate-pulse inline-block" />
            running
          </span>
        )}
      </div>

      <div className="h-80 overflow-y-auto space-y-0.5 pr-1">
        {lines.length === 0 && !done && (
          <p className="text-muted-foreground animate-pulse">Waiting for results…</p>
        )}
        {lines.map((line, i) => (
          <div
            key={i}
            className={
              line.kind === "error"
                ? "text-red-400"
                : "text-green-400"
            }
          >
            <span className="text-zinc-600 select-none mr-1">$</span>
            {line.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
