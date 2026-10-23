import { BarChart3, CalendarDays, CheckCircle2, RefreshCw, X } from "lucide-react";
import type { AWSAccountPlanResponse, AWSConnection, AWSCostResponse } from "@/lib/api";
import { creditExpiryDisplay } from "@/lib/creditBalance";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

interface IntegrationDetailsProps {
  provider: ProviderDefinition;
  connection: AWSConnection;
  cost?: AWSCostResponse;
  plan?: AWSAccountPlanResponse;
  planError?: string;
  busy: boolean;
  onClose: () => void;
  onLoadCosts: () => void;
  onRefreshPlan: () => void;
}

export function IntegrationDetails({ provider, connection, cost, plan, planError, busy, onClose, onLoadCosts, onRefreshPlan }: IntegrationDetailsProps) {
  const expiry = creditExpiryDisplay(plan?.expiration_date);
  const credits = plan?.credits_remaining != null ? new Intl.NumberFormat("en-US", { style: "currency", currency: plan.currency || "USD" }).format(plan.credits_remaining) : null;
  return (
    <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="hub-dialog hub-details-dialog" role="dialog" aria-modal="true" aria-labelledby="details-dialog-title">
        <div className="hub-dialog-header">
          <div className="hub-details-title"><div className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} size={20} /></div><div><p className="hub-eyebrow">Connected integration</p><h2 id="details-dialog-title">{provider.name}</h2></div></div>
          <button className="hub-icon-action" onClick={onClose} aria-label="Close details"><X size={18} /></button>
        </div>
        <div className="hub-detail-status"><CheckCircle2 size={17} /><span>Connection active</span><small>Last updated {new Date(connection.updated_at).toLocaleString()}</small></div>
        <div className="hub-detail-grid">
          <div><span>Account</span><strong>{connection.account_id || "Not supplied"}</strong></div>
          <div><span>Region</span><strong>{connection.region}</strong></div>
          <div><span>Plan status</span><strong>{plan?.plan_status || "Unavailable"}</strong><small>{planError || plan?.plan_type || "AWS Free Tier data"}</small></div>
          <div className={`hub-credit-detail ${expiry.state === "expired" ? "is-expired" : expiry.state === "today" ? "is-warning" : ""}`}><span>AWS promotional credits</span><strong>{credits || (planError ? "Unable to retrieve credit information" : "Unavailable")}</strong><small>{plan ? <>{expiry.label} · Expires {plan.expiration_date || "unavailable"}</> : (planError || "Loading AWS credit information…")}</small>{plan && <small>Last synced {new Date(plan.retrieved_at).toLocaleString()}</small>}<button className="hub-text-button" disabled={busy} onClick={onRefreshPlan}><RefreshCw size={13} /> Refresh</button></div>
        </div>
        <div className="hub-detail-cost">
          <div><div className="hub-detail-cost-icon"><BarChart3 size={18} /></div><div><span>Month-to-date spend</span><strong>{cost ? `${cost.currency} ${Number(cost.amount || 0).toFixed(2)}` : "Not loaded"}</strong></div></div>
          {cost ? <small><CalendarDays size={13} /> {cost.period_start} – {cost.period_end_exclusive}</small> : <button className="hub-secondary-button" disabled={busy} onClick={onLoadCosts}>{busy ? "Loading…" : "Load Cost Explorer data"}</button>}
        </div>
        <p className="hub-detail-note">AWS credits come from Free Tier <code>GetAccountPlanState</code>. The API does not provide an original promotional-credit amount for every account, so UniSora leaves that value unavailable rather than estimating it.</p>
      </section>
    </div>
  );
}
