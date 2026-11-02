"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, CalendarDays, CheckCircle2, RefreshCw, X } from "lucide-react";
import { getOpenAISummary, type OpenAISummaryResponse } from "@/lib/api";
import type { OpenAIConnection } from "@/lib/api";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

type RangePreset = "7d" | "30d" | "current-month" | "previous-month" | "custom";

interface OpenAIUsageDetailsProps {
  provider: ProviderDefinition;
  connection: OpenAIConnection;
  onClose: () => void;
}

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function rangeFor(preset: Exclude<RangePreset, "custom">) {
  const today = new Date();
  const end = new Date(today);
  end.setHours(0, 0, 0, 0);
  if (preset === "current-month") return { start: isoDate(new Date(today.getFullYear(), today.getMonth(), 1)), end: isoDate(end) };
  if (preset === "previous-month") return { start: isoDate(new Date(today.getFullYear(), today.getMonth() - 1, 1)), end: isoDate(new Date(today.getFullYear(), today.getMonth(), 0)) };
  const days = preset === "7d" ? 6 : 29;
  const start = new Date(end);
  start.setDate(start.getDate() - days);
  return { start: isoDate(start), end: isoDate(end) };
}

function formatTokens(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatAmount(value: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase(), maximumFractionDigits: 4 }).format(value);
}

export function OpenAIUsageDetails({ provider, connection, onClose }: OpenAIUsageDetailsProps) {
  const [preset, setPreset] = useState<RangePreset>("30d");
  const initialRange = rangeFor("30d");
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [data, setData] = useState<OpenAISummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    if (endDate < startDate) {
      setError("The end date must be on or after the start date.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await getOpenAISummary(startDate, endDate));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "OpenAI usage could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [startDate, endDate]);

  function choosePreset(value: RangePreset) {
    setPreset(value);
    if (value !== "custom") {
      const range = rangeFor(value);
      setStartDate(range.start);
      setEndDate(range.end);
    }
  }

  const maxDailyTokens = useMemo(() => Math.max(...(data?.usage.daily.map((day) => day.total_tokens) || [1]), 1), [data]);
  const maxDailyCost = useMemo(() => Math.max(...(data?.costs?.daily.map((day) => day.amount) || [1]), 1), [data]);

  return (
    <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="hub-dialog hub-details-dialog hub-openai-usage-dialog" role="dialog" aria-modal="true" aria-labelledby="openai-usage-title">
        <div className="hub-dialog-header">
          <div className="hub-details-title"><div className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} size={20} /></div><div><p className="hub-eyebrow">OpenAI API usage</p><h2 id="openai-usage-title">{provider.name}</h2></div></div>
          <button className="hub-icon-action" onClick={onClose} aria-label="Close OpenAI usage"><X size={18} /></button>
        </div>
        <div className="hub-detail-status"><CheckCircle2 size={17} /><span>Connection active</span><small>Last verified {connection.last_verified_at ? new Date(connection.last_verified_at).toLocaleString() : "not available"}</small></div>
        <div className="hub-usage-controls"><select value={preset} onChange={(event) => choosePreset(event.target.value as RangePreset)} aria-label="Usage time range"><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option><option value="current-month">Current month</option><option value="previous-month">Previous month</option><option value="custom">Custom range</option></select>{preset === "custom" && <><label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label></>}<button className="hub-secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14} />{loading ? "Refreshing…" : "Refresh usage"}</button></div>
        {error ? <div className="hub-form-error" role="alert">{error}</div> : loading ? <div className="hub-verifying"><div className="hub-spinner" /><p>Loading actual OpenAI organization usage and costs…</p></div> : data ? <>
          <div className="hub-usage-summary"><div className="hub-metric"><span>Reported API cost</span><strong>{data.costs ? formatAmount(data.costs.total, data.costs.currency) : "Unavailable"}</strong><small>{data.costs ? "OpenAI reported cost" : data.costs_error || "Requires organization cost access"}</small></div><div className="hub-metric"><span>Total tokens</span><strong>{formatTokens(data.usage.total_tokens)}</strong><small>Input + output, without double-counting</small></div><div className="hub-metric"><span>Input tokens</span><strong>{formatTokens(data.usage.total_input_tokens)}</strong><small>Reported input tokens</small></div><div className="hub-metric"><span>Output tokens</span><strong>{formatTokens(data.usage.total_output_tokens)}</strong><small>Reported output tokens</small></div>{data.usage.requests !== null && <div className="hub-metric"><span>API requests</span><strong>{data.usage.requests.toLocaleString()}</strong><small>Reported model requests</small></div>}</div>
          <div className="hub-chart-grid"><section className="hub-chart-card"><div className="hub-chart-heading"><div><p className="hub-eyebrow">Daily trend</p><h3>Token usage</h3></div><BarChart3 size={18} /></div>{data.usage.daily.length ? <div className="hub-mini-bars">{data.usage.daily.map((day) => <div className="hub-mini-bar-column" key={day.start_time} title={`${formatTokens(day.total_tokens)} tokens`}><div className="hub-mini-bar token" style={{ height: `${Math.max((day.total_tokens / maxDailyTokens) * 100, day.total_tokens ? 4 : 0)}%` }} /><small>{new Date(day.start_time * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small></div>)}</div> : <p className="hub-chart-empty">No token usage was reported for this period.</p>}</section><section className="hub-chart-card"><div className="hub-chart-heading"><div><p className="hub-eyebrow">Daily trend</p><h3>API cost</h3></div><BarChart3 size={18} /></div>{data.costs?.daily.length ? <div className="hub-mini-bars">{data.costs.daily.map((day) => <div className="hub-mini-bar-column" key={day.start_time} title={formatAmount(day.amount, day.currency)}><div className="hub-mini-bar cost" style={{ height: `${Math.max((day.amount / maxDailyCost) * 100, day.amount ? 4 : 0)}%` }} /><small>{new Date(day.start_time * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small></div>)}</div> : <p className="hub-chart-empty">{data.costs_error || "No cost data is available for this period."}</p>}</section></div>
          <div className="hub-usage-breakdowns"><section className="hub-chart-card"><div className="hub-chart-heading"><div><p className="hub-eyebrow">Model breakdown</p><h3>Usage by model</h3></div></div>{data.usage.by_model.length ? <div className="hub-breakdown-list">{data.usage.by_model.map((model) => <div key={model.model}><span>{model.model}</span><strong>{formatTokens(model.total_tokens)} tokens</strong></div>)}</div> : <p className="hub-chart-empty">No model usage was reported.</p>}</section>{data.costs && <section className="hub-chart-card"><div className="hub-chart-heading"><div><p className="hub-eyebrow">Cost breakdown</p><h3>Cost by project</h3></div></div>{data.costs.by_project.length ? <div className="hub-breakdown-list">{data.costs.by_project.map((project) => <div key={project.project_id}><span>{project.project_id}</span><strong>{formatAmount(project.amount, project.currency)}</strong></div>)}</div> : <p className="hub-chart-empty">No project cost data was reported.</p>}</section>}</div>
          <p className="hub-detail-note"><CalendarDays size={13} /> API usage and reported API costs are separate from ChatGPT Plus, Pro, or other ChatGPT subscriptions. Last synchronized {new Date(data.usage.synced_at).toLocaleString()}.</p>
        </> : null}
      </section>
    </div>
  );
}
