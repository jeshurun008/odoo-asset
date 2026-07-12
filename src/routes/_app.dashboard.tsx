import { createFileRoute, Link } from "@tanstack/react-router";
import {
  UserCheck,
  CalendarClock,
  ClipboardCheck,
  ArrowRight,
} from "lucide-react";
import { MovementChart } from "@/components/shell/MovementChart";
import { DashboardMetrics } from "@/components/dashboard/DashboardMetrics";

export const Route = createFileRoute("/_app/dashboard")({
  component: Dashboard,
  head: () => ({
    meta: [
      { title: "Dashboard — AssetFlow" },
      {
        name: "description",
        content:
          "Live overview of assets, allocations, transfers, and maintenance across your organization.",
      },
    ],
  }),
});

function Dashboard() {
  return (
    <div className="max-w-7xl mx-auto w-full space-y-8 pt-2 animate-in fade-in duration-300">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
            Sunday · Jul 12
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-primary tracking-tight">
            Good morning, <span className="font-serif-italic">Maya</span>.
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            3 allocations need approval and 2 maintenance windows open today.
          </p>
        </div>
        <Link
          to="/assets"
          className="group inline-flex items-center gap-2 self-start md:self-auto rounded-full bg-surface border border-white/[0.06] hover:border-white/10 px-4 py-2 text-xs text-primary hover:bg-surface-alt transition-[gap,background,border-color] duration-150 hover:gap-3"
        >
          Register asset
          <ArrowRight
            size={14}
            className="transition-transform duration-150 group-hover:-rotate-45"
          />
        </Link>
      </header>

      <DashboardMetrics />

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-3 md:gap-4">
        <div className="lg:col-span-2 rounded-xl bg-surface border border-white/[0.06] p-5 md:p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                This week
              </div>
              <h2 className="mt-1 text-lg text-primary font-bold">
                Movement across{" "}
                <span className="font-serif-italic">every location</span>
              </h2>
            </div>
            <Link
              to="/reports"
              className="text-xs text-brand-cream-soft hover:text-primary transition-colors"
            >
              View reports
            </Link>
          </div>
          <MovementChart />
        </div>

        <div className="rounded-xl bg-surface border border-white/[0.06] p-5 md:p-6 space-y-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Attention
            </div>
            <h2 className="mt-1 text-lg text-primary font-bold">
              Awaiting <span className="font-serif-italic">you</span>
            </h2>
          </div>
          <ul className="space-y-2">
            {[
              { icon: UserCheck, label: "Approve 3 allocation requests", to: "/allocations" },
              { icon: CalendarClock, label: "Confirm 2 room bookings", to: "/bookings" },
              { icon: ClipboardCheck, label: "Close Q3 audit — Warehouse 4", to: "/audits" },
            ].map((row) => {
              const Icon = row.icon;
              return (
                <li key={row.label}>
                  <Link
                    to={row.to}
                    className="group flex items-center gap-3 rounded-lg bg-surface-alt border border-white/[0.06] hover:border-white/10 px-3 py-2.5 hover:bg-surface-alt/80 transition-colors duration-150"
                  >
                    <span className="h-7 w-7 rounded-md border border-white/10 flex items-center justify-center shrink-0">
                      <Icon size={14} className="text-primary/70" strokeWidth={1.75} />
                    </span>
                    <span className="text-xs text-brand-cream-soft group-hover:text-primary flex-1">
                      {row.label}
                    </span>
                    <ArrowRight
                      size={14}
                      className="text-muted-foreground transition-transform duration-150 group-hover:-rotate-45 group-hover:text-primary"
                    />
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </section>
    </div>
  );
}
