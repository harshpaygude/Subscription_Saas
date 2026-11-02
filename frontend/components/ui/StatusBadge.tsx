"use client";

import React from "react";

export type StatusVariant = "success" | "warning" | "error" | "info" | "neutral" | "accent";

interface StatusBadgeProps {
  variant?: StatusVariant;
  dot?: boolean;
  children: React.ReactNode;
  size?: "sm" | "md";
  className?: string;
}

export function StatusBadge({
  variant = "neutral",
  dot = true,
  children,
  size = "md",
  className = "",
}: StatusBadgeProps) {
  return (
    <span className={`status-badge status-${variant} size-${size} ${className}`}>
      {dot && <span className="status-badge-dot" />}
      {children}
    </span>
  );
}
