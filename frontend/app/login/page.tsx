"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";

import { login } from "@/lib/api";


export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await login(
        email,
        password
      );

      localStorage.setItem(
        "access_token",
        response.access_token
      );

      router.replace("/dashboard");

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Invalid email or password."
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <main className="login-page">

      <div className="login-container">

        <div className="login-brand">

          <div className="login-logo">
            S
          </div>

          <div>
            <div className="login-brand-name">
              SubHub
              <span>PRO</span>
            </div>

            <div className="login-brand-subtitle">
              Subscription Central
            </div>
          </div>

        </div>


        <div className="login-card">

          <div className="login-heading">

            <h1>
              Welcome back
            </h1>

            <p>
              Sign in to manage your subscriptions,
              licenses and spending.
            </p>

          </div>


          {error && (
            <div className="login-error">
              {error}
            </div>
          )}


          <form
            onSubmit={handleSubmit}
            className="login-form"
          >

            <div className="form-field">

              <label htmlFor="email">
                Email
              </label>

              <div className="input-wrapper">

                <Mail size={17} />

                <input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  required
                />

              </div>

            </div>


            <div className="form-field">

              <div className="password-label">

                <label htmlFor="password">
                  Password
                </label>

                <button
                  type="button"
                  className="forgot-password"
                >
                  Forgot password?
                </button>

              </div>


              <div className="input-wrapper">

                <Lock size={17} />

                <input
                  id="password"
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  required
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(!showPassword)
                  }
                >
                  {showPassword ? (
                    <EyeOff size={17} />
                  ) : (
                    <Eye size={17} />
                  )}
                </button>

              </div>

            </div>


            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading
                ? "Signing in..."
                : "Sign in to SubHub"}
            </button>

          </form>


          <div className="login-divider">
            <span>OR</span>
          </div>


          <div className="social-login">

            <button
              type="button"
              className="social-button"
            >
              Continue with Microsoft
            </button>

            <button
              type="button"
              className="social-button"
            >
              Continue with Google
            </button>

          </div>


          <p className="register-text">

            Don't have an account?

            <a href="/register">
              Create account
            </a>

          </p>

        </div>


        <div className="login-footer">
          © 2026 SubHub. Subscription Management Platform.
        </div>

      </div>

    </main>
  );
}
