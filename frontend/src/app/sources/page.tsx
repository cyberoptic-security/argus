"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { SourceStatus } from "@/lib/types";
import SourceCard from "@/components/SourceCard";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceStatus[]>([]);

  useEffect(() => {
    api.sources.list().then(setSources).catch(console.error);
  }, []);

  const free  = sources.filter((s) => !s.requires_key);
  const keyed = sources.filter((s) =>  s.requires_key);

  const enabledCount = sources.filter((s) => s.enabled).length;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Sources</h1>
          {sources.length > 0 && (
            <p className="text-sm text-muted-foreground mt-1">
              {enabledCount} of {sources.length} sources ready ·{" "}
              <Link href="/config" className="text-primary hover:underline">
                manage API keys →
              </Link>
            </p>
          )}
        </div>
      </div>

      {free.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Free sources
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {free.map((src) => <SourceCard key={src.name} source={src} />)}
          </div>
        </section>
      )}

      {keyed.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Keyed sources
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {keyed.map((src) => <SourceCard key={src.name} source={src} />)}
          </div>
        </section>
      )}

      {sources.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Could not reach the backend. Make sure it&apos;s running at{" "}
          <code className="font-mono text-foreground">
            {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
          </code>
          .
        </p>
      )}
    </div>
  );
}
