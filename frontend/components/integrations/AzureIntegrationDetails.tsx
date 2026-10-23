"use client";
import { useEffect, useState } from "react";
import { CalendarDays, RefreshCw, X } from "lucide-react";
import { discoverAzureSubscriptions, getAzureCost, selectAzureSubscriptions, type AzureConnection } from "@/lib/api";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

type AzureSubscription = { id: string; display_name: string; state?: string; tenant_id?: string; selected?: boolean };
export function AzureIntegrationDetails({ provider, connection, onClose }: { provider: ProviderDefinition; connection: AzureConnection; onClose: () => void }) {
  const [subscriptions, setSubscriptions] = useState<AzureSubscription[]>([]); const [busy, setBusy] = useState(false); const [message, setMessage] = useState(""); const [cost, setCost] = useState<unknown>(null);
  async function discover() { setBusy(true); setMessage(""); try { const result = await discoverAzureSubscriptions(); setSubscriptions(result.subscriptions); } catch (e) { setMessage(e instanceof Error ? e.message : "Azure subscription discovery failed."); } finally { setBusy(false); } }
  async function save() { setBusy(true); try { await selectAzureSubscriptions(subscriptions.filter((item) => item.selected).map((item) => item.id)); setMessage("Azure subscription selection saved."); } catch (e) { setMessage(e instanceof Error ? e.message : "Could not save subscription selection."); } finally { setBusy(false); } }
  async function loadCost(subscriptionId: string) { setBusy(true); try { const end = new Date(); const start = new Date(); start.setDate(1); setCost(await getAzureCost(subscriptionId, start.toISOString().slice(0, 10), end.toISOString().slice(0, 10))); } catch (e) { setMessage(e instanceof Error ? e.message : "Azure cost data is unavailable."); } finally { setBusy(false); } }
  useEffect(() => { void discover(); }, []);
  return <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="hub-dialog hub-details-dialog" role="dialog" aria-modal="true" aria-labelledby="azure-details-title">
    <div className="hub-dialog-header"><div className="hub-details-title"><div className="hub-provider-icon hub-provider-azure"><ProviderIcon icon="azure" size={20} /></div><div><p className="hub-eyebrow">Connected integration</p><h2 id="azure-details-title">{provider.name}</h2></div></div><button className="hub-icon-action" onClick={onClose} aria-label="Close Azure details"><X size={18} /></button></div>
    <div className="hub-detail-status"><span>Connection active</span><small>Last refresh {connection.last_successful_refresh ? new Date(connection.last_successful_refresh).toLocaleString() : "Not yet refreshed"}</small></div>
    {message && <p className="hub-form-error" role="alert">{message}</p>}<div className="hub-dialog-actions" style={{ justifyContent: "flex-start", marginTop: 0 }}><button className="hub-secondary-button" onClick={() => void discover()} disabled={busy}><RefreshCw size={14} /> Refresh subscriptions</button><button className="hub-primary-button small" onClick={() => void save()} disabled={busy}>Save selection</button></div>
    <div className="hub-azure-subscriptions">{subscriptions.length ? subscriptions.map((item) => <label key={item.id}><input type="checkbox" checked={Boolean(item.selected)} onChange={(event) => setSubscriptions((all) => all.map((entry) => entry.id === item.id ? { ...entry, selected: event.target.checked } : entry))} /><span><strong>{item.display_name}</strong><small>{item.id} · {item.state || "unknown state"}</small></span><button type="button" className="hub-text-button" disabled={busy || !item.selected} onClick={() => void loadCost(item.id)}><CalendarDays size={14} /> Cost</button></label>) : <p className="hub-dialog-intro">No Azure subscriptions have been discovered yet, or the connected account lacks subscription access.</p>}</div>
    {cost !== null && <pre className="hub-azure-cost">{JSON.stringify(cost, null, 2)}</pre>}
  </section></div>;
}
