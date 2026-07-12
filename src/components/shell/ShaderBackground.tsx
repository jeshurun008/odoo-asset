import { useEffect, useState } from "react";
import { NeuroNoise } from "@paper-design/shaders-react";

/**
 * Full-viewport animated background. Mount this ONCE in __root.tsx so it
 * persists across route changes instead of re-initializing on every page.
 */
export default function ShaderBackground() {
  const [size, setSize] = useState({ width: 1920, height: 1080 });
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const updateSize = () =>
      setSize({ width: window.innerWidth, height: window.innerHeight });
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: -1,
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
      }}
      aria-hidden="true"
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
    </div>
  );
}
