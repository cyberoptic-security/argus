import type {
  ApiKeyExport,
  ApiKeyImportResult,
  ApiKeyStatus,
  DnsCheck,
  PaginatedResponse,
  Scan,
  ScanCreate,
  SourceStatus,
  Subdomain,
  Wordlist,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

type QueryParams = Record<string, string | number | boolean | undefined>;

function qs(params: QueryParams): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const api = {
  scans: {
    list: (offset = 0, limit = 20) =>
      req<PaginatedResponse<Scan>>(`/api/scans${qs({ offset, limit })}`),

    get: (id: string) => req<Scan>(`/api/scans/${id}`),

    create: (body: ScanCreate) =>
      req<Scan>("/api/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),

    cancel: (id: string) =>
      fetch(`${BASE}/api/scans/${id}/cancel`, { method: "POST" }),

    delete: async (id: string) => {
      const res = await fetch(`${BASE}/api/scans/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(`${res.status}: ${text}`);
      }
    },

    results: (id: string, params: QueryParams = {}) =>
      req<PaginatedResponse<Subdomain>>(`/api/scans/${id}/results${qs(params)}`),

    exportUrl: (id: string, format: "json" | "csv") =>
      `${BASE}/api/scans/${id}/export?format=${format}`,

    streamUrl: (id: string) => `${BASE}/api/scans/${id}/stream`,
  },

  config: {
    apiKeys: () => req<ApiKeyStatus[]>("/api/config/api-keys"),

    setApiKey: (source: string, body: { api_key: string; api_secret?: string }) =>
      req<ApiKeyStatus>(`/api/config/api-keys/${source}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),

    deleteApiKey: (source: string) =>
      fetch(`${BASE}/api/config/api-keys/${source}`, { method: "DELETE" }),

    exportApiKeys: () => req<ApiKeyExport>("/api/config/api-keys/export"),

    importApiKeys: (body: ApiKeyExport) =>
      req<ApiKeyImportResult>("/api/config/api-keys/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),

    wordlists: () => req<Wordlist[]>("/api/config/wordlists"),

    uploadWordlist: (name: string, file: File) => {
      const form = new FormData();
      form.append("file", file);
      return req<Wordlist>(`/api/config/wordlists${qs({ name })}`, {
        method: "POST",
        body: form,
      });
    },

    deleteWordlist: (id: number) =>
      fetch(`${BASE}/api/config/wordlists/${id}`, { method: "DELETE" }),
  },

  sources: {
    list: () => req<SourceStatus[]>("/api/sources"),
  },

  dnsChecks: {
    create: (body: { fqdns: string[]; scan_id?: string }) =>
      req<DnsCheck>("/api/dns-checks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),

    get: (id: string) => req<DnsCheck>(`/api/dns-checks/${id}`),

    getByScan: (scanId: string) => req<DnsCheck>(`/api/dns-checks/by-scan/${scanId}`),
  },
};
