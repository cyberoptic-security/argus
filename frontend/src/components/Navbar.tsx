"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/scans",   label: "Scans" },
  { href: "/sources", label: "Sources" },
  { href: "/config",  label: "Config" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-border bg-card">
      <div className="container mx-auto px-4 max-w-7xl flex items-center gap-6 h-14">
        <Link href="/" className="flex items-center gap-2 font-semibold text-primary shrink-0">
          <Shield className="h-5 w-5" />
          Argus
        </Link>
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "text-sm transition-colors",
              pathname.startsWith(href)
                ? "text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
