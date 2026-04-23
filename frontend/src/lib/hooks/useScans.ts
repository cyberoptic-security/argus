"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { PaginatedResponse, Scan } from "../types";

export function useScans(limit = 20) {
  const [data, setData] = useState<PaginatedResponse<Scan> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.scans.list(offset, limit));
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [offset, limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, error, refresh, offset, setOffset };
}
