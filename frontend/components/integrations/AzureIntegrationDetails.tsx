"use client";
import { useEffect, useState } from "react";
import { CalendarDays, RefreshCw, X } from "lucide-react";
import { discoverAzureSubscriptions, getAzureCost, selectAzureSubscriptions, type AzureConnection } from "@/lib/api";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

type AzureSubscription = { id: string; display_name: string; state?: string; tenant_id?: string; selected?: boolean };
type AzureCostColumn = { name?: string };
type AzureCostResponse = { properties?: { columns?: AzureCostColumn[]; rows?: unknown[][] } };

function costRows(value: unknown) {
  const payload = value as { cost?: AzureCostResponse } | null;
  const columns = payload?.cost?.properties?.columns || [];
  const rows = payload?.cost?.properties?.rows || [];
  const costIndex = Math.max(0, columns.findIndex((column) => /cost|amount|charge|pretax/i.test(column.name || "")));
  const dateIndex = columns.findIndex((column) => /date|day|period/i.test(column.name || ""));
  const currencyIndex = columns.findIndex((column) => /currency/i.test(column.name || ""));
  return rows.map((row) => ({
    date: dateIndex >= 0 ? String(row[dateIndex] ?? "") : "",
    amount: Number(row[costIndex] ?? 0),
    currency: currencyIndex >= 0 ? String(row[currencyIndex] || "") : "",
  })).filter((row) => Number.isFinite(row.amount));
}

export function AzureIntegrationDetails({ provider, connection, onClose }: { provider: ProviderDefinition; connection: AzureConnection; onClose: () => void }) {
  const [subscriptions, setSubscriptions] = useState<AzureSubscription[]>([]); const [busy, setBusy] = useState(false); const [message, setMessage] = useState(""); const [cost, setCost] = useState<unknown>(null); const [costSubscription, setCostSubscription] = useState("");
  async function discover() { setBusy(true); setMessage(""); try { const result = await discoverAzureSubscriptions(); setSubscriptions(result.subscriptions); } catch (e) { setMessage(e instanceof Error ? e.message : "Azure subscription discovery failed."); } finally { setBusy(false); } }
  async function save() { setBusy(true); try { await selectAzureSubscriptions(subscriptions.filter((item) => item.selected).map((item) => item.id)); setMessage("Azure subscription selection saved."); } catch (e) { setMessage(e instanceof Error ? e.message : "Could not save subscription selection."); } finally { setBusy(false); } }
  async function loadCost(subscriptionId: string) { setBusy(true); setMessage(""); try { const end = new Date(); const start = new Date(); start.setDate(1); setCostSubscription(subscriptionId); setCost(await getAzureCost(subscriptionId, start.toISOString().slice(0, 10), end.toISOString().slice(0, 10))); } catch (e) { setMessage(e instanceof Error ? e.message : "Azure cost data is unavailable. Confirm Cost Management Reader access."); } finally { setBusy(false); } }
  useEffect(() => { void discover(); }, []);
  const rows = costRows(cost); const total = rows.reduce((sum, row) => sum + row.amount, 0); const currency = rows.find((row) => row.currency)?.currency || "provider currency";
  return <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="hub-dialog hub-details-dialog" role="dialog" aria-modal="true" aria-labelledby="azure-details-title">
    <div className="hub-dialog-header"><div className="hub-details-title"><div className="hub-provider-icon hub-provider-azure"><ProviderIcon icon="azure" size={20} /></div><div><p className="hub-eyebrow">Connected integration</p><h2 id="azure-details-title">{provider.name}</h2></div></div><button className="hub-icon-action" onClick={onClose} aria-label="Close Azure details"><X size={18} /></button></div>
    <div className="hub-detail-status"><span>Connection active</span><small>Last refresh {connection.last_successful_refresh ? new Date(connection.last_successful_refresh).toLocaleString() : "Not yet refreshed"}</small></div>
    {message && <p className="hub-form-error" role="alert">{message}</p>}<div className="hub-dialog-actions" style={{ justifyContent: "flex-start", marginTop: 0 }}><button className="hub-secondary-button" onClick={() => void discover()} disabled={busy}><RefreshCw size={14} /> Refresh subscriptions</button><button className="hub-primary-button small" onClick={() => void save()} disabled={busy}>Save selection</button></div>
    <div className="hub-azure-subscriptions">{subscriptions.length ? subscriptions.map((item) => <label key={item.id}><input type="checkbox" checked={Boolean(item.selected)} onChange={(event) => setSubscriptions((all) => all.map((entry) => entry.id === item.id ? { ...entry, selected: event.target.checked } : entry))} /><span><strong>{item.display_name}</strong><small>{item.id} · {item.state || "unknown state"}</small></span><button type="button" className="hub-text-button" disabled={busy || !item.selected} onClick={() => void loadCost(item.id)}><CalendarDays size={14} /> View PAYG cost</button></label>) : <p className="hub-dialog-intro">No Azure subscriptions have been discovered yet, or the connected account lacks subscription access.</p>}</div>
    {cost !== null && <div className="hub-azure-cost-panel"><div className="hub-usage-summary"><div className="hub-metric"><span>Current-month PAYG cost</span><strong>{total.toFixed(2)}</strong><small>{currency} · Azure Cost Management</small></div><div className="hub-metric"><span>Daily cost records</span><strong>{rows.length}</strong><small>{costSubscription || "Selected subscription"}</small></div></div>{rows.length ? <div className="hub-azure-cost-table"><div className="hub-azure-cost-table-heading"><strong>Daily breakdown</strong><span>Actual cost reported by Azure</span></div>{rows.slice().reverse().map((row, index) => <div key={`${row.date}-${index}`}><span>{row.date || "Reported period"}</span><strong>{row.amount.toFixed(2)} {row.currency || currency}</strong></div>)}</div> : <p className="hub-dialog-intro">Azure returned no cost rows for the current month. If this is a new PAYG subscription, allow 24–48 hours for usage data to appear.</p>}<p className="hub-detail-note">Costs are fetched live from Azure Cost Management. UniSora does not estimate charges or convert currencies.</p></div>}
  </section></div>;
}
