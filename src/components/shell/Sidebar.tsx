import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Building2,
  Package,
  UserCheck,
  ArrowLeftRight,
  CalendarClock,
  Wrench,
  ClipboardCheck,
  BarChart3,
  Settings,
  type LucideIcon,
} from "lucide-react";

type NavItem = { to: string; label: string; icon: LucideIcon };
type NavGroup = { label: string; items: NavItem[] };

const groups: NavGroup[] = [
  {
    label: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Inventory",
    items: [
      { to: "/organization", label: "Organization", icon: Building2 },
      { to: "/assets", label: "Assets", icon: Package },
      { to: "/allocations", label: "Allocations", icon: UserCheck },
      { to: "/transfers", label: "Transfers", icon: ArrowLeftRight },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/bookings", label: "Bookings", icon: CalendarClock },
      { to: "/maintenance", label: "Maintenance", icon: Wrench },
      { to: "/audits", label: "Audits", icon: ClipboardCheck },
    ],
  },
  {
    label: "Insights",
    items: [
      { to: "/reports", label: "Reports", icon: BarChart3 },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="hidden md:flex md:w-60 lg:w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground bg-noise-subtle">
      <div className="px-6 pt-6 pb-8">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-surface flex items-center justify-center">
            <span className="font-serif-italic text-primary text-lg leading-none">A</span>
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold text-primary tracking-tight">AssetFlow</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Ops workspace
            </div>
          </div>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-6 space-y-6">
        {groups.map((group) => (
          <div key={group.label}>
            <div className="px-3 mb-2 text-[10px] uppercase tracking-widest text-muted-foreground">
              {group.label}
            </div>
            <ul className="space-y-1">
              {group.items.map((item) => {
                const active =
                  item.to === "/"
                    ? pathname === "/"
                    : pathname === item.to || pathname.startsWith(item.to + "/");
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className={[
                        "group flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors duration-150",
                        active
                          ? "bg-surface text-primary border border-white/10"
                          : "text-brand-cream-soft hover:text-primary hover:bg-surface/60 border border-transparent",
                      ].join(" ")}
                    >
                      <Icon size={18} strokeWidth={1.75} />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="px-4 pb-6">
        <div className="rounded-xl bg-surface p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">
            Plan
          </div>
          <div className="text-sm text-primary font-bold">Operations · Team</div>
          <div className="mt-2 text-xs text-muted-foreground">
            <span className="font-serif-italic text-primary">2,481</span> assets tracked
          </div>
        </div>
      </div>
    </aside>
  );
}