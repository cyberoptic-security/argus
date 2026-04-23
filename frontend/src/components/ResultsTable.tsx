"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { PaginatedResponse, Subdomain } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const LIMIT = 100;

interface Props {
  scanId: string;
}

export default function ResultsTable({ scanId }: Props) {
  const [data, setData]               = useState<PaginatedResponse<Subdomain> | null>(null);
  const [search, setSearch]           = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [hasIp, setHasIp]             = useState<boolean | undefined>(undefined);
  const [offset, setOffset]           = useState(0);

  const load = useCallback(async () => {
    try {
      const result = await api.scans.results(scanId, {
        offset,
        limit: LIMIT,
        search:    search      || undefined,
        source:    sourceFilter || undefined,
        has_ip:    hasIp,
      });
      setData(result);
    } catch (e) {
      console.error(e);
    }
  }, [scanId, offset, search, sourceFilter, hasIp]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => { setOffset(0); }, [search, sourceFilter, hasIp]);

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

        <div className="flex gap-1 ml-auto">
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
        <p className="text-xs text-muted-foreground">{data.total.toLocaleString()} subdomains</p>
      )}

      <div className="rounded-lg border border-border overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="border-b border-border bg-muted/50">
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
                <td colSpan={4} className="px-4 py-10 text-center text-muted-foreground text-sm">
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
