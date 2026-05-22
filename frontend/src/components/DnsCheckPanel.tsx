"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Download,
  Info,
  Shield,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { DnsCheckResult, DnsSeverity } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  scanId: string;
  activeCheckId: string | null;
  onReset: () => void;
}

type Phase = "idle" | "running" | "done";

const SEVERITY_ORDER: DnsSeverity[] = ["critical", "high", "medium", "low", "info"];

const SEVERITY_STYLES: Record<DnsSeverity, string> = {
  critical: "bg-red-500/15 text-red-400 border border-red-500/30",
  high:     "bg-orange-500/15 text-orange-400 border border-orange-500/30",
  medium:   "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
  low:      "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  info:     "bg-muted text-muted-foreground border border-border",
};

const CHECK_TYPE_STYLES: Record<string, string> = {
  spf:   "bg-purple-500/10 text-purple-400",
  dmarc: "bg-cyan-500/10 text-cyan-400",
  mx:    "bg-green-500/10 text-green-400",
  dkim:  "bg-pink-500/10 text-pink-400",
};

function SeverityBadge({ severity }: { severity: DnsSeverity }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_STYLES[severity]}`}>
      {severity}
    </span>
  );
}

function CheckTypeBadge({ type }: { type: string }) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono font-semibold ${CHECK_TYPE_STYLES[type] ?? "bg-muted text-muted-foreground"}`}>
      {type.toUpperCase()}
    </span>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "pass") return <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />;
  if (status === "fail") return <XCircle className="h-4 w-4 text-red-500 shrink-0" />;
  if (status === "warn") return <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0" />;
  return <Info className="h-4 w-4 text-muted-foreground shrink-0" />;
}

function sortedFindings(results: DnsCheckResult[]): DnsCheckResult[] {
  return [...results].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
  );
}

