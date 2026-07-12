import { useEffect, useRef, useState } from "react";
import { NeuroNoise } from "@paper-design/shaders-react";

interface ShaderCardProps {
  eyebrow?: string;
  title: string;
  cta?: { label: string; onClick?: () => void };
  className?: string;
}

/**
 * Contained animated shader panel — the app's one signature visual element.
 * Use ONCE per screen (hero feature panel on landing, one highlight card
 * on the dashboard). Never as a full-page background.
 */
export default function ShaderCard({
  eyebrow,
  title,
  cta,
  className = "",
}: ShaderCardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 600, height: 320 });
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-[20px] ${className}`}
      style={{ boxShadow: "var(--af-shadow-card)" }}
    >
      <NeuroNoise
        width={size.width}
        height={size.height}
        colorFront="#ffffff"
        colorMid="#47a6ff"
        colorBack="#111111"
        brightness={0.05}
        contrast={0.3}
        speed={reducedMotion ? 0 : 1}
        fit="cover"
      />
      <div className="absolute inset-0 flex flex-col justify-end p-6">
        {eyebrow && (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-white/70">
            {eyebrow}
          </p>
        )}
        <h3 className="mb-4 text-2xl font-semibold leading-tight text-white">
          {title}
        </h3>
        {cta && (
          <button
            onClick={cta.onClick}
            className="flex w-fit items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-white/90"
          >
            {cta.label}
          </button>
        )}
      </div>
    </div>
  );
}
