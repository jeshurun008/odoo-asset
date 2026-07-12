type BadgeVariant = "mint" | "sky" | "peach" | "lilac";

interface StatBadgeProps {
  label: string;
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string }> = {
  mint: { bg: "var(--af-mint-bg)", text: "var(--af-mint-text)" },
  sky: { bg: "var(--af-sky-bg)", text: "var(--af-sky-text)" },
  peach: { bg: "var(--af-peach-bg)", text: "var(--af-peach-text)" },
  lilac: { bg: "var(--af-lilac-bg)", text: "var(--af-lilac-text)" },
};

export default function StatBadge({ label, variant = "sky" }: StatBadgeProps) {
  const { bg, text } = variantStyles[variant];
  return (
    <span
      className="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium"
      style={{ backgroundColor: bg, color: text }}
    >
      {label}
    </span>
  );
}
