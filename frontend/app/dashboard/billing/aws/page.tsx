"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, CalendarDays, RefreshCw } from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { getAWSAccountPlan, getAWSCosts, listAWSConnections, type AWSAccountPlanResponse, type AWSConnection, type AWSCostResponse } from "@/lib/api";

type BillingRow = { connection: AWSConnection; cost?: AWSCostResponse; plan?: AWSAccountPlanResponse; error?: string };

export default function AWSBillingPage() {
  const [rows, setRows] = useState<BillingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const connections = await listAWSConnections();
      const results = await Promise.all(connections.map(async (connection): Promise<BillingRow> => {
        const [costResult, planResult] = await Promise.allSettled([getAWSCosts(connection.id), getAWSAccountPlan(connection.id)]);
        const messages = [costResult.status === "rejected" ? (costResult.reason instanceof Error ? costResult.reason.message : "Cost data unavailable") : "", planResult.status === "rejected" ? (planResult.reason instanceof Error ? planResult.reason.message : "Credit data unavailable") : ""].filter(Boolean);
        return { connection, cost: costResult.status === "fulfilled" ? costResult.value : undefined, plan: planResult.status === "fulfilled" ? planResult.value : undefined, error: messages.join(" ") || undefined };
      }));
      setRows(results);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Could not load AWS billing data."); }
    finally { setLoading(false); setRefreshing(false); }
  }

  useEffect(() => { void load(); }, []);

  return <DashboardFrame title="AWS billing" description="Actual AWS Cost Explorer spend and Free Tier information for your connected accounts.">
    <div className="hub-billing-back"><Link className="hub-text-button" href="/dashboard/billing"><ArrowLeft size={14} /> All services</Link></div>
    {error && <div className="hub-notice" role="alert">{error}</div>}
    {loading ? <div className="hub-data-empty"><div className="hub-spinner" /> Loading AWS billing data…</div> : rows.length === 0 ? <div className="hub-empty-state"><h3>No AWS account connected</h3><p>Connect AWS first, then return here to view Cost Explorer and Free Tier data.</p><Link className="hub-primary-button small" href="/dashboard/integrations">Connect AWS</Link></div> : <>
      <div className="hub-section-heading"><div><p className="hub-eyebrow">Connected accounts</p><h2>AWS billing details</h2><p>Spend is month-to-date. Credits are shown only when AWS Free Tier returns them.</p></div><button className="hub-secondary-button" onClick={() => { setRefreshing(true); void load(); }} disabled={refreshing}><RefreshCw size={14} /> {refreshing ? "Refreshing…" : "Refresh"}</button></div>
      <div className="hub-billing-account-list">{rows.map(({ connection, cost, plan, error: rowError }) => <article className="hub-billing-account-card" key={connection.id}><div className="hub-billing-account-header"><div><p className="hub-eyebrow">AWS account</p><h3>{connection.account_id || "Account identifier unavailable"}</h3><span>{connection.region} · {connection.status}</span></div><span className="hub-availability connected">Connected</span></div><div className="hub-metrics hub-billing-metrics"><div className="hub-metric"><span>Month-to-date spend</span><strong>{cost ? `${cost.currency} ${Number(cost.amount || 0).toFixed(2)}` : "Not available"}</strong><small>{cost ? `${cost.period_start} – ${cost.period_end_exclusive}` : "Cost Explorer permission or data unavailable"}</small></div><div className="hub-metric"><span>Free Tier credits remaining</span><strong>{plan?.credits_remaining != null ? `${plan.currency} ${plan.credits_remaining}` : "Not available"}</strong><small>{plan ? `${plan.plan_type} · ${plan.days_remaining == null ? "expiry unavailable" : `${plan.days_remaining} days remaining`}` : "AWS Free Tier permission or data unavailable"}</small></div><div className="hub-metric"><span>Plan status</span><strong>{plan?.plan_status || "Not available"}</strong><small>{plan?.expiration_date ? `Expires ${plan.expiration_date}` : "No expiration returned"}</small></div></div>{rowError && <div className="hub-notice" role="status">{rowError}</div>}<p className="hub-detail-note"><CalendarDays size={13} /> Last synchronized {new Date(plan?.retrieved_at || connection.updated_at).toLocaleString()}. AWS does not return allocated or used credit totals for every account, so unavailable values are not estimated.</p></article>)}</div>
    </>}
  </DashboardFrame>;
}
