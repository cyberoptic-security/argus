import { Globe, Key } from "lucide-react";
import type { SourceStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  source: SourceStatus;
}

export default function SourceCard({ source }: Props) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          {source.requires_key ? (
            <Key className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
          <div>
            <p className="font-medium text-sm">{source.display_name}</p>
            <p className="text-xs text-muted-foreground">
              {source.requires_key ? "API key required" : "Free — no key"}
            </p>
          </div>
        </div>
        <Badge variant={source.enabled ? "success" : "secondary"}>
          {source.enabled ? "ready" : source.requires_key ? "no key" : "disabled"}
        </Badge>
      </CardContent>
    </Card>
  );
}