function exportCsv(results: DnsCheckResult[]) {
  const headers = ["FQDN", "Check", "Status", "Severity", "Title", "Detail", "Recommendation", "Raw Value"];
  const rows = results.map((r) => [
    r.fqdn, r.check_type, r.status, r.severity,
    r.title, r.detail, r.recommendation ?? "", r.raw_value ?? "",
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "dns-security-results.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function FindingsTable({
  results,
  expandedId,
  onExpand,
}: {
  results: DnsCheckResult[];
  expandedId: number | null;
  onExpand: (id: number | null) => void;
}) {
  if (!results.length) {
    return (
      <p className="text-sm text-muted-foreground text-center py-6">No findings to display.</p>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-x-auto">
      <table className="w-full text-sm min-w-[680px]">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="w-8 px-3 py-2" />
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Severity</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">FQDN</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Check</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Finding</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <React.Fragment key={r.id}>
              <tr
                className="border-b border-border/40 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => onExpand(expandedId === r.id ? null : r.id)}
              >
                <td className="px-3 py-2.5 text-center">
                  <StatusIcon status={r.status} />
                </td>
                <td className="px-3 py-2.5">
                  <SeverityBadge severity={r.severity} />
                </td>
                <td className="px-3 py-2.5 font-mono text-xs text-muted-foreground">
                  {r.fqdn}
                </td>
                <td className="px-3 py-2.5">
                  <CheckTypeBadge type={r.check_type} />
                </td>
                <td className="px-3 py-2.5 text-xs">{r.title}</td>
              </tr>
              {expandedId === r.id && (
                <tr className="border-b border-border/40 bg-muted/10">
                  <td colSpan={5} className="px-5 py-3 space-y-2">
                    <p className="text-xs text-foreground/80 leading-relaxed">{r.detail}</p>
                    {r.recommendation && (
                      <div className="flex gap-1.5 items-start pt-1">
                        <span className="text-xs font-semibold text-blue-400 shrink-0 mt-px">
                          Recommendation:
                        </span>
                        <p className="text-xs text-blue-300/80 leading-relaxed">
                          {r.recommendation}
                        </p>
                      </div>
                    )}
                    {r.raw_value && (
                      <p className="text-xs font-mono bg-muted rounded px-2 py-1.5 text-muted-foreground break-all mt-1">
                        {r.raw_value}
                      </p>
                    )}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DnsCheckPanel({ scanId, activeCheckId, onReset }: Props) {
  const [phase, setPhase]             = useState<Phase>("idle");
  const [checkId, setCheckId]         = useState<string | null>(null);
  const [results, setResults]         = useState<DnsCheckResult[]>([]);
  const [expandedId, setExpandedId]   = useState<number | null>(null);
  const [severityFilter, setSeverityFilter] = useState("");

  // On mount: load the most recent check for this scan (if any)
  useEffect(() => {
    api.dnsChecks.getByScan(scanId)
      .then((existing) => {
        setCheckId(existing.id);
        setResults(existing.results);
        const active = existing.status === "running" || existing.status === "pending";
        setPhase(active ? "running" : "done");
      })
      .catch(() => { /* no previous check */ });
  }, [scanId]);

  // When parent triggers a new check, start polling it
  useEffect(() => {
    if (!activeCheckId) return;
    setCheckId(activeCheckId);
    setPhase("running");
    setResults([]);
    setExpandedId(null);
    setSeverityFilter("");
  }, [activeCheckId]);

  // Poll while running
  useEffect(() => {
    if (phase !== "running" || !checkId) return;
    const interval = setInterval(async () => {
      try {
        const check = await api.dnsChecks.get(checkId);
        setResults(check.results);
        if (check.status !== "running" && check.status !== "pending") {
          setPhase("done");
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [phase, checkId]);

  // Summary counts
  const severityCounts = results.reduce<Record<string, number>>((acc, r) => {
    if (r.status !== "pass" && r.status !== "info") {
      acc[r.severity] = (acc[r.severity] ?? 0) + 1;
    }
    return acc;
  }, {});
  const passCount = results.filter((r) => r.status === "pass").length;

  const filtered = sortedFindings(
    severityFilter
      ? results.filter((r) => r.severity === severityFilter || r.status === severityFilter)
      : results
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Shield className="h-4 w-4" />
          DNS Security Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* ── IDLE ── */}
        {phase === "idle" && (
          <p className="text-sm text-muted-foreground py-1">
            Select domains in the Results table above, then click{" "}
            <span className="text-foreground font-medium">DNS Security Check</span>{" "}
            to analyse email security configuration (SPF, DMARC, DKIM, MX).
          </p>
        )}

        {/* ── RUNNING ── */}
        {phase === "running" && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
              Running DNS checks…{" "}
              {results.length > 0 && (
                <span className="text-foreground">{results.length} findings so far</span>
              )}
            </div>
            {results.length > 0 && (
              <FindingsTable
                results={sortedFindings(results)}
                expandedId={expandedId}
                onExpand={setExpandedId}
              />
            )}
          </div>
        )}

        {/* ── DONE ── */}
        {phase === "done" && (
          <div className="space-y-4">
            {/* summary + actions */}
            <div className="flex flex-wrap items-center gap-2">
              {(["critical", "high", "medium"] as const).map(
                (sev) =>
                  (severityCounts[sev] ?? 0) > 0 && (
                    <span
                      key={sev}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_STYLES[sev]}`}
                    >
                      {severityCounts[sev]} {sev}
                    </span>
                  )
              )}
              {(["low", "info"] as const).map(
                (sev) =>
                  (severityCounts[sev] ?? 0) > 0 && (
                    <span key={sev} className="text-xs text-muted-foreground">
                      {severityCounts[sev]} {sev}
                    </span>
                  )
              )}
              <span className="text-xs text-green-500">{passCount} pass</span>
              <span className="text-xs text-muted-foreground">· {results.length} total</span>

              <div className="flex gap-1 ml-auto">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => exportCsv(sortedFindings(results))}
                >
                  <Download className="h-3 w-3 mr-1" />CSV
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setPhase("idle");
                    setResults([]);
                    setCheckId(null);
                    setSeverityFilter("");
                    onReset();
                  }}
                >
                  Run New Check
                </Button>
              </div>
            </div>

            {/* severity filter */}
            <select
              className="rounded-md border border-input bg-transparent px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="">All findings</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
              <option value="pass">Pass</option>
            </select>

            <FindingsTable
              results={filtered}
              expandedId={expandedId}
              onExpand={setExpandedId}
            />
          </div>
        )}

      </CardContent>
    </Card>
  );
}
