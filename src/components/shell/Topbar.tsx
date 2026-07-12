import { Link, useRouterState } from "@tanstack/react-router";
import { Bell, Search, ChevronRight } from "lucide-react";

function toCrumbs(pathname: string) {
  if (pathname === "/") return [{ label: "Dashboard", to: "/" }];
  const parts = pathname.split("/").filter(Boolean);
  return [
    { label: "Home", to: "/" },
    ...parts.map((p, i) => ({
      label: p.charAt(0).toUpperCase() + p.slice(1),
      to: "/" + parts.slice(0, i + 1).join("/"),
    })),
  ];
}

export function Topbar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const crumbs = toCrumbs(pathname);

  return (
    <div className="p-2 md:p-4">
      <div className="flex items-center justify-between gap-4 md:gap-8 rounded-full bg-black/90 border border-white/5 px-4 py-2 md:px-6 shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_10px_30px_-15px_rgba(0,0,0,0.9)]">
        <nav className="flex items-center gap-1.5 text-xs md:text-sm min-w-0">
          {crumbs.map((c, i) => {
            const last = i === crumbs.length - 1;
            return (
              <span key={c.to} className="flex items-center gap-1.5 min-w-0">
                {i > 0 && (
                  <ChevronRight
                    size={12}
                    className="text-muted-foreground/60 shrink-0"
                  />
                )}
                {last ? (
                  <span className="text-primary truncate">{c.label}</span>
                ) : (
                  <Link
                    to={c.to}
                    className="text-brand-cream-soft hover:text-primary truncate"
                  >
                    {c.label}
                  </Link>
                )}
              </span>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 md:gap-4">
          <button
            type="button"
            className="hidden sm:flex items-center gap-2 rounded-full bg-surface border border-white/[0.06] hover:border-white/10 px-3 py-1.5 text-xs text-muted-foreground hover:text-primary transition-colors duration-150"
          >
            <Search size={14} />
            <span>Search assets, people, tags…</span>
            <span className="ml-4 text-[10px] uppercase tracking-widest text-muted-foreground/70">
              ⌘K
            </span>
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="relative rounded-full p-2 text-brand-cream-soft hover:text-primary hover:bg-surface transition-colors duration-150"
          >
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
          </button>
          <button
            type="button"
            className="flex items-center gap-2 rounded-full bg-surface pl-1 pr-3 py-1 text-xs text-primary hover:bg-surface-alt transition-colors duration-150"
          >
            <span className="h-7 w-7 rounded-full bg-surface-alt flex items-center justify-center text-[11px] font-bold">
              MR
            </span>
            <span className="hidden md:inline">Maya R.</span>
          </button>
        </div>
      </div>
    </div>
  );
}