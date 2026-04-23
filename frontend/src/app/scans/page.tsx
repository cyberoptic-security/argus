"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { PaginatedResponse, Scan } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { relativeTime, scanStatusVariant } from "@/lib/utils";

const LIMIT = 20;

export default function ScansPage() {
  const [data, setData]     = useState<PaginatedResponse<Scan> | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);

  async function load(o = offset) {
    setLoading(true);
    try { setData(await api.scans.list(o, LIMIT)); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function deleteScan(scan: Scan) {
    const label = scan.name ?? scan.domains[0];
    if (!confirm(`Delete scan "${label}"? This cannot be undone.`)) return;
    try {
      await api.scans.delete(scan.id);
      load(offset);
    } catch (e) {
      console.error(e);
      alert(`Failed to delete scan: ${e instanceof Error ? e.message : e}`);
    }
  }

  useEffect(() => { load(); }, [offset]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Scans</h1>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => load()} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button size="sm" asChild>
            <Link href="/">New Scan</Link>
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name / Domains</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden md:table-cell">Sources</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Started</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data?.items.map((scan) => (
              <tr
                key={scan.id}
                className="border-b border-border/40 hover:bg-muted/30 transition-colors"
              >
                <td className="px-4 py-3">
                  <p className="font-medium">{scan.name ?? scan.domains[0]}</p>
                  {scan.name && (
                    <p className="text-xs text-muted-foreground font-mono">{scan.domains.join(", ")}</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <Badge variant={scanStatusVariant(scan.status)}>{scan.status}</Badge>
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground hidden md:table-cell">
                  {scan.sources.join(", ")}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                  {relativeTime(scan.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button size="sm" variant="ghost" asChild>
                      <Link href={`/scans/${scan.id}`}>View →</Link>
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => deleteScan(scan)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-14 text-center text-muted-foreground text-sm">
                  No scans yet.{" "}
                  <Link href="/" className="text-primary hover:underline">
                    Start one →
                  </Link>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {data && data.total > LIMIT && (
        <div className="flex items-center justify-between">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            disabled={offset === 0}
          >
            Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            {offset + 1}–{Math.min(offset + LIMIT, data.total)} of {data.total}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setOffset(offset + LIMIT)}
            disabled={offset + LIMIT >= data.total}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
