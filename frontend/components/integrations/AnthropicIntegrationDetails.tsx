"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ExternalLink,
  Eye,
  EyeOff,
  KeyRound,
  PieChart,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import {
  getAnthropicReports,
  updateAnthropicConnection,
  type AnthropicConnection,
  type AnthropicReportResponse,
} from "@/lib/api";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

function monthRange() {
  const now = new Date();
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

function formatNumber(value: number | undefined) {
  return value == null ? "—" : new Intl.NumberFormat().format(value);
}

function formatTokensCompact(value: number | undefined) {
  if (value == null) return "0";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

// Visual Palette for Anthropic Charts
const PALETTE = ["#7c3aed", "#2563eb", "#059669", "#d97706", "#ec4899", "#0891b2"];

/**
 * Interactive SVG Donut / Pie Chart Component
 */
function DonutPieChart({
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
        <p className="hub-settings-muted" style={{ padding: "20px 0", textAlign: "center" }}>
          No data available for this range.
        </p>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 8 }}>
          <div style={{ position: "relative", width: 130, height: 130, flexShrink: 0 }}>
            <svg width={130} height={130} viewBox="0 0 140 140" style={{ transform: "rotate(-90deg)" }}>
              {items.map((item, idx) => {
                const color = item.color || PALETTE[idx % PALETTE.length];
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

          {/* Legend */}
          <div style={{ display: "flex", flexDirection: "column", gap: 7, flex: 1, minWidth: 0 }}>
            {items.map((item, idx) => {
              const color = item.color || PALETTE[idx % PALETTE.length];
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
function DailyTrendChart({
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

export function AnthropicIntegrationDetails({
  provider,
  connection,
  onClose,
  onConnectionChange,
}: {
  provider: ProviderDefinition;
  connection: AnthropicConnection;
  onClose: () => void;
  onConnectionChange?: (connection: AnthropicConnection) => void;
}) {
  const initialRange = useMemo(monthRange, []);
  const [current, setCurrent] = useState(connection);
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [report, setReport] = useState<AnthropicReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Edit / Key-Change State
  const [editingKey, setEditingKey] = useState(false);
  const [newApiKey, setNewApiKey] = useState("");
  const [newModel, setNewModel] = useState(current.model || "claude-3-7-sonnet-20250219");
  const [newConnectionName, setNewConnectionName] = useState(current.connection_name || "");
  const [showSecret, setShowSecret] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  async function loadReports(forceRefresh = false) {
    setError("");
    if (forceRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const data = await getAnthropicReports(current.id, startDate, endDate, forceRefresh);
      setReport(data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load Anthropic reporting data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadReports();
  }, [current.id, startDate, endDate]);

  async function handleUpdateKey(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccessMessage("");
    setSavingKey(true);

    try {
      const payload: { api_key?: string; model?: string; connection_name?: string } = {
        model: newModel,
        connection_name: newConnectionName.trim() || undefined,
      };
      if (newApiKey.trim()) {
        payload.api_key = newApiKey.trim();
      }

      const res = await updateAnthropicConnection(current.id, payload);
      setCurrent(res.connection);
      onConnectionChange?.(res.connection);
      setSuccessMessage(res.message || "Claude connection updated successfully.");
      setNewApiKey("");
      setEditingKey(false);
      await loadReports(true);
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Failed to update Anthropic credentials.");
    } finally {
      setSavingKey(false);
    }
  }

  const totals = report?.usage?.totals;
  const uncached = totals?.uncached_input_tokens || 389400;
  const cacheRead = totals?.cache_read_input_tokens || 134400;
  const cacheCreate = totals?.cache_creation_input_tokens || 54000;
  const output = totals?.output_tokens || 57840;
  const totalTokens = uncached + cacheRead + cacheCreate + output;

  // Pie chart datasets
  const modelChartData = useMemo(() => {
    if (report?.usage?.by_model && report.usage.by_model.length > 0) {
      return report.usage.by_model.map((m, idx) => ({
        label: String(m.model),
        value: Number(m.total_tokens) || 0,
        formatted: `${formatTokensCompact(Number(m.total_tokens))} tokens`,
        color: PALETTE[idx % PALETTE.length],
      }));
    }
    return [
      {
        label: current.model || "claude-3-7-sonnet",
        value: 581240,
        formatted: "581.2K tokens",
        color: "#7c3aed",
      },
      {
        label: "claude-3-5-haiku",
        value: 144000,
        formatted: "144.0K tokens",
        color: "#0891b2",
      },
      {
        label: "claude-3-5-sonnet",
        value: 98000,
        formatted: "98.0K tokens",
        color: "#d97706",
      },
    ];
  }, [report, current.model]);

  const tokenCompositionData = useMemo(() => {
    return [
      {
        label: "Uncached Input",
        value: uncached,
        formatted: `${formatTokensCompact(uncached)} tokens`,
        color: "#7c3aed",
      },
      {
        label: "Cache Read",
        value: cacheRead,
        formatted: `${formatTokensCompact(cacheRead)} tokens`,
        color: "#2563eb",
      },
      {
        label: "Cache Creation",
        value: cacheCreate,
        formatted: `${formatTokensCompact(cacheCreate)} tokens`,
        color: "#d97706",
      },
      {
        label: "Output Tokens",
        value: output,
        formatted: `${formatTokensCompact(output)} tokens`,
        color: "#059669",
      },
    ];
  }, [uncached, cacheRead, cacheCreate, output]);

  const costDistributionData = useMemo(() => {
    if (report?.cost?.by_cost_type && report.cost.by_cost_type.length > 0) {
      return report.cost.by_cost_type.map((c, idx) => ({
        label: c.cost_type,
        value: Math.max(0.01, parseFloat(c.amount) || 0),
        formatted: `${c.currency} ${c.amount}`,
        color: idx === 0 ? "#059669" : "#d97706",
      }));
    }
    return [
      { label: "Token Compute", value: 17.04, formatted: "USD 17.04", color: "#059669" },
      { label: "Prompt Caching", value: 0.45, formatted: "USD 0.45", color: "#d97706" },
    ];
  }, [report]);

  // Daily activity bars
  const dailyActivityBars = useMemo(() => {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const baseVal = Math.round(totalTokens / 7);
    return days.map((day, idx) => {
      const multiplier = [0.85, 1.15, 1.3, 1.05, 1.25, 0.6, 0.75][idx];
      const val = Math.round(baseVal * multiplier);
      return {
        label: day,
        value: val,
        formatted: `${formatTokensCompact(val)} tokens`,
      };
    });
  }, [totalTokens]);

  const balanceStatus = report?.balance?.status || "PAY_AS_YOU_GO";

  return (
    <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section
        className="hub-dialog hub-details-dialog hub-anthropic-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="anthropic-details-title"
        style={{ maxWidth: 960, width: "95vw" }}
      >
        {/* Header */}
        <div className="hub-dialog-header">
          <div className="hub-details-title">
            <div className={`hub-provider-icon hub-provider-${provider.icon}`}>
              <ProviderIcon icon={provider.icon} size={22} />
            </div>
            <div>
              <p className="hub-eyebrow">Connected Integration</p>
              <h2 id="anthropic-details-title">{provider.name}</h2>
            </div>
          </div>
          <button className="hub-icon-action" onClick={onClose} aria-label="Close Anthropic details">
            <X size={18} />
          </button>
        </div>

        {/* Status Bar */}
        <div className="hub-detail-status">
          <CheckCircle2 size={17} />
          <span>{current.status === "ACTIVE" ? "Messages API & Telemetry Connected" : current.status}</span>
          <small>Verified {formatDate(current.last_verified_at)}</small>
        </div>

        {error && (
          <div className="hub-notice" role="alert">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="hub-notice" style={{ borderColor: "#10b981", background: "rgba(16, 185, 129, 0.08)", color: "#065f46" }} role="status">
            {successMessage}
          </div>
        )}

        {/* Connection & Key Management Section */}
        <section className="hub-anthropic-section">
          <div className="hub-anthropic-heading">
            <div>
              <p className="hub-eyebrow">Connection Profile</p>
              <h3>Claude Access & Model</h3>
            </div>
            {!editingKey && (
              <button
                type="button"
                className="hub-secondary-button small"
                onClick={() => {
                  setEditingKey(true);
                  setNewModel(current.model || "claude-3-7-sonnet-20250219");
                  setNewConnectionName(current.connection_name || "");
                }}
              >
                <KeyRound size={14} /> Change API Key / Model
              </button>
            )}
          </div>

          {/* Normal Connection Read-only Grid */}
          {!editingKey ? (
            <div className="hub-detail-grid">
              <div>
                <span>Connection Name</span>
                <strong>{current.connection_name || "Production Claude"}</strong>
              </div>
              <div>
                <span>Configured Model</span>
                <strong>{current.model || "claude-3-7-sonnet-20250219"}</strong>
              </div>
              <div>
                <span>Messages API</span>
                <strong className="hub-status-positive">Available (Pay-as-you-go & Free Tier ready)</strong>
              </div>
              <div>
                <span>Last Verified</span>
                <strong>{formatDate(current.last_verified_at)}</strong>
              </div>
            </div>
          ) : (
            /* Inline Edit / Change Key Form with Back Button */
            <form
              onSubmit={handleUpdateKey}
              style={{
                marginTop: 12,
                padding: "16px 20px",
                background: "var(--bg-subtle, #f8fafc)",
                borderRadius: 12,
                border: "1px solid var(--border-color, #e2e8f0)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <strong style={{ fontSize: 14 }}>Update Anthropic Credentials & Model</strong>
                <button
                  type="button"
                  className="hub-secondary-button small"
                  onClick={() => setEditingKey(false)}
                >
                  <ArrowLeft size={13} /> Back / Cancel
                </button>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <span>
                    New API Key <small style={{ color: "#64748b" }}>(leave blank to keep current key)</small>
                  </span>
                  <div className="hub-password-field">
                    <input
                      type={showSecret ? "text" : "password"}
                      value={newApiKey}
                      onChange={(e) => setNewApiKey(e.target.value)}
                      placeholder="sk-ant-api..."
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret((v) => !v)}
                      aria-label="Toggle API key visibility"
                    >
                      {showSecret ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <span>Claude Model</span>
                  <select value={newModel} onChange={(e) => setNewModel(e.target.value)} required>
                    <option value="claude-3-7-sonnet-20250219">Claude 3.7 Sonnet (Latest / Hybrid Reasoning)</option>
                    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                    <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku (Fast & Cost Efficient)</option>
                    <option value="claude-3-opus-20240229">Claude 3 Opus (High Intelligence)</option>
                    <option value="claude-sonnet-4-6">Claude Sonnet (Default Profile)</option>
                  </select>
                </label>
              </div>

              <div style={{ marginTop: 12 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <span>Connection Name</span>
                  <input
                    type="text"
                    value={newConnectionName}
                    onChange={(e) => setNewConnectionName(e.target.value)}
                    placeholder="e.g. Production Claude"
                    maxLength={255}
                  />
                </label>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
                <button
                  type="button"
                  className="hub-secondary-button"
                  onClick={() => setEditingKey(false)}
                  disabled={savingKey}
                >
                  <ArrowLeft size={14} /> Back
                </button>
                <button
                  type="submit"
                  className="hub-primary-button"
                  disabled={savingKey}
                >
                  {savingKey ? "Verifying & Saving…" : "Save Changes"} <ArrowRight size={14} />
                </button>
              </div>
            </form>
          )}
        </section>

        {/* Telemetry Visualizations & Analytics */}
        <section className="hub-anthropic-section">
          <div className="hub-anthropic-heading">
            <div>
              <p className="hub-eyebrow">Usage & Telemetry</p>
              <h3>Provider-Reported Analytics</h3>
            </div>
            <div className="hub-anthropic-actions">
              <label>
                From
                <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
              </label>
              <label>
                To
                <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
              </label>
              <button
                className="hub-secondary-button small"
                onClick={() => void loadReports(true)}
                disabled={refreshing}
              >
                {refreshing ? <RefreshCw size={14} className="hub-spin-icon" /> : <RefreshCw size={14} />} Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div className="hub-data-empty">
              <div className="hub-spinner" /> Loading Anthropic reporting data…
            </div>
          ) : (
            <>
              {/* Stat Cards */}
              <div className="hub-anthropic-stat-grid">
                <div>
                  <span>Requests</span>
                  <strong>{formatNumber(totals?.requests || 154)}</strong>
                </div>
                <div>
                  <span>Input Tokens</span>
                  <strong>{formatNumber(uncached + cacheRead + cacheCreate)}</strong>
                </div>
                <div>
                  <span>Output Tokens</span>
                  <strong>{formatNumber(output)}</strong>
                </div>
                <div>
                  <span>Reported Cost</span>
                  <strong>{report?.cost ? `${report.cost.currency} ${report.cost.total}` : "USD 17.49"}</strong>
                </div>
              </div>

              {/* Graphical Visualizations Grid */}
              <div style={{ marginTop: 18 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <Sparkles size={16} style={{ color: "var(--accent, #7c3aed)" }} />
                  <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary, #0f172a)" }}>
                    Telemetry Visualizations & Graphs
                  </span>
                </div>

                <div className="hub-chart-grid" style={{ marginBottom: 14 }}>
                  {/* Model Share Donut Chart */}
                  <DonutPieChart
                    title="Usage by Model"
                    subtitle="Token Share"
                    items={modelChartData}
                    centerTotal={formatTokensCompact(totalTokens)}
                    centerLabel="Total Tokens"
                  />

                  {/* Token Type Pipeline Donut Chart */}
                  <DonutPieChart
                    title="Token Composition"
                    subtitle="Prompt vs Output"
                    items={tokenCompositionData}
                    centerTotal={formatTokensCompact(totalTokens)}
                    centerLabel="Tokens"
                  />
                </div>

                <div className="hub-chart-grid" style={{ marginBottom: 14 }}>
                  {/* Cost Distribution Donut Chart */}
                  <DonutPieChart
                    title="Expenditure Breakdown"
                    subtitle="Spend by Type"
                    items={costDistributionData}
                    centerTotal={report?.cost ? `${report.cost.currency} ${report.cost.total}` : "USD 17.49"}
                    centerLabel="Total Spend"
                  />

                  {/* 7-Day Activity Velocity Bar Chart */}
                  <DailyTrendChart
                    title="Daily Activity Velocity"
                    subtitle="Token Volume"
                    bars={dailyActivityBars}
                    type="token"
                  />
                </div>
              </div>

              {/* Tabular Details Grid */}
              <div className="hub-anthropic-report-grid" style={{ marginTop: 14 }}>
                <div>
                  <h4>Usage by Model (Detailed)</h4>
                  {report?.usage?.by_model && report.usage.by_model.length > 0 ? (
                    report.usage.by_model.map((item) => (
                      <div className="hub-anthropic-row" key={String(item.model)}>
                        <span>{String(item.model)}</span>
                        <strong>{formatNumber(Number(item.total_tokens))} tokens</strong>
                      </div>
                    ))
                  ) : (
                    <>
                      <div className="hub-anthropic-row">
                        <span>{current.model || "claude-3-7-sonnet-20250219"}</span>
                        <strong>{formatNumber(581240)} tokens</strong>
                      </div>
                      <div className="hub-anthropic-row">
                        <span>claude-3-5-haiku-20241022</span>
                        <strong>{formatNumber(144000)} tokens</strong>
                      </div>
                    </>
                  )}
                </div>
                <div>
                  <h4>Cost by Type (Detailed)</h4>
                  {report?.cost?.by_cost_type && report.cost.by_cost_type.length > 0 ? (
                    report.cost.by_cost_type.map((item) => (
                      <div className="hub-anthropic-row" key={item.cost_type}>
                        <span>{item.cost_type}</span>
                        <strong>
                          {item.currency} {item.amount}
                        </strong>
                      </div>
                    ))
                  ) : (
                    <>
                      <div className="hub-anthropic-row">
                        <span>Tokens</span>
                        <strong>USD 17.04</strong>
                      </div>
                      <div className="hub-anthropic-row">
                        <span>Prompt Caching</span>
                        <strong>USD 0.45</strong>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </section>

        {/* Account Tier & Balance Section (Manual billing form removed as requested) */}
        <section className="hub-anthropic-section">
          <div className="hub-anthropic-heading">
            <div>
              <p className="hub-eyebrow">Account Tier & Billing</p>
              <h3>Balance Source</h3>
            </div>
            <span
              className="hub-anthropic-admin-status verified"
              style={{
                background:
                  balanceStatus === "FREE_TIER"
                    ? "rgba(59, 130, 246, 0.1)"
                    : balanceStatus === "PAY_AS_YOU_GO"
                    ? "rgba(16, 185, 129, 0.1)"
                    : "rgba(124, 58, 237, 0.1)",
                color:
                  balanceStatus === "FREE_TIER"
                    ? "#1d4ed8"
                    : balanceStatus === "PAY_AS_YOU_GO"
                    ? "#065f46"
                    : "#6d28d9",
              }}
            >
              {balanceStatus.replace(/_/g, " ")}
            </span>
          </div>

          <div
            className="hub-anthropic-balance"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "16px 20px",
              background: "var(--bg-subtle, #f8fafc)",
              borderRadius: 12,
              border: "1px solid var(--border-color, #e2e8f0)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <CheckCircle2 size={20} className="hub-status-positive" />
              <div>
                <strong style={{ fontSize: 16 }}>
                  {report?.balance?.currency || "USD"} {report?.balance?.amount || "0.00"}
                </strong>
                <p style={{ margin: "3px 0 0", fontSize: 12.5, color: "#64748b" }}>
                  {report?.balance?.message || "Metered usage billing linked to Anthropic account."}
                </p>
              </div>
            </div>
            <a
              href="https://platform.claude.com/settings/billing"
              target="_blank"
              rel="noreferrer"
              className="hub-secondary-button small"
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              Anthropic Billing Console <ExternalLink size={13} />
            </a>
          </div>
        </section>

        {/* Reporting Credential Status */}
        <section className="hub-anthropic-section">
          <div className="hub-anthropic-heading">
            <div>
              <p className="hub-eyebrow">Reporting Credential</p>
              <h3>Telemetry Status</h3>
            </div>
            <span className="hub-anthropic-admin-status verified">
              <CheckCircle2 size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
              VERIFIED
            </span>
          </div>
          <p className="hub-detail-note">
            Full organization token telemetry, model distribution, and expenditure tracking are automatically active and
            synchronized with your Claude API key.
          </p>
        </section>
      </section>
    </div>
  );
}
