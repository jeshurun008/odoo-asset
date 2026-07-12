import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import MetricCard from "@/components/shell/MetricCard";
import { Package, UserCheck, ArrowLeftRight, Wrench } from "lucide-react";

// Matches app/schemas/dashboard.py::DashboardKpisResponse exactly.
interface DashboardKpis {
  assets_available: number;
  assets_allocated: number;
  maintenance_today: number;
  upcoming_bookings: number;
  pending_transfers: number;
  upcoming_returns: number;
  overdue_assets: number;
  unread_notifications: number;
}

export function useDashboardKpis() {
  return useQuery({
    queryKey: ["dashboard-kpis"],
    queryFn: () => api.get<DashboardKpis>("/dashboard/kpis"),
  });
}

export function DashboardMetrics() {
  const { data, isLoading, isError } = useDashboardKpis();

  if (isLoading) {
    return (
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-xl bg-surface border border-white/[0.06]"
          />
        ))}
      </section>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl bg-surface border border-white/[0.06] p-6 text-sm text-muted-foreground">
        Couldn't load dashboard data. Check that the backend is running and
        you're signed in.
      </div>
    );
  }

  const kpis = data ?? {
    assets_available: 0,
    assets_allocated: 0,
    maintenance_today: 0,
    upcoming_bookings: 0,
    pending_transfers: 0,
    upcoming_returns: 0,
    overdue_assets: 0,
    unread_notifications: 0,
  };

  // No invented deltas/trends — backend only returns current counts, so
  // "delta" is omitted rather than fabricated. overdue_assets is surfaced
  // as a warning badge where it's genuinely relevant (allocations card).
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
      <MetricCard
        icon={Package}
        label="Assets available"
        value={kpis.assets_available.toLocaleString()}
        href="/assets"
        hrefLabel="Browse inventory"
      />
      <MetricCard
        icon={UserCheck}
        label="Assets allocated"
        value={kpis.assets_allocated.toLocaleString()}
        delta={kpis.overdue_assets > 0 ? `${kpis.overdue_assets} overdue` : undefined}
        deltaVariant="warning"
        href="/allocations"
        hrefLabel="View allocations"
        tone="alt"
      />
      <MetricCard
        icon={ArrowLeftRight}
        label="Pending transfers"
        value={kpis.pending_transfers.toLocaleString()}
        href="/transfers"
        hrefLabel="Open transfers"
      />
      <MetricCard
        icon={Wrench}
        label="Maintenance today"
        value={kpis.maintenance_today.toLocaleString()}
        href="/maintenance"
        hrefLabel="Schedule work"
        tone="alt"
      />
    </section>
  );
}
