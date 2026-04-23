"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { Scan } from "@/lib/types";
import ScanForm from "@/components/ScanForm";
import LiveTerminal from "@/components/LiveTerminal";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  const [activeScan, setActiveScan] = useState<Scan | null>(null);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
      <Card>
        <CardHeader>
          <CardTitle>New Scan</CardTitle>
        </CardHeader>
        <CardContent>
          <ScanForm onScanCreated={setActiveScan} />
        </CardContent>
      </Card>

      <div className="space-y-3">
        {activeScan ? (
          <>
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                Live Output
              </h2>
              <Button size="sm" variant="outline" asChild>
                <Link href={`/scans/${activeScan.id}`}>
                  Full results <ExternalLink className="ml-1.5 h-3 w-3" />
                </Link>
              </Button>
            </div>
            <LiveTerminal scanId={activeScan.id} />
          </>
        ) : (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center h-64 gap-2 text-muted-foreground">
              <p className="text-sm">Start a scan to see live output here</p>
              <p className="text-xs">Results stream in real-time via SSE</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
