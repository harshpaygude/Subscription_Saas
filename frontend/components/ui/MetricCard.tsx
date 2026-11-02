"use client";

import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  onClick?: () => void;
  className?: string;
}

export function MetricCard({
  label,
  value,
  subtext,
  icon,
  trend,
  onClick,
  className = "",
}: MetricCardProps) {
  const isInteractive = Boolean(onClick);

  return (
    <div
      className={`metric-card ${isInteractive ? "is-clickable" : ""} ${className}`}
      onClick={onClick}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
    >
      <div className="metric-card-top">
        <span className="metric-card-label">{label}</span>
        {icon && <div className="metric-card-icon">{icon}</div>}
      </div>

      <div className="metric-card-value-row">
        <span className="metric-card-value">{value}</span>
        {trend && (
          <span
            className={`metric-card-trend ${trend.isPositive ? "is-positive" : "is-negative"}`}
          >
            {trend.value}
          </span>
        )}
      </div>

      {subtext && <p className="metric-card-subtext">{subtext}</p>}
    </div>
  );
}
