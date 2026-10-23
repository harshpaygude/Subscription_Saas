"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  Building2,
  Eye,
  EyeOff,
  Lock,
  Mail,
} from "lucide-react";

import Link from "next/link";

import { useRouter } from "next/navigation";

import { register } from "@/lib/api";


export default function RegisterPage() {

  const router = useRouter();


  const [organizationName, setOrganizationName] =
    useState("");


  const [email, setEmail] =
    useState("");


  const [password, setPassword] =
    useState("");


  const [confirmPassword, setConfirmPassword] =
    useState("");


  const [showPassword, setShowPassword] =
    useState(false);


  const [showConfirmPassword, setShowConfirmPassword] =
    useState(false);


  const [loading, setLoading] =
    useState(false);


  const [error, setError] =
    useState("");


  const [success, setSuccess] =
    useState("");


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {

    event.preventDefault();

    setError("");
    setSuccess("");


    /* ========================= */
    /* VALIDATION */
    /* ========================= */

    if (!organizationName.trim()) {

      setError(
        "Please enter your organization name."
      );

      return;
    }


    if (!email.trim()) {

      setError(
        "Please enter your email address."
      );

      return;
    }


    if (password.length < 8) {

      setError(
        "Password must be at least 8 characters."
      );

      return;
    }


    if (password !== confirmPassword) {

      setError(
        "Passwords do not match."
      );

      return;
    }


    setLoading(true);


    /* ========================= */
    /* REGISTER */
    /* ========================= */

    try {

      await register(
        email.trim(),
        password,
        organizationName.trim()
      );


      setSuccess(
        "Account created successfully. Redirecting to login..."
      );


      setTimeout(() => {

        router.replace("/login");

      }, 1200);


    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to create your account."
      );

    } finally {

      setLoading(false);

    }
  }


  return (
    <main className="login-page">

      <div className="login-container">


        {/* ========================= */}
        {/* BRAND */}
        {/* ========================= */}

        <div className="login-brand">

          <div className="login-logo">
            S
          </div>


          <div>

            <div className="login-brand-name">

              UniSora

              <span>
                PRO
              </span>

            </div>


            <div className="login-brand-subtitle">
              Subscription Central
            </div>

          </div>

        </div>


        {/* ========================= */}
        {/* REGISTER CARD */}
        {/* ========================= */}

        <div className="login-card">


          <div className="login-heading">

            <h1>
              Create your account
            </h1>


            <p>
              Set up your UniSora workspace and
              start managing your subscriptions.
            </p>

          </div>


          {/* ========================= */}
          {/* ERROR */}
          {/* ========================= */}

          {error && (

            <div className="login-error">
              {error}
            </div>

          )}


          {/* ========================= */}
          {/* SUCCESS */}
          {/* ========================= */}

          {success && (

            <div className="login-success">
              {success}
            </div>

          )}


          {/* ========================= */}
          {/* FORM */}
          {/* ========================= */}

          <form
            onSubmit={handleSubmit}
            className="login-form"
          >


            {/* ORGANIZATION */}

            <div className="form-field">

              <label htmlFor="organization">
                Organization Name
              </label>


              <div className="input-wrapper">

                <Building2 size={17} />


                <input
                  id="organization"
                  type="text"
                  placeholder="Your company name"
                  value={organizationName}
                  onChange={(event) =>
                    setOrganizationName(
                      event.target.value
                    )
                  }
                  required
                />

              </div>

            </div>


            {/* EMAIL */}

            <div className="form-field">

              <label htmlFor="register-email">
                Work Email
              </label>


              <div className="input-wrapper">

                <Mail size={17} />


                <input
                  id="register-email"
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


            {/* PASSWORD */}

            <div className="form-field">

              <label htmlFor="register-password">
                Password
              </label>


              <div className="input-wrapper">

                <Lock size={17} />


                <input
                  id="register-password"
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  placeholder="Create a password"
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
                    setShowPassword(
                      !showPassword
                    )
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


            {/* CONFIRM PASSWORD */}

            <div className="form-field">

              <label htmlFor="confirm-password">
                Confirm Password
              </label>


              <div className="input-wrapper">

                <Lock size={17} />


                <input
                  id="confirm-password"
                  type={
                    showConfirmPassword
                      ? "text"
                      : "password"
                  }
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value
                    )
                  }
                  required
                />


                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowConfirmPassword(
                      !showConfirmPassword
                    )
                  }
                >

                  {showConfirmPassword ? (
                    <EyeOff size={17} />
                  ) : (
                    <Eye size={17} />
                  )}

                </button>

              </div>

            </div>


            {/* SUBMIT */}

            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >

              {loading
                ? "Creating account..."
                : "Create UniSora Account"}

            </button>

          </form>


          {/* ========================= */}
          {/* LOGIN LINK */}
          {/* ========================= */}

          <p className="register-text">

            Already have an account?

            <Link href="/login">
              Sign in
            </Link>

          </p>


        </div>


        {/* FOOTER */}

        <div className="login-footer">
          © 2026 UniSora. Subscription Management Platform.
        </div>


      </div>

    </main>
  );
}
