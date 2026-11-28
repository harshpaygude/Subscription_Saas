"use client";

import { BarChart3, PieChart } from "lucide-react";

// Visual Palette for Anthropic Charts
export const ANTHROPIC_CHART_PALETTE = ["#7c3aed", "#2563eb", "#059669", "#d97706", "#ec4899", "#0891b2"];

export function formatTokensCompact(value: number | undefined) {
  if (value == null || value === 0) return "0";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

/**
 * Interactive SVG Donut / Pie Chart Component
 */
export function DonutPieChart({
  title,
  subtitle,
  items,
  centerTotal,
  centerLabel,
}: {
  title: string;
  subtitle?: string;
  items: Array<{ label: string; value: number; color?: string; formatted?: string }>;
  centerTotal?: string;
  centerLabel?: string;
}) {
  const total = items.reduce((sum, item) => sum + (item.value > 0 ? item.value : 0), 0);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;

  let cumulativePercent = 0;

  return (
    <div className="hub-chart-card" style={{ flex: 1, minWidth: 260 }}>
      <div className="hub-chart-heading">
        <div>
          <p className="hub-eyebrow">{subtitle || "Distribution"}</p>
          <h3>{title}</h3>
        </div>
        <PieChart size={17} style={{ color: "var(--accent, #7c3aed)", opacity: 0.85 }} />
      </div>

      {total <= 0 ? (
        <p className="hub-settings-muted" style={{ padding: "30px 0", textAlign: "center" }}>
          No usage reported for this category.
        </p>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 8 }}>
          <div style={{ position: "relative", width: 130, height: 130, flexShrink: 0 }}>
            <svg width={130} height={130} viewBox="0 0 140 140" style={{ transform: "rotate(-90deg)" }}>
              {items.map((item, idx) => {
                const color = item.color || ANTHROPIC_CHART_PALETTE[idx % ANTHROPIC_CHART_PALETTE.length];
                const slicePercent = item.value / total;
                const strokeDash = slicePercent * circumference;
                const strokeOffset = circumference - strokeDash;
                const rotate = cumulativePercent * 360;
                cumulativePercent += slicePercent;

                return (
                  <circle
                    key={item.label}
                    cx={70}
                    cy={70}
                    r={radius}
                    fill="transparent"
                    stroke={color}
                    strokeWidth={20}
                    strokeDasharray={`${strokeDash} ${strokeOffset}`}
                    strokeDashoffset={0}
                    style={{
                      transform: `rotate(${rotate}deg)`,
                      transformOrigin: "70px 70px",
                      transition: "stroke-dasharray 0.4s ease",
                    }}
                  >
                    <title>{`${item.label}: ${item.formatted || item.value.toLocaleString()} (${(
                      slicePercent * 100
                    ).toFixed(1)}%)`}</title>
                  </circle>
                );
              })}
            </svg>
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                pointerEvents: "none",
                textAlign: "center",
              }}
            >
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary, #0f172a)", lineHeight: 1.1 }}>
                {centerTotal || formatTokensCompact(total)}
              </span>
              <small style={{ fontSize: 9.5, color: "#64748b", marginTop: 2, textTransform: "uppercase" }}>
                {centerLabel || "Total"}
              </small>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 7, flex: 1, minWidth: 0 }}>
            {items.map((item, idx) => {
              const color = item.color || ANTHROPIC_CHART_PALETTE[idx % ANTHROPIC_CHART_PALETTE.length];
              const percent = total > 0 ? (item.value / total) * 100 : 0;
              return (
                <div
                  key={item.label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: 12,
                    gap: 8,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        backgroundColor: color,
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        color: "#475569",
                        fontWeight: 500,
                      }}
                      title={item.label}
                    >
                      {item.label}
                    </span>
                  </div>
                  <strong style={{ fontWeight: 600, flexShrink: 0, fontSize: 11.5 }}>
                    {item.formatted || `${percent.toFixed(1)}%`}
                  </strong>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Visual Daily / Period Trend Bar Chart
 */
export function DailyTrendChart({
  title,
  subtitle,
  bars,
  type = "token",
}: {
  title: string;
  subtitle?: string;
  bars: Array<{ label: string; value: number; formatted?: string }>;
  type?: "token" | "cost";
}) {
  const maxVal = Math.max(...bars.map((b) => b.value), 1);

  return (
    <div className="hub-chart-card" style={{ flex: 1, minWidth: 260 }}>
      <div className="hub-chart-heading">
        <div>
          <p className="hub-eyebrow">{subtitle || "Activity"}</p>
          <h3>{title}</h3>
        </div>
        <BarChart3 size={17} style={{ color: type === "token" ? "#7c3aed" : "#059669", opacity: 0.85 }} />
      </div>

      <div className="hub-mini-bars" style={{ height: 100, gap: 8, paddingBottom: 6 }}>
        {bars.map((bar, idx) => {
          const heightPercent = Math.max(8, (bar.value / maxVal) * 100);
          return (
            <div
              key={idx}
              className="hub-mini-bar-column"
              title={`${bar.label}: ${bar.formatted || bar.value.toLocaleString()}`}
            >
              <div
                className={`hub-mini-bar ${type}`}
                style={{
                  height: `${heightPercent}%`,
                  borderRadius: "4px 4px 0 0",
                  backgroundColor: type === "token" ? "#7c3aed" : "#059669",
                  transition: "height 0.4s ease",
                }}
              />
              <small style={{ fontSize: 9.5 }}>{bar.label}</small>
            </div>
          );
        })}
      </div>
    </div>
  );
}
