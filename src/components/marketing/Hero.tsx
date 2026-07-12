import { useEffect, useRef, useState } from "react";
import {
  Menu,
  X,
  Package,
  ArrowRightLeft,
  Wrench,
  ClipboardCheck,
} from "lucide-react";
import { Link } from "@tanstack/react-router";

export default function Hero() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = ["Overview", "Modules", "Security", "Pricing", "FAQ"];

  const features = [
    {
      icon: Package,
      eyebrow: "ASSETS",
      title: "Every asset, one record",
      description:
        "Track equipment, devices, and inventory from acquisition to retirement, with a single source of truth for status, location, and ownership.",
      accent: "#D4AF7A",
    },
    {
      icon: ArrowRightLeft,
      eyebrow: "TRANSFERS",
      title: "Move assets without losing the trail",
      description:
        "Reassign assets between departments or locations with a full history of who had what, and when it changed hands.",
      accent: "#C9A0DC",
    },
    {
      icon: Wrench,
      eyebrow: "MAINTENANCE",
      title: "Stay ahead of upkeep",
      description:
        "Schedule and log maintenance work so nothing slips through — service history stays attached to the asset itself.",
      accent: "#8FBFA6",
    },
    {
      icon: ClipboardCheck,
      eyebrow: "AUDITS",
      title: "Verify what's actually on the ground",
      description:
        "Run audits against your asset records to catch discrepancies early, with a clear log of what was checked and by whom.",
      accent: "#8CB4D9",
    },
  ];

  return (
    <section className="relative overflow-hidden">
      <div className="relative flex flex-col">
        {/* Nav */}
        <nav className="relative z-20 mx-auto flex w-full max-w-7xl items-center justify-between px-8 py-6">
          <span
            className="text-2xl font-semibold"
            style={{ color: "var(--af-text-primary)" }}
          >
            AssetFlow
          </span>

          <div className="hidden items-center gap-8 md:flex">
            {navItems.map((item) => (
              <a
                key={item}
                href="#"
                className="text-sm font-medium transition-colors hover:opacity-70"
                style={{ color: "var(--af-text-primary)" }}
              >
                {item}
              </a>
            ))}
          </div>

          <button
            className="md:hidden"
            style={{ color: "var(--af-text-primary)" }}
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          {mobileMenuOpen && (
            <div
              className="absolute left-8 right-8 top-full mt-2 rounded-2xl bg-white/95 p-6 backdrop-blur-md md:hidden"
              style={{ boxShadow: "var(--af-shadow-card)" }}
            >
              <div className="flex flex-col gap-4">
                {navItems.map((item) => (
                  <a
                    key={item}
                    href="#"
                    className="text-sm font-medium transition-colors hover:opacity-70"
                    style={{ color: "var(--af-text-primary)" }}
                  >
                    {item}
                  </a>
                ))}
              </div>
            </div>
          )}
        </nav>

        {/* Hero content */}
        <div className="flex flex-col items-center px-6 pb-16 pt-20 text-center md:pt-28">
          <p
            className="mb-4 text-sm font-semibold tracking-wider"
            style={{ color: "var(--af-text-secondary)" }}
          >
            ASSET &amp; RESOURCE MANAGEMENT
          </p>

          <h1
            className="leading-none tracking-tighter"
            style={{ fontFamily: "'Fraunces', serif" }}
          >
            <span
              className="block text-6xl font-normal md:text-7xl lg:text-8xl"
              style={{ color: "var(--af-text-muted)" }}
            >
              Every asset.
            </span>

            <span
              className="block text-6xl font-normal md:text-7xl lg:text-8xl"
              style={{
                color: "var(--af-text-primary)",
                marginTop: "-12px",
              }}
            >
              Accounted for.
            </span>
          </h1>

          <p
            className="mb-6 mt-6 max-w-2xl text-lg md:text-xl"
            style={{ color: "var(--af-text-secondary)" }}
          >
            One workspace for allocations, transfers, maintenance, and audits.
          </p>

          <div className="flex items-center justify-center gap-4">
            <button className="rounded-full bg-white px-4 py-2 font-medium text-black transition-colors hover:bg-white/90">
              See how it works
            </button>

            <Link
              to="/dashboard"
              className="rounded-full px-4 py-2 font-medium text-white transition-colors"
              style={{ backgroundColor: "var(--af-active)" }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.backgroundColor =
                  "var(--af-active-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.backgroundColor = "var(--af-active)")
              }
            >
              Get started
            </Link>
          </div>
        </div>

        {/* Feature sections */}
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-12 px-6 py-12 md:gap-16 md:py-16">
          {features.map((feature, i) => (
            <FeatureRow key={feature.eyebrow} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureRow({
  feature,
  index,
}: {
  feature: {
    icon: React.ComponentType<{ size?: number; strokeWidth?: number; color?: string }>;
    eyebrow: string;
    title: string;
    description: string;
    accent: string;
  };
  index: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const reversed = index % 2 === 1;
  const Icon = feature.icon;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.25, rootMargin: "0px 0px -10% 0px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`flex flex-col items-center gap-8 md:gap-12 ${
        reversed ? "md:flex-row-reverse" : "md:flex-row"
      }`}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible
          ? "translateX(0)"
          : `translateX(${reversed ? "70px" : "-70px"})`,
        transition:
          "opacity 0.9s cubic-bezier(0.16, 1, 0.3, 1), transform 0.9s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* Icon visual */}
      <div className="flex w-full flex-1 items-center justify-center">
        <div
          className="relative flex h-48 w-48 items-center justify-center rounded-[2rem] md:h-56 md:w-56"
          style={{
            background:
              "linear-gradient(155deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.02) 100%)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            border: "1px solid rgba(255,255,255,0.12)",
            boxShadow: `0 8px 40px -8px ${feature.accent}33, inset 0 1px 0 rgba(255,255,255,0.15)`,
          }}
        >
          {/* subtle gradient ring */}
          <div
            className="absolute inset-3 rounded-[1.6rem]"
            style={{
              border: `1px solid ${feature.accent}40`,
            }}
          />
          {/* glow behind icon */}
          <div
            className="absolute h-20 w-20 rounded-full blur-2xl"
            style={{ backgroundColor: `${feature.accent}55` }}
          />
          <Icon size={44} strokeWidth={1.25} color={feature.accent} />
        </div>
      </div>

      {/* Text */}
      <div className="w-full flex-1 text-center md:text-left">
        <div
          className="mb-6 inline-block rounded-2xl px-6 py-5 md:mb-6"
          style={{
            background:
              "linear-gradient(155deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%)",
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            border: "1px solid rgba(255,255,255,0.10)",
            boxShadow: "0 4px 30px -10px rgba(0,0,0,0.35)",
          }}
        >
          <p
            className="mb-3 text-sm font-semibold tracking-[0.2em]"
            style={{ color: feature.accent }}
          >
            {feature.eyebrow}
          </p>

          <h3
            className="mb-4 text-4xl md:text-5xl"
            style={{
              fontFamily: "'Fraunces', serif",
              color: "var(--af-text-primary)",
            }}
          >
            {feature.title}
          </h3>

          <p
            className="text-lg leading-relaxed md:text-xl"
            style={{ color: "var(--af-text-secondary)" }}
          >
            {feature.description}
          </p>
        </div>
      </div>
    </div>
  );
}