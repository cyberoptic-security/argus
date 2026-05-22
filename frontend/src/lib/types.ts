export type ScanStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface Scan {
  id: string;
  name: string | null;
  domains: string[];
  status: ScanStatus;
  sources: string[];
  options: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface ScanCreate {
  name?: string;
  domains: string[];
  sources: string[];
  options?: Record<string, unknown>;
}

export interface Subdomain {
  id: number;
  scan_id: string;
  domain: string | null;
  fqdn: string;
  ip_addresses: string[] | null;
  sources: string[];
  created_at: string;
}

export interface ApiKeyStatus {
  source: string;
  has_key: boolean;
  has_secret: boolean;
}

export interface Wordlist {
  id: number;
  name: string;
  entry_count: number;
  created_at: string;
}

export interface SourceStatus {
  name: string;
  display_name: string;
  requires_key: boolean;
  enabled: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export type DnsCheckJobStatus = "pending" | "running" | "completed" | "failed";
export type DnsFindingStatus = "pass" | "warn" | "fail" | "info";
export type DnsSeverity = "critical" | "high" | "medium" | "low" | "info";
export type DnsCheckType = "spf" | "dmarc" | "mx" | "dkim";

export interface DnsCheckResult {
  id: number;
  check_id: string;
  fqdn: string;
  check_type: DnsCheckType;
  status: DnsFindingStatus;
  severity: DnsSeverity;
  title: string;
  detail: string;
  raw_value: string | null;
  recommendation: string | null;
  created_at: string;
}

export interface DnsCheck {
  id: string;
  scan_id: string | null;
  fqdns: string[];
  status: DnsCheckJobStatus;
  created_at: string;
  completed_at: string | null;
  results: DnsCheckResult[];
}

export interface SSEEvent {
  type: "subdomain" | "progress" | "error" | "done";
  fqdn?: string;
  source?: string;
  sources?: string[];
  ips?: string[] | null;
  ts?: number;
  total?: number;
  status?: string;
  message?: string;
}
