import { Link } from "@tanstack/react-router";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { StatBadge } from "./StatBadge";

type BadgeVariant = "neutral" | "warning" | "info";

type Props = {
  icon: LucideIcon;
  label: string;
  value: string;
  delta?: string;
  deltaVariant?: BadgeVariant;
  href?: string;
  hrefLabel?: string;
  tone?: "default" | "alt";
};

export function MetricCard({
  icon: Icon,
  label,
  value,
  delta,
  deltaVariant = "neutral",
  href,
  hrefLabel = "Open module",
  tone = "default",
}: Props) {
  return (
    <div
      className={[
        "group rounded-xl p-5 flex flex-col justify-between min-h-[168px] border border-white/[0.06] hover:border-white/10 transition-colors duration-150",
        tone === "alt" ? "bg-surface-alt" : "bg-surface",
      ].join(" ")}
    >
      <div className="flex items-start justify-between">
        <div className="h-8 w-8 rounded-lg border border-white/10 flex items-center justify-center text-primary/80">
          <Icon size={16} strokeWidth={1.75} />
        </div>
        {delta && <StatBadge variant={deltaVariant}>{delta}</StatBadge>}
      </div>
      <div className="mt-6">
        <div className="text-3xl md:text-4xl font-bold text-primary leading-none tabular-nums">
          {value}
        </div>
        <div className="mt-2 text-xs text-muted-foreground">{label}</div>
      </div>
      {href && (
        <Link
          to={href}
          className="mt-4 inline-flex items-center gap-1.5 text-xs text-primary/90 hover:text-primary transition-[gap,color] duration-150 hover:gap-2.5"
        >
          {hrefLabel}
          <ArrowRight
            size={14}
            className="transition-transform duration-150 group-hover:-rotate-45"
          />
        </Link>
      )}
    </div>
  );
}