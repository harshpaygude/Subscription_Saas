"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (token) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="loading-screen">
      <div className="brand-logo-mark">U</div>
      <div className="hub-spinner" />
      <h1 className="section-title" style={{ marginTop: 4 }}>UniSora PRO</h1>
      <p className="section-subtitle">Preparing your workspace…</p>
    </div>
  );
}
