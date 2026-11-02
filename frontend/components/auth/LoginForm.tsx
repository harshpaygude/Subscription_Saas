"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import Link from "next/link";
import { login } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await login(email, password);
      localStorage.setItem("access_token", response.access_token);
      // Check onboarding status before redirecting
      router.replace("/onboarding");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Invalid email or password."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="lp-form-panel">
      <div className="lp-form-card">
        {/* Mobile brand header */}
        <div className="lp-mobile-brand">
          <div className="lp-logo-mark-sm">U</div>
          <span className="lp-mobile-brand-name">UniSora <span>PRO</span></span>
        </div>

        <div className="lp-form-heading">
          <h1>Welcome back</h1>
          <p>Sign in to manage your subscriptions, licenses and company resources.</p>
        </div>

        {error && (
          <div className="lp-error-banner" role="alert">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="lp-form" noValidate>
          <div className="lp-field">
            <label htmlFor="lp-email">Work email</label>
            <div className="lp-input-wrap">
              <Mail size={15} className="lp-input-icon" />
              <input
                id="lp-email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div className="lp-field">
            <div className="lp-field-header">
              <label htmlFor="lp-password">Password</label>
              <button type="button" className="lp-forgot-link">Forgot password?</button>
            </div>
            <div className="lp-input-wrap">
              <Lock size={15} className="lp-input-icon" />
              <input
                id="lp-password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="lp-toggle-pw"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="lp-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="lp-btn-spinner" />
            ) : null}
            {loading ? "Signing in…" : "Sign in to UniSora"}
          </button>
        </form>

        <p className="lp-signup-text">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="lp-signup-link">Create account</Link>
        </p>

        <div className="lp-form-footer">
          © 2026 UniSora. Subscription Management Platform.
        </div>
      </div>
    </div>
  );
}
