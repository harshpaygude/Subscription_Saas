"use client";

import { useEffect, useState } from "react";
import { IntroAnimation } from "@/components/auth/IntroAnimation";
import { LoginBrandPanel } from "@/components/auth/LoginBrandPanel";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  const [showIntro, setShowIntro] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Don't show intro if user navigated back from dashboard
    const skipIntro = sessionStorage.getItem("intro_shown");
    if (skipIntro) {
      setShowIntro(false);
    }
  }, []);

  function handleIntroComplete() {
    sessionStorage.setItem("intro_shown", "1");
    setShowIntro(false);
  }

  if (!mounted) {
    return <div className="intro-overlay intro-hold" aria-hidden="true"><div className="intro-content"><div className="intro-logo-wrap"><div className="intro-logo">U</div></div></div></div>;
  }

  return (
    <>
      {showIntro && <IntroAnimation onComplete={handleIntroComplete} />}
      <main className="lp-shell" style={{ opacity: showIntro ? 0 : 1, transition: "opacity 0.3s ease" }}>
        <LoginBrandPanel />
        <LoginForm />
      </main>
    </>
  );
}
