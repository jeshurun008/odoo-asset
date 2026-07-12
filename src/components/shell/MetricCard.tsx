import type { LucideIcon } from "lucide-react";
import StatBadge from "./StatBadge";

interface MetricCardProps {
  icon: LucideIcon;
  iconTint?: "mint" | "sky" | "peach" | "lilac";
  value: string;
  label: string;
  badgeLabel?: string;
  badgeVariant?: "mint" | "sky" | "peach" | "lilac";
  linkLabel?: string;
  onLinkClick?: () => void;
}

const tintBg: Record<string, string> = {
  mint: "var(--af-mint-bg)",
  sky: "var(--af-sky-bg)",
  peach: "var(--af-peach-bg)",
  lilac: "var(--af-lilac-bg)",
};

const tintText: Record<string, string> = {
  mint: "var(--af-mint-text)",
  sky: "var(--af-sky-text)",
  peach: "var(--af-peach-text)",
  lilac: "var(--af-lilac-text)",
};

export default function MetricCard({
  icon: Icon,
  iconTint = "sky",
  value,
  label,
  badgeLabel,
  badgeVariant = "mint",
  linkLabel,
  onLinkClick,
}: MetricCardProps) {
  return (
    <div
      className="rounded-[20px] p-5"
      style={{
        backgroundColor: "var(--af-surface)",
        backdropFilter: "var(--af-blur-glass)",
        WebkitBackdropFilter: "var(--af-blur-glass)",
        border: "1px solid var(--af-border)",
        boxShadow: "var(--af-shadow-card)",
      }}
    >
      <div className="mb-4 flex items-center justify-between">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-full"
          style={{ backgroundColor: tintBg[iconTint] }}
        >
          <Icon size={18} style={{ color: tintText[iconTint] }} />
        </div>
        {badgeLabel && <StatBadge label={badgeLabel} variant={badgeVariant} />}
      </div>

      <p className="text-3xl font-semibold" style={{ color: "var(--af-text-primary)" }}>
        {value}
      </p>
      <p className="mb-3 text-sm" style={{ color: "var(--af-text-secondary)" }}>
        {label}
      </p>

      {linkLabel && (
        <button
          onClick={onLinkClick}
          className="flex items-center gap-1 text-sm font-medium transition-colors hover:opacity-70"
          style={{ color: "var(--af-text-primary)" }}
        >
          {linkLabel}
          <span className="inline-block -rotate-45 transition-transform group-hover:translate-x-0.5">
            →
          </span>
        </button>
      )}
    </div>
  );
}