"use client";

import { useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { api } from "@/lib/api";
import type { Scan, SourceStatus, Wordlist } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
  onScanCreated: (scan: Scan) => void;
}

export default function ScanForm({ onScanCreated }: Props) {
  const [domains, setDomains]               = useState("");
  const [name, setName]                     = useState("");
  const [sources, setSources]               = useState<SourceStatus[]>([]);
  const [selected, setSelected]             = useState<Set<string>>(new Set(["crtsh"]));
  const [includeBrute, setIncludeBrute]     = useState(false);
  const [wordlists, setWordlists]           = useState<Wordlist[]>([]);
  const [wordlistId, setWordlistId]         = useState("");
  const [loading, setLoading]               = useState(false);
  const [error, setError]                   = useState<string | null>(null);

  useEffect(() => {
    api.sources.list()
      .then((s) => {
        setSources(s);
        setSelected(new Set(s.filter((x) => x.enabled).map((x) => x.name)));
      })
      .catch(() => {});
    api.config.wordlists().then(setWordlists).catch(() => {});
  }, []);

  function toggle(name: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const domainList = domains.split(/[\n,]+/).map((d) => d.trim()).filter(Boolean);
    if (!domainList.length) { setError("Enter at least one domain"); return; }

    const sourcesToRun = Array.from(selected);
    if (includeBrute) sourcesToRun.push("brute");
    if (!sourcesToRun.length) { setError("Select at least one source"); return; }

    setLoading(true);
    try {
      const scan = await api.scans.create({
        name: name.trim() || undefined,
        domains: domainList,
        sources: sourcesToRun,
        options: wordlistId ? { wordlist_id: Number(wordlistId) } : {},
      });
      onScanCreated(scan);
      setDomains("");
      setName("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const free   = sources.filter((s) => !s.requires_key);
  const keyed  = sources.filter((s) =>  s.requires_key);

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-1.5">
        <Label>Domains</Label>
        <textarea
          className="w-full h-24 rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none font-mono"
          placeholder={"example.com\ntarget.io"}
          value={domains}
          onChange={(e) => setDomains(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">One per line or comma-separated</p>
      </div>

      <div className="space-y-1.5">
        <Label>Name <span className="text-muted-foreground font-normal">(optional)</span></Label>
        <Input placeholder="My scan" value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div className="space-y-3">
        <Label>Sources</Label>

        {free.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">Free</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {free.map((src) => (
                <label key={src.name} className="flex items-center gap-2 cursor-pointer select-none text-sm">
                  <input
                    type="checkbox"
                    checked={selected.has(src.name)}
                    onChange={() => toggle(src.name)}
                    className="rounded border-input accent-blue-500"
                  />
                  {src.display_name}
                </label>
              ))}
            </div>
          </div>
        )}

        {keyed.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">Keyed</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {keyed.map((src) => (
                <label
                  key={src.name}
                  className={`flex items-center gap-2 select-none text-sm ${
                    src.enabled ? "cursor-pointer" : "cursor-not-allowed opacity-40"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(src.name)}
                    onChange={() => src.enabled && toggle(src.name)}
                    disabled={!src.enabled}
                    className="rounded border-input accent-blue-500"
                  />
                  {src.display_name}
                  {!src.enabled && <span className="text-xs">(no key)</span>}
                </label>
              ))}
            </div>
          </div>
        )}

        <div>
          <p className="text-xs text-muted-foreground mb-2">Active</p>
          <label className="flex items-center gap-2 cursor-pointer select-none text-sm">
            <input
              type="checkbox"
              checked={includeBrute}
              onChange={(e) => setIncludeBrute(e.target.checked)}
              className="rounded border-input accent-blue-500"
            />
            DNS Brute Force
          </label>
          {includeBrute && (
            <div className="mt-2 ml-6 space-y-1.5">
              <Label className="text-xs">Wordlist</Label>
              <select
                className="w-full rounded-md border border-input bg-transparent px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={wordlistId}
                onChange={(e) => setWordlistId(e.target.value)}
              >
                <option value="">Built-in default</option>
                {wordlists.map((wl) => (
                  <option key={wl.id} value={String(wl.id)}>
                    {wl.name} ({wl.entry_count.toLocaleString()} words)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" disabled={loading} className="w-full">
        {loading ? (
          <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Starting…</>
        ) : (
          <><Play className="mr-2 h-4 w-4" />Start Scan</>
        )}
      </Button>
    </form>
  );
}
