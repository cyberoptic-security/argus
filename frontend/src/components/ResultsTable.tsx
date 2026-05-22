"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Search, Shield } from "lucide-react";
import { api } from "@/lib/api";
import type { PaginatedResponse, Subdomain } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const LIMIT = 100;

interface Props {
  scanId: string;
  selectable?: boolean;
  onRunDnsCheck?: (fqdns: string[]) => void;
}

export default function ResultsTable({ scanId, selectable, onRunDnsCheck }: Props) {
  const [data, setData]                 = useState<PaginatedResponse<Subdomain> | null>(null);
  const [search, setSearch]             = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [hasIp, setHasIp]               = useState<boolean | undefined>(undefined);
  const [offset, setOffset]             = useState(0);
  const [selection, setSelection]       = useState<Set<string>>(new Set());
  const headerCheckRef                  = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const result = await api.scans.results(scanId, {
        offset,
        limit:  LIMIT,
        search: search       || undefined,
        source: sourceFilter || undefined,
        has_ip: hasIp,
      });
      setData(result);
    } catch (e) {
      console.error(e);
    }
  }, [scanId, offset, search, sourceFilter, hasIp]);

  useEffect(() => { load(); }, [load]);

  // Reset offset and selection when filters change
  useEffect(() => { setOffset(0); setSelection(new Set()); }, [search, sourceFilter, hasIp]);

  const pageItems = data?.items ?? [];

  // Keep header checkbox indeterminate state in sync
  useEffect(() => {
    const el = headerCheckRef.current;
    if (!el) return;
    const all  = pageItems.length > 0 && pageItems.every((s) => selection.has(s.fqdn));
    const some = pageItems.some((s) => selection.has(s.fqdn));
    el.checked       = all;
    el.indeterminate = some && !all;
  });

  function togglePage() {
    const allSelected = pageItems.every((s) => selection.has(s.fqdn));
    const next = new Set(selection);
    if (allSelected) pageItems.forEach((s) => next.delete(s.fqdn));
    else             pageItems.forEach((s) => next.add(s.fqdn));
    setSelection(next);
  }

  function toggleRow(fqdn: string, checked: boolean) {
    const next = new Set(selection);
    if (checked) next.add(fqdn);
    else         next.delete(fqdn);
    setSelection(next);
  }

  const colSpan = selectable ? 5 : 4;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            className="pl-8"
            placeholder="Search FQDNs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <Input
          className="w-36"
          placeholder="Source filter"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
        />

        <select
          className="rounded-md border border-input bg-transparent px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={hasIp === undefined ? "" : String(hasIp)}
          onChange={(e) =>
            setHasIp(e.target.value === "" ? undefined : e.target.value === "true")
          }
        >
          <option value="">All</option>
          <option value="true">Has IP</option>
          <option value="false">No IP</option>
        </select>

        <div className="flex gap-1 ml-auto flex-wrap">
          {selectable && selection.size > 0 && (
            <Button
              size="sm"
              onClick={() => onRunDnsCheck?.(Array.from(selection))}
            >
              <Shield className="h-3 w-3 mr-1.5" />
              DNS Security Check ({selection.size})
            </Button>
          )}
          <Button size="sm" variant="outline" asChild>
            <a href={api.scans.exportUrl(scanId, "csv")} download>
              <Download className="h-3 w-3 mr-1" />CSV
            </a>
          </Button>
          <Button size="sm" variant="outline" asChild>
            <a href={api.scans.exportUrl(scanId, "json")} download>
              <Download className="h-3 w-3 mr-1" />JSON
            </a>
          </Button>
        </div>
      </div>

      {data && (
        <p className="text-xs text-muted-foreground">
          {data.total.toLocaleString()} subdomains
          {selectable && selection.size > 0 && (
            <span className="text-foreground ml-2">· {selection.size} selected</span>
          )}
        </p>
      )}

      <div className="rounded-lg border border-border overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              {selectable && (
                <th className="w-10 px-3 py-2.5 text-center">
                  <input
                    type="checkbox"
                    ref={headerCheckRef}
                    className="h-3.5 w-3.5 rounded accent-primary"
                    onChange={togglePage}
                  />
                </th>
              )}
              <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Domain</th>
              <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">FQDN</th>
              <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">IPs</th>
              <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Sources</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((sub) => (
              <tr
                key={sub.id}
                className="border-b border-border/40 hover:bg-muted/30 transition-colors"
              >
                {selectable && (
                  <td className="px-3 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      className="h-3.5 w-3.5 rounded accent-primary"
                      checked={selection.has(sub.fqdn)}
                      onChange={(e) => toggleRow(sub.fqdn, e.target.checked)}
                    />
                  </td>
                )}
                <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{sub.domain ?? "—"}</td>
                <td className="px-4 py-2 font-mono text-xs">{sub.fqdn}</td>
                <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                  {sub.ip_addresses?.join(", ") ?? "—"}
                </td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-1">
                    {sub.sources.map((s) => (
                      <Badge key={s} variant="secondary" className="text-xs font-mono">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={colSpan} className="px-4 py-10 text-center text-muted-foreground text-sm">
                  No results
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
            {offset + 1}–{Math.min(offset + LIMIT, data.total)} of {data.total.toLocaleString()}
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
