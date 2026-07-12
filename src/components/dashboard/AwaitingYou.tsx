import { Link } from "@tanstack/react-router";
import { AlertTriangle, ClipboardCheck, ArrowRight, CheckCircle2 } from "lucide-react";
import { useAwaitingYou } from "@/hooks/useAwaitingYou";

export function AwaitingYou() {
  const { items, isLoading, isError } = useAwaitingYou();

  if (isLoading) {
    return (
      <ul className="space-y-2">
        {[0, 1].map((i) => (
          <li
            key={i}
            className="h-11 animate-pulse rounded-lg bg-surface-alt border border-white/[0.06]"
          />
        ))}
      </ul>
    );
  }

  if (isError) {
    return (
      <p className="text-xs text-muted-foreground">
        Couldn't load pending items.
      </p>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-lg bg-surface-alt border border-white/[0.06] px-3 py-2.5">
        <span className="h-7 w-7 rounded-md border border-white/10 flex items-center justify-center shrink-0">
          <CheckCircle2 size={14} className="text-primary/70" strokeWidth={1.75} />
        </span>
        <span className="text-xs text-brand-cream-soft">
          You're all caught up.
        </span>
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {items.map((item) => {
        const Icon = item.kind === "overdue" ? AlertTriangle : ClipboardCheck;
        return (
          <li key={item.id}>
            <Link
              to={item.to}
              className="group flex items-center gap-3 rounded-lg bg-surface-alt border border-white/[0.06] hover:border-white/10 px-3 py-2.5 hover:bg-surface-alt/80 transition-colors duration-150"
            >
              <span className="h-7 w-7 rounded-md border border-white/10 flex items-center justify-center shrink-0">
                <Icon size={14} className="text-primary/70" strokeWidth={1.75} />
              </span>
              <span className="text-xs text-brand-cream-soft group-hover:text-primary flex-1">
                {item.label}
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
  );
}
