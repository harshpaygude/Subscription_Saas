"use client";

import { useEffect, useState } from "react";

const STATEMENTS = [
  "Every subscription.\nOne clear view.",
  "Every license.\nFully accountable.",
  "Every expense.\nUnder control.",
];

export function LoginBrandPanel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) return;

    const cycle = () => {
      setVisible(false);
      setTimeout(() => {
        setActiveIndex((prev) => (prev + 1) % STATEMENTS.length);
        setVisible(true);
      }, 500);
    };

    const interval = setInterval(cycle, 3200);
    return () => clearInterval(interval);
  }, []);

  const lines = STATEMENTS[activeIndex].split("\n");

  return (
    <div className="lp-brand-panel">
      {/* Background decorative shapes */}
      <div className="lp-shape lp-shape-1" />
      <div className="lp-shape lp-shape-2" />
      <div className="lp-shape lp-shape-3" />

      <div className="lp-brand-inner">
        {/* Logo + name */}
        <div className="lp-logo-row">
          <div className="lp-logo-mark">U</div>
          <div>
            <div className="lp-app-name">
              UniSora <span>PRO</span>
            </div>
            <div className="lp-app-sub">Intelligent Subscription Management</div>
          </div>
        </div>

        {/* Animated statements */}
        <div className="lp-statement-wrap">
          <div className={`lp-statement ${visible ? "lp-visible" : "lp-hidden"}`}>
            {lines.map((line, i) => (
              <div key={i} className="lp-statement-line">{line}</div>
            ))}
          </div>
          <div className="lp-accent-line" />
        </div>

        {/* Bottom trust indicators */}
        <div className="lp-trust-row">
          <div className="lp-trust-item">
            <span className="lp-trust-dot" />
            Multi-cloud integrations
          </div>
          <div className="lp-trust-item">
            <span className="lp-trust-dot" />
            SOC 2 ready architecture
          </div>
          <div className="lp-trust-item">
            <span className="lp-trust-dot" />
            Real-time cost tracking
          </div>
        </div>
      </div>
    </div>
  );
}
