"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Building2, Eye, EyeOff, Lock, Mail, CheckCircle2 } from "lucide-react";
import { register, login } from "@/lib/api";
import { LoginBrandPanel } from "@/components/auth/LoginBrandPanel";

export default function RegisterPage() {
  const router = useRouter();

  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!organizationName.trim()) {
      setError("Please enter your organization name.");
      return;
    }

    if (!email.trim()) {
      setError("Please enter your work email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await register(email.trim(), password, organizationName.trim());
      setSuccess("Account created successfully! Preparing your onboarding workspace…");

      // Auto-login so user lands directly on the onboarding page
      try {
        const loginRes = await login(email.trim(), password);
        localStorage.setItem("access_token", loginRes.access_token);
        setTimeout(() => {
          router.replace("/onboarding");
        }, 700);
      } catch {
        setTimeout(() => {
          router.replace("/login");
        }, 1200);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create your account."
      );
      setLoading(false);
    }
  }

  return (
    <main className="lp-shell">
      <LoginBrandPanel />

      <div className="lp-form-panel">
        <div className="lp-form-card">
          {/* Mobile brand header */}
          <div className="lp-mobile-brand">
            <div className="lp-logo-mark-sm">U</div>
            <span className="lp-mobile-brand-name">
              UniSora <span>PRO</span>
            </span>
          </div>

          <div className="lp-form-heading">
            <h1>Create your account</h1>
            <p>Set up your UniSora workspace and start managing your company subscriptions.</p>
          </div>

          {error && (
            <div className="lp-error-banner" role="alert">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}

          {success && (
            <div className="lp-success-banner" role="status">
              <CheckCircle2 size={15} style={{ flexShrink: 0 }} />
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="lp-form" noValidate>
            {/* Organization Name */}
            <div className="lp-field">
              <label htmlFor="reg-org">Organization name</label>
              <div className="lp-input-wrap">
                <Building2 size={15} className="lp-input-icon" />
                <input
                  id="reg-org"
                  type="text"
                  placeholder="Acme Technologies Inc."
                  value={organizationName}
                  onChange={(e) => setOrganizationName(e.target.value)}
                  autoComplete="organization"
                  required
                />
              </div>
            </div>

            {/* Work Email */}
            <div className="lp-field">
              <label htmlFor="reg-email">Work email</label>
              <div className="lp-input-wrap">
                <Mail size={15} className="lp-input-icon" />
                <input
                  id="reg-email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="lp-field">
              <label htmlFor="reg-password">Password</label>
              <div className="lp-input-wrap">
                <Lock size={15} className="lp-input-icon" />
                <input
                  id="reg-password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
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

            {/* Confirm Password */}
            <div className="lp-field">
              <label htmlFor="reg-confirm-password">Confirm password</label>
              <div className="lp-input-wrap">
                <Lock size={15} className="lp-input-icon" />
                <input
                  id="reg-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="lp-toggle-pw"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="lp-submit-btn"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="lp-btn-spinner" />
                  Creating workspace…
                </>
              ) : (
                "Create UniSora Account"
              )}
            </button>
          </form>

          <p className="lp-signup-text">
            Already have an account?{" "}
            <Link href="/login" className="lp-signup-link">
              Sign in
            </Link>
          </p>

          <div className="lp-form-footer">
            © 2026 UniSora. Subscription Management Platform.
          </div>
        </div>
      </div>
    </main>
  );
}
