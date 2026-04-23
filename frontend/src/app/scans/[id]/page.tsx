"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Scan } from "@/lib/types";
import ResultsTable from "@/components/ResultsTable";
import LiveTerminal from "@/components/LiveTerminal";
import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { relativeTime, scanStatusVariant } from "@/lib/utils";

export default function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [scan, setScan]               = useState<Scan | null>(null);
  const [showTerminal, setShowTerminal] = useState(false);

  useEffect(() => {
    api.scans.get(id).then(setScan).catch(console.error);

    const poll = setInterval(() => {
      api.scans.get(id)
        .then((s) => {
          setScan(s);
          if (s.status !== "running" && s.status !== "pending") clearInterval(poll);
        })
        .catch(console.error);
    }, 3000);

    return () => clearInterval(poll);
  }, [id]);

  if (!scan) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        Loading…
      </div>
    );
  }

  const isActive = scan.status === "running" || scan.status === "pending";

  async function cancelScan() {
    await api.scans.cancel(id).catch(console.error);
    setScan(await api.scans.get(id).catch(() => scan!));
  }

  async function deleteScan() {
    const label = scan?.name ?? scan?.domains[0] ?? "this scan";
    if (!confirm(`Delete "${label}"? This cannot be undone.`)) return;
    try {
      await api.scans.delete(id);
      router.push("/scans");
    } catch (e) {
      console.error(e);
      alert(`Failed to delete scan: ${e instanceof Error ? e.message : e}`);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/scans"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors mb-2 inline-block"
          >
            ← Scans
          </Link>
          <h1 className="text-2xl font-semibold">{scan.name ?? scan.domains[0]}</h1>
          <p className="text-sm text-muted-foreground font-mono mt-1">
            {scan.domains.join(" · ")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={scanStatusVariant(scan.status)}>{scan.status}</Badge>
          <span className="text-xs text-muted-foreground">{relativeTime(scan.created_at)}</span>
          {isActive && (
            <Button size="sm" variant="outline" onClick={() => setShowTerminal((t) => !t)}>
              {showTerminal ? "Hide live output" : "Show live output"}
            </Button>
          )}
          {isActive && (
            <Button size="sm" variant="destructive" onClick={cancelScan}>
              Cancel
            </Button>
          )}
          <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" onClick={deleteScan}>
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Delete
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span>Sources: <span className="text-foreground">{scan.sources.join(", ")}</span></span>
        {scan.started_at && (
          <span>Started: <span className="text-foreground">{new Date(scan.started_at).toLocaleString()}</span></span>
        )}
        {scan.completed_at && (
          <span>Completed: <span className="text-foreground">{new Date(scan.completed_at).toLocaleString()}</span></span>
        )}
        {scan.error && <span className="text-destructive">Error: {scan.error}</span>}
      </div>

      {isActive && showTerminal && <LiveTerminal scanId={id} />}

      <Card>
        <CardHeader>
          <CardTitle>Results</CardTitle>
        </CardHeader>
        <CardContent>
          <ResultsTable scanId={id} />
        </CardContent>
      </Card>
    </div>
  );
}
