import { useState } from "react";
import {
  LayoutGrid,
  Building2,
  Package,
  Users,
  ArrowLeftRight,
  Calendar,
  Wrench,
  ClipboardCheck,
  BarChart3,
  Settings,
} from "lucide-react";

interface NavItem {
  label: string;
  icon: typeof LayoutGrid;
  href: string;
}

const overview: NavItem[] = [{ label: "Dashboard", icon: LayoutGrid, href: "/dashboard" }];

const inventory: NavItem[] = [
  { label: "Organization", icon: Building2, href: "/dashboard/organization" },
  { label: "Assets", icon: Package, href: "/dashboard/assets" },
  { label: "Allocations", icon: Users, href: "/dashboard/allocations" },
  { label: "Transfers", icon: ArrowLeftRight, href: "/dashboard/transfers" },
];

const operations: NavItem[] = [
  { label: "Bookings", icon: Calendar, href: "/dashboard/bookings" },
  { label: "Maintenance", icon: Wrench, href: "/dashboard/maintenance" },
  { label: "Audits", icon: ClipboardCheck, href: "/dashboard/audits" },
];

const insights: NavItem[] = [
  { label: "Reports", icon: BarChart3, href: "/dashboard/reports" },
  { label: "Settings", icon: Settings, href: "/dashboard/settings" },
];

function NavGroup({
  title,
  items,
  activeHref,
}: {
  title: string;
  items: NavItem[];
  activeHref: string;
}) {
  return (
    <div className="mb-6">
      <p
        className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wide"
        style={{ color: "var(--af-text-muted)" }}
      >
        {title}
      </p>
      <div className="flex flex-col gap-1">
        {items.map((item) => {
          const isActive = item.href === activeHref;
          return (
            <a
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors"
              style={{
                backgroundColor: isActive ? "var(--af-active)" : "transparent",
                color: isActive ? "#FFFFFF" : "var(--af-text-primary)",
              }}
            >
              <item.icon size={18} />
              {item.label}
            </a>
          );
        })}
      </div>
    </div>
  );
}

export default function Sidebar({ activeHref = "/dashboard" }: { activeHref?: string }) {
  return (
    <aside
      className="flex h-screen w-64 flex-col justify-between p-4"
      style={{ backgroundColor: "var(--af-bg-elevated)" }}
    >
      <div>
        <div className="mb-8 flex items-center gap-2 px-2 py-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full font-semibold"
            style={{ backgroundColor: "var(--af-active)", color: "#fff" }}
          >
            A
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "var(--af-text-primary)" }}>
              AssetFlow
            </p>
            <p className="text-[10px]" style={{ color: "var(--af-text-muted)" }}>
              OPS WORKSPACE
            </p>
          </div>
        </div>

        <NavGroup title="Overview" items={overview} activeHref={activeHref} />
        <NavGroup title="Inventory" items={inventory} activeHref={activeHref} />
        <NavGroup title="Operations" items={operations} activeHref={activeHref} />
        <NavGroup title="Insights" items={insights} activeHref={activeHref} />
      </div>

      <div
        className="rounded-2xl bg-white p-4"
        style={{ boxShadow: "var(--af-shadow-card)" }}
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--af-text-muted)" }}>
          Plan
        </p>
        <p className="text-sm font-semibold" style={{ color: "var(--af-text-primary)" }}>
          Operations · Team
        </p>
      </div>
    </aside>
  );
}
