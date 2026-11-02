"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, CalendarDays, RefreshCw, Server, AlertCircle } from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  getAWSAccountPlan,
  getAWSCosts,
  listAWSConnections,
  type AWSAccountPlanResponse,
  type AWSConnection,
  type AWSCostResponse,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";

type BillingRow = {
  connection: AWSConnection;
  cost?: AWSCostResponse;
  plan?: AWSAccountPlanResponse;
  error?: string;
};

export default function AWSBillingPage() {
  const [rows, setRows] = useState<BillingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const requestInFlight = useRef(false);

  async function load(attempt = 0) {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setError("");
    try {
      const connections = await listAWSConnections();
      const results = await Promise.all(
        connections.map(async (connection): Promise<BillingRow> => {
          const [costResult, planResult] = await Promise.allSettled([
            getAWSCosts(connection.id),
            getAWSAccountPlan(connection.id),
          ]);
          const messages = [
            costResult.status === "rejected"
              ? costResult.reason instanceof Error
                ? costResult.reason.message
                : "Cost data unavailable"
              : "",
            planResult.status === "rejected"
              ? planResult.reason instanceof Error
                ? planResult.reason.message
                : "Credit data unavailable"
              : "",
          ].filter(Boolean);
          return {
            connection,
            cost: costResult.status === "fulfilled" ? costResult.value : undefined,
            plan: planResult.status === "fulfilled" ? planResult.value : undefined,
            error: messages.join(" ") || undefined,
          };
        })
      );
      setRows(results);
    } catch (requestError) {
      const status =
        typeof requestError === "object" && requestError !== null && "status" in requestError
          ? Number(requestError.status)
          : 0;
      const retryable = !status || status === 429 || status >= 500;
      if (retryable && attempt < 2) {
        requestInFlight.current = false;
        window.setTimeout(() => void load(attempt + 1), 900 * (attempt + 1));
        return;
      }
      setError(
        requestError instanceof Error ? requestError.message : "Could not load AWS billing data."
      );
    } finally {
      requestInFlight.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    const interval = window.setInterval(refreshWhenVisible, 60_000);
    return () => {
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
      window.clearInterval(interval);
    };
  }, []);

  return (
    <DashboardFrame
      title="AWS Cloud Billing"
      description="Live AWS Cost Explorer telemetry, Month-to-date expenditure, and Free Tier credit tracking."
      actions={
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => {
            setRefreshing(true);
            void load();
          }}
          disabled={refreshing}
        >
          <RefreshCw size={14} className={refreshing ? "spin-animation" : ""} />
          <span>{refreshing ? "Refreshing…" : "Refresh AWS Data"}</span>
        </button>
      }
    >
      <div className="mb-4">
        <Link href="/dashboard/billing" className="btn btn-secondary btn-sm inline-flex">
          <ArrowLeft size={14} />
          <span>Back to All Billing</span>
        </Link>
      </div>

      {error && (
        <div className="alert-notice alert-danger mb-4" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      {loading ? (
        <div className="hub-data-empty">
          <div className="hub-spinner" />
          <span>Synchronizing AWS Cost Explorer…</span>
        </div>
      ) : rows.length === 0 ? (
        <section className="dashboard-content-card">
          <EmptyState
            icon={<Server size={28} />}
            title="No AWS Account Connected"
            description="Connect your Amazon Web Services account using an IAM Role ARN or Access Key to view live Cost Explorer telemetry."
            action={
              <Link href="/dashboard/integrations" className="btn btn-primary btn-sm">
                <span>Connect AWS Account</span>
              </Link>
            }
          />
        </section>
      ) : (
        <div className="space-y-6">
          {rows.map(({ connection, cost, plan, error: rowError }) => (
            <section key={connection.id} className="dashboard-content-card">
              <div className="card-header-bar">
                <div>
                  <div className="flex-items-center gap-2">
                    <h3 className="card-heading">
                      Account: {connection.account_id || "AWS Account"}
                    </h3>
                    <StatusBadge variant="success" size="sm">
                      Connected
                    </StatusBadge>
                  </div>
                  <p className="card-subheading">
                    Region: {connection.region} · Status: {connection.status}
                  </p>
                </div>
              </div>

              {rowError && (
                <div className="alert-notice alert-warning mb-4" role="status">
                  <AlertCircle size={15} />
                  <span>{rowError}</span>
                </div>
              )}

              {/* AWS Account Metrics */}
              <div className="overview-metrics-grid">
                <MetricCard
                  label="Month-to-Date Spend"
                  value={
                    cost
                      ? `${cost.currency} ${Number(cost.amount || 0).toFixed(2)}`
                      : "Not available"
                  }
                  subtext={
                    cost
                      ? `${cost.period_start} – ${cost.period_end_exclusive}`
                      : "Cost Explorer permissions or data pending"
                  }
                />
                <MetricCard
                  label="Free Tier Credits Remaining"
                  value={
                    plan?.credits_remaining != null
                      ? `${plan.currency} ${plan.credits_remaining}`
                      : "Not available"
                  }
                  subtext={
                    plan
                      ? `${plan.plan_type} · ${plan.days_remaining ?? "—"} days remaining`
                      : "Free Tier data unavailable"
                  }
                />
                <MetricCard
                  label="Plan Status"
                  value={plan?.plan_status || "Active"}
                  subtext={plan?.expiration_date ? `Expires ${plan.expiration_date}` : "Standard billing"}
                />
              </div>

              <div className="historical-note-box mt-4">
                <CalendarDays size={16} className="text-muted flex-none" />
                <span className="text-muted text-xs">
                  Last verified: {new Date(plan?.retrieved_at || connection.updated_at).toLocaleString()}. AWS Free Tier and Cost Explorer values are verified directly against AWS APIs.
                </span>
              </div>
            </section>
          ))}
        </div>
      )}
    </DashboardFrame>
  );
}
