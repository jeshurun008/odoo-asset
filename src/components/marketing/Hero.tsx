import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Link } from "@tanstack/react-router";
import ShaderCard from "../shell/ShaderCard";

export default function Hero() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = ["Overview", "Modules", "Security", "Pricing", "FAQ"];

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--af-bg)" }}>
      <section className="relative min-h-screen overflow-hidden">
        <div className="relative flex h-full flex-col">
          {/* Nav */}
          <nav className="relative z-20 mx-auto flex w-full max-w-7xl items-center justify-between px-8 py-6">
            <span className="text-2xl font-semibold" style={{ color: "var(--af-text-primary)" }}>
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
          <div className="flex flex-1 flex-col items-center justify-center px-6 pb-16 pt-4 text-center">
            <p
              className="mb-4 text-sm font-semibold tracking-wider"
              style={{ color: "var(--af-text-secondary)" }}
            >
              ASSET &amp; RESOURCE MANAGEMENT
            </p>

            <h1 className="leading-none tracking-tighter">
              <span
                className="block text-6xl font-normal md:text-7xl lg:text-8xl"
                style={{ color: "var(--af-text-muted)" }}
              >
                Every asset.
              </span>
              <span
                className="block text-6xl font-semibold md:text-7xl lg:text-8xl"
                style={{ color: "var(--af-text-primary)", marginTop: "-12px" }}
              >
                Accounted for.
              </span>
            </h1>

            <p
              className="mb-6 mt-6 max-w-2xl text-lg md:text-xl"
              style={{ color: "var(--af-text-secondary)" }}
            >
              One workspace for allocations, transfers, maintenance, and
              audits.
            </p>

            <div className="mb-14 flex items-center justify-center gap-4">
              <button
                className="rounded-full bg-white px-4 py-2 font-medium transition-colors hover:opacity-80"
                style={{ color: "var(--af-text-primary)", boxShadow: "var(--af-shadow-card)" }}
              >
                See how it works
              </button>
              <Link
                to="/dashboard"
                className="rounded-full px-4 py-2 font-medium text-white transition-colors"
                style={{ backgroundColor: "var(--af-active)" }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.backgroundColor = "var(--af-active-hover)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.backgroundColor = "var(--af-active)")
                }
              >
                Get started
              </Link>
            </div>

            {/* Signature shader panel */}
            <ShaderCard
              eyebrow="New"
              title="See where every asset lives, in real time"
              cta={{ label: "Explore the platform" }}
              className="h-72 w-full max-w-3xl"
            />
          </div>
        </div>
      </section>
    </div>
  );
}
