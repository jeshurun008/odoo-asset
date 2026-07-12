import { Sparkles } from "lucide-react";

type Props = { title: string; kicker: string; description: string };

export function ModuleStub({ title, kicker, description }: Props) {
  return (
    <div className="max-w-4xl mx-auto w-full pt-6 animate-in fade-in duration-300">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
        {kicker}
      </div>
      <h1 className="text-2xl md:text-3xl font-bold text-primary tracking-tight">
        {title}
      </h1>
      <p className="mt-2 text-sm text-muted-foreground max-w-xl">{description}</p>

      <div className="mt-8 rounded-xl bg-surface p-8 flex items-center gap-4">
        <div className="h-10 w-10 rounded-lg bg-surface-alt flex items-center justify-center text-primary">
          <Sparkles size={18} strokeWidth={1.75} />
        </div>
        <div>
          <div className="text-sm text-primary font-bold">
            Module scaffolded
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            Content for <span className="font-serif-italic text-primary">{title}</span> lands here next.
          </div>
        </div>
      </div>
    </div>
  );
}