"use client";

import { useEffect, useState } from "react";

interface Props {
  onComplete: () => void;
}

export function IntroAnimation({ onComplete }: Props) {
  const [phase, setPhase] = useState<"enter" | "hold" | "exit">("enter");

  useEffect(() => {
    // Respect prefers-reduced-motion
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) {
      onComplete();
      return;
    }

    const t1 = setTimeout(() => setPhase("hold"), 600);
    const t2 = setTimeout(() => setPhase("exit"), 1100);
    const t3 = setTimeout(() => onComplete(), 1400);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [onComplete]);

  return (
    <div className={`intro-overlay intro-${phase}`} aria-hidden="true">
      <div className="intro-content">
        <div className="intro-logo-wrap">
          <div className="intro-logo">U</div>
          <div className="intro-glow" />
        </div>
        <div className="intro-brand">
          <span className="intro-brand-name">UniSora</span>
          <span className="intro-brand-pro">PRO</span>
        </div>
        <p className="intro-tagline">Intelligent Subscription Management</p>
      </div>
    </div>
  );
}
