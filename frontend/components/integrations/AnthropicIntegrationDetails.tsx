"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CheckCircle2, ExternalLink, KeyRound, RefreshCw, ShieldAlert, Trash2, X } from "lucide-react";
import { configureAnthropicAdminCredential, getAnthropicReports, removeAnthropicAdminCredential, removeAnthropicManualBalance, saveAnthropicManualBalance, type AnthropicConnection, type AnthropicReportResponse } from "@/lib/api";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

function monthRange() {
  const now = new Date();
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

function formatNumber(value: number | undefined) { return value == null ? "—" : new Intl.NumberFormat().format(value); }
function formatDate(value: string | null | undefined) { return value ? new Date(value).toLocaleString() : "Not available"; }

export function AnthropicIntegrationDetails({ provider, connection, onClose, onConnectionChange }: { provider: ProviderDefinition; connection: AnthropicConnection; onClose: () => void; onConnectionChange?: (connection: AnthropicConnection) => void }) {
  const initialRange = useMemo(monthRange, []);
  const [current, setCurrent] = useState(connection);
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [report, setReport] = useState<AnthropicReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [savingAdmin, setSavingAdmin] = useState(false);
  const [manualAmount, setManualAmount] = useState(current.manual_balance_amount || "");
  const [manualCurrency, setManualCurrency] = useState(current.manual_balance_currency || "USD");
  const [savingBalance, setSavingBalance] = useState(false);

  async function loadReports(forceRefresh = false) {
    setError("");
    if (forceRefresh) setRefreshing(true); else setLoading(true);
    try { setReport(await getAnthropicReports(current.id, startDate, endDate, forceRefresh)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not load Anthropic reporting data."); }
    finally { setLoading(false); setRefreshing(false); }
  }

  useEffect(() => { void loadReports(); }, [current.id, startDate, endDate]);

  async function saveAdmin(event: FormEvent) {
    event.preventDefault();
    if (!adminKey.trim()) return;
    setSavingAdmin(true); setError("");
    try {
      const result = await configureAnthropicAdminCredential(current.id, adminKey.trim());
      const next = { ...current, admin_access_status: result.admin_access_status as AnthropicConnection["admin_access_status"], admin_verified_at: result.admin_verified_at };
      setCurrent(next); onConnectionChange?.(next);
      setAdminKey("");
      await loadReports(true);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not verify the reporting credential."); }
    finally { setSavingAdmin(false); }
  }

  async function removeAdmin() {
    if (!window.confirm("Remove the Anthropic reporting credential? The standard Messages API key will remain active.")) return;
    try { await removeAnthropicAdminCredential(current.id); const next = { ...current, admin_access_status: "NOT_CONFIGURED" as const, admin_verified_at: null }; setCurrent(next); onConnectionChange?.(next); setReport(null); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not remove the reporting credential."); }
  }

  async function saveBalance(event: FormEvent) {
    event.preventDefault(); setSavingBalance(true); setError("");
    try {
      const result = await saveAnthropicManualBalance(current.id, manualAmount, manualCurrency);
      setReport((value) => value ? { ...value, balance: result.balance } : value);
      const next = { ...current, manual_balance_amount: result.balance.amount, manual_balance_currency: result.balance.currency, manual_balance_entered_at: result.balance.entered_at }; setCurrent(next); onConnectionChange?.(next);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not save the manual balance."); }
    finally { setSavingBalance(false); }
  }

  async function clearBalance() {
    try { await removeAnthropicManualBalance(current.id); setManualAmount(""); const next = { ...current, manual_balance_amount: null, manual_balance_currency: null, manual_balance_entered_at: null }; setCurrent(next); onConnectionChange?.(next); setReport((value) => value ? { ...value, balance: { ...value.balance, status: "UNSUPPORTED", amount: null, currency: null, entered_at: null, source: "provider_unavailable" } } : value); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not remove the manual balance."); }
  }

  const totals = report?.usage?.totals;
  return <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="hub-dialog hub-details-dialog hub-anthropic-dialog" role="dialog" aria-modal="true" aria-labelledby="anthropic-details-title">
      <div className="hub-dialog-header"><div className="hub-details-title"><div className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} size={20} /></div><div><p className="hub-eyebrow">Connected integration</p><h2 id="anthropic-details-title">{provider.name}</h2></div></div><button className="hub-icon-action" onClick={onClose} aria-label="Close Anthropic details"><X size={18} /></button></div>
      <div className="hub-detail-status"><CheckCircle2 size={17} /><span>{current.status === "ACTIVE" ? "Messages API connected" : current.status}</span><small>Verified {formatDate(current.last_verified_at)}</small></div>
      {error && <div className="hub-notice" role="alert">{error}</div>}
      <section className="hub-anthropic-section"><div className="hub-anthropic-heading"><div><p className="hub-eyebrow">Connection</p><h3>Claude access</h3></div></div><div className="hub-detail-grid"><div><span>Connection name</span><strong>{current.connection_name || "Default connection"}</strong></div><div><span>Configured model</span><strong>{current.model || "Not reported"}</strong></div><div><span>Messages API</span><strong className="hub-status-positive">Available</strong></div><div><span>Last successful verification</span><strong>{formatDate(current.last_verified_at)}</strong></div></div></section>
      <section className="hub-anthropic-section"><div className="hub-anthropic-heading"><div><p className="hub-eyebrow">Usage & costs</p><h3>Provider-reported analytics</h3></div><div className="hub-anthropic-actions"><label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label><button className="hub-secondary-button small" onClick={() => void loadReports(true)} disabled={refreshing}>{refreshing ? <RefreshCw size={14} className="hub-spin-icon" /> : <RefreshCw size={14} />} Refresh</button></div></div>
        {loading ? <div className="hub-data-empty"><div className="hub-spinner" /> Loading Anthropic reporting data…</div> : report?.admin_access_status !== "VERIFIED" ? <div className="hub-data-empty"><ShieldAlert size={18} /><div><strong>Administrative reporting access is not configured.</strong><span>Add an Admin API key below to retrieve organization usage and costs.</span></div></div> : <><div className="hub-anthropic-stat-grid"><div><span>Requests</span><strong>{formatNumber(totals?.requests)}</strong></div><div><span>Input tokens</span><strong>{formatNumber((totals?.uncached_input_tokens || 0) + (totals?.cache_read_input_tokens || 0) + (totals?.cache_creation_input_tokens || 0))}</strong></div><div><span>Output tokens</span><strong>{formatNumber(totals?.output_tokens)}</strong></div><div><span>Reported cost</span><strong>{report.cost ? `${report.cost.currency} ${report.cost.total}` : "—"}</strong></div></div><p className="hub-detail-note">Includes uncached input, cache read, cache creation, output tokens, and model-grouped rows. Analytics data refreshed {formatDate(report.data_refreshed_at)}. Anthropic may revise recent values for up to 7 days.</p><div className="hub-anthropic-report-grid"><div><h4>Usage by model</h4>{report.usage?.by_model.length ? report.usage.by_model.map((item) => <div className="hub-anthropic-row" key={String(item.model)}><span>{String(item.model)}</span><strong>{formatNumber(Number(item.total_tokens))} tokens</strong></div>) : <p className="hub-settings-muted">No usage during this period.</p>}</div><div><h4>Cost by type</h4>{report.cost?.by_cost_type.length ? report.cost.by_cost_type.map((item) => <div className="hub-anthropic-row" key={item.cost_type}><span>{item.cost_type}</span><strong>{item.currency} {item.amount}</strong></div>) : <p className="hub-settings-muted">No reported cost during this period.</p>}</div></div></>}
      </section>
      <section className="hub-anthropic-section"><div className="hub-anthropic-heading"><div><p className="hub-eyebrow">Remaining credits</p><h3>Balance source</h3></div></div>{(report?.balance.status === "MANUAL" || current.manual_balance_amount) ? <div className="hub-anthropic-balance manual"><strong>{current.manual_balance_currency} {current.manual_balance_amount}</strong><span>Manual entry · last confirmed {formatDate(current.manual_balance_entered_at)}</span><button className="hub-text-button" onClick={() => void clearBalance()}><Trash2 size={13} /> Remove manual balance</button></div> : <div className="hub-anthropic-balance"><ShieldAlert size={18} /><div><strong>Live remaining-credit balance unavailable</strong><span>Anthropic’s supported analytics APIs report usage and cost, but do not expose the organization’s prepaid-credit balance to this integration.</span><a href="https://platform.claude.com/settings/billing" target="_blank" rel="noreferrer">Open Anthropic Console billing <ExternalLink size={13} /></a></div></div>}<form className="hub-anthropic-manual-form" onSubmit={saveBalance}><input aria-label="Manual balance amount" type="number" min="0" step="0.000001" placeholder="Manual balance" value={manualAmount} onChange={(event) => setManualAmount(event.target.value)} /><input aria-label="Balance currency" maxLength={3} value={manualCurrency} onChange={(event) => setManualCurrency(event.target.value.toUpperCase())} /><button className="hub-secondary-button small" disabled={savingBalance}>{savingBalance ? "Saving…" : "Save manual balance"}</button></form></section>
      <section className="hub-anthropic-section"><div className="hub-anthropic-heading"><div><p className="hub-eyebrow">Administrative access</p><h3>{current.admin_access_status === "VERIFIED" ? "Reporting credential verified" : "Configure usage and cost reporting"}</h3></div><span className={`hub-anthropic-admin-status ${current.admin_access_status.toLowerCase()}`}>{current.admin_access_status.replaceAll("_", " ")}</span></div><p className="hub-detail-note">A standard <code>sk-ant-api…</code> Messages key cannot be assumed to have organization reporting access. Use a separate Admin API key or Enterprise Analytics key; it is encrypted and never returned to the browser.</p>{current.admin_access_status === "VERIFIED" ? <button className="hub-secondary-button small" onClick={() => void removeAdmin()}><Trash2 size={14} /> Remove reporting credential</button> : <form className="hub-anthropic-admin-form" onSubmit={saveAdmin}><KeyRound size={16} /><input type="password" autoComplete="new-password" placeholder="sk-ant-admin… or Analytics API key" value={adminKey} onChange={(event) => setAdminKey(event.target.value)} /><button className="hub-primary-button small" disabled={savingAdmin || !adminKey.trim()}>{savingAdmin ? "Verifying…" : "Verify and save"}</button></form>}</section>
    </section>
  </div>;
}
