import { useState } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { api, setTokens, ApiError } from "../lib/api-client";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const data = await api.post<LoginResponse>("/auth/login", {
        email,
        password,
      });
      setTokens(data.access_token, data.refresh_token);
      navigate({ to: "/dashboard" });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Invalid email or password.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div
        className="w-full max-w-sm rounded-[20px] p-8"
        style={{
          backgroundColor: "var(--af-surface)",
          border: "1px solid var(--af-border)",
          backdropFilter: "var(--af-blur-glass)",
          boxShadow: "var(--af-shadow-card)",
        }}
      >
        <Link
          to="/"
          className="mb-8 block text-xl font-semibold"
          style={{ color: "var(--af-text-primary)" }}
        >
          AssetFlow
        </Link>

        <h1
          className="mb-1 text-2xl font-normal"
          style={{ fontFamily: "Fraunces, serif", color: "var(--af-text-primary)" }}
        >
          Sign in
        </h1>
        <p className="mb-6 text-sm" style={{ color: "var(--af-text-secondary)" }}>
          Enter your credentials to access your workspace.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-xs font-medium"
              style={{ color: "var(--af-text-secondary)" }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm outline-none"
              style={{
                backgroundColor: "rgba(255,255,255,0.04)",
                border: "1px solid var(--af-border)",
                color: "var(--af-text-primary)",
              }}
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-xs font-medium"
              style={{ color: "var(--af-text-secondary)" }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm outline-none"
              style={{
                backgroundColor: "rgba(255,255,255,0.04)",
                border: "1px solid var(--af-border)",
                color: "var(--af-text-primary)",
              }}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-sm" style={{ color: "#F87171" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-full px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: "var(--af-active)" }}
            onMouseEnter={(e) => {
              if (!submitting) e.currentTarget.style.backgroundColor = "var(--af-active-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "var(--af-active)";
            }}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
