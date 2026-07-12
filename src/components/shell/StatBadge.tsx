type Variant = "neutral" | "warning" | "info";

const styles: Record<Variant, string> = {
  neutral:
    "text-muted-foreground border-white/[0.08] bg-transparent",
  warning:
    "text-amber-300/90 border-amber-300/25 bg-amber-300/[0.06]",
  info:
    "text-sky-300/90 border-sky-300/25 bg-sky-300/[0.06]",
};

export function StatBadge({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: Variant;
}) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-2 py-0.5",
        "text-[10px] uppercase tracking-widest tabular-nums",
        styles[variant],
      ].join(" ")}
    >
      {children}
    </span>
  );
}