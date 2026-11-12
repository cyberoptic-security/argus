"use client";

import { useEffect, useRef, useState } from "react";
import { Trash2, Upload, Save, Download } from "lucide-react";
import { api } from "@/lib/api";
import type { ApiKeyExport, ApiKeyStatus, Wordlist } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const NEEDS_SECRET = new Set(["censys"]);

interface KeyState {
  key: string;
  secret: string;
}

export default function ConfigPage() {
  const [apiKeys, setApiKeys]   = useState<ApiKeyStatus[]>([]);
  const [wordlists, setWordlists] = useState<Wordlist[]>([]);
  const [inputs, setInputs]     = useState<Record<string, KeyState>>({});
  const [saving, setSaving]     = useState<string | null>(null);
  const [wlName, setWlName]     = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef                 = useRef<HTMLInputElement>(null);
  const importRef               = useRef<HTMLInputElement>(null);
  const [keyIo, setKeyIo]       = useState<string | null>(null);

  async function refresh() {
    const [keys, wls] = await Promise.all([
      api.config.apiKeys().catch(() => [] as ApiKeyStatus[]),
      api.config.wordlists().catch(() => [] as Wordlist[]),
    ]);
    setApiKeys(keys);
    setWordlists(wls);
  }

  useEffect(() => { refresh(); }, []);

  function setInput(source: string, field: keyof KeyState, value: string) {
    setInputs((prev) => {
      const current = prev[source] ?? { key: "", secret: "" };
      return { ...prev, [source]: { ...current, [field]: value } };
    });
  }

  async function saveKey(source: string) {
    const input = inputs[source];
    if (!input?.key) return;
    setSaving(source);
    try {
      await api.config.setApiKey(source, {
        api_key:    input.key,
        api_secret: NEEDS_SECRET.has(source) ? input.secret || undefined : undefined,
      });
      setInputs((prev) => ({ ...prev, [source]: { key: "", secret: "" } }));
      await refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(null);
    }
  }

  async function exportKeys() {
    setKeyIo(null);
    try {
      const data = await api.config.exportApiKeys();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `argus-api-keys-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setKeyIo(`Exported ${data.keys.length} key${data.keys.length === 1 ? "" : "s"}.`);
    } catch (e) {
      console.error(e);
      setKeyIo("Export failed.");
    }
  }

  async function importKeys(file: File) {
    setKeyIo(null);
    try {
      const data = JSON.parse(await file.text()) as ApiKeyExport;
      if (!Array.isArray(data.keys)) throw new Error("Invalid export file");
      const result = await api.config.importApiKeys(data);
      const parts = [`Imported ${result.imported.length} key${result.imported.length === 1 ? "" : "s"}.`];
      if (result.skipped.length > 0) {
        parts.push(`Skipped: ${result.skipped.join(", ")}.`);
      }
      setKeyIo(parts.join(" "));
      await refresh();
    } catch (e) {
      console.error(e);
      setKeyIo("Import failed — check the file is a valid Argus key export.");
    } finally {
      if (importRef.current) importRef.current.value = "";
    }
  }

  async function deleteKey(source: string) {
    await api.config.deleteApiKey(source).catch(console.error);
    await refresh();
  }

  async function uploadWordlist() {
    const file = fileRef.current?.files?.[0];
    if (!file || !wlName.trim()) return;
    setUploading(true);
    try {
      await api.config.uploadWordlist(wlName.trim(), file);
      setWlName("");
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setUploading(false);
    }
  }

  async function deleteWordlist(id: number) {
    await api.config.deleteWordlist(id).catch(console.error);
    await refresh();
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-semibold">Configuration</h1>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>API Keys</CardTitle>
            <div className="flex items-center gap-2">
              <input
                ref={importRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) importKeys(file);
                }}
              />
              <Button size="sm" variant="outline" onClick={exportKeys}>
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Export
              </Button>
              <Button size="sm" variant="outline" onClick={() => importRef.current?.click()}>
                <Upload className="h-3.5 w-3.5 mr-1.5" />
                Import
              </Button>
            </div>
          </div>
          {keyIo && <p className="text-xs text-muted-foreground mt-2">{keyIo}</p>}
        </CardHeader>
        <CardContent className="space-y-5">
          {apiKeys.length === 0 && (
            <p className="text-sm text-muted-foreground">No keyed sources configured.</p>
          )}
          {apiKeys.map(({ source, has_key }) => (
            <div
              key={source}
              className="space-y-2 pb-5 border-b border-border/50 last:border-0 last:pb-0"
            >
              <div className="flex items-center justify-between">
                <Label className="font-mono">{source}</Label>
                {has_key && (
                  <div className="flex items-center gap-2">
                    <Badge variant="success">configured</Badge>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => deleteKey(source)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </div>
              <Input
                type="password"
                placeholder={NEEDS_SECRET.has(source) ? "API ID" : "API key"}
                value={inputs[source]?.key ?? ""}
                onChange={(e) => setInput(source, "key", e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && saveKey(source)}
              />
              {NEEDS_SECRET.has(source) && (
                <Input
                  type="password"
                  placeholder="API secret"
                  value={inputs[source]?.secret ?? ""}
                  onChange={(e) => setInput(source, "secret", e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && saveKey(source)}
                />
              )}
              <Button
                size="sm"
                onClick={() => saveKey(source)}
                disabled={saving === source || !inputs[source]?.key}
              >
                <Save className="h-3.5 w-3.5 mr-1.5" />
                {saving === source ? "Saving…" : "Save"}
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Wordlists</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {wordlists.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No wordlists uploaded. The built-in default is used for brute force.
            </p>
          )}
          {wordlists.map((wl) => (
            <div key={wl.id} className="flex items-center justify-between py-1">
              <div>
                <p className="text-sm font-medium">{wl.name}</p>
                <p className="text-xs text-muted-foreground">
                  {wl.entry_count.toLocaleString()} words ·{" "}
                  {new Date(wl.created_at).toLocaleDateString()}
                </p>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                onClick={() => deleteWordlist(wl.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}

          <div className="pt-3 border-t border-border/50 space-y-2">
            <Label>Upload wordlist</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Name"
                value={wlName}
                onChange={(e) => setWlName(e.target.value)}
                className="flex-1"
              />
              <input ref={fileRef} type="file" accept=".txt" className="hidden" />
              <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()}>
                <Upload className="h-3.5 w-3.5 mr-1.5" />
                Choose file
              </Button>
            </div>
            <Button
              size="sm"
              onClick={uploadWordlist}
              disabled={uploading || !wlName.trim()}
            >
              {uploading ? "Uploading…" : "Upload"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
