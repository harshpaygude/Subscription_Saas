"use client";

import { useEffect, useState } from "react";
import { BarChart3, TrendingUp, CalendarClock, ShieldCheck, RefreshCw } from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { getAnalyticsSummary, type AnalyticsSummary } from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ExportAuditDropdown } from "@/components/dashboard/ExportAuditDropdown";

export default function ReportsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadData() {
    setLoading(true);
    try {
      const summary = await getAnalyticsSummary();
      setData(summary);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load analytics.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  return (
    <DashboardFrame
      title="Reports & Analytics"
      description="Aggregated SaaS and cloud expenditure analysis calculated directly from verified workspace contracts and telemetry."
      actions={
        <div className="reports-top-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin-animation" : ""} />
            <span>Refresh Analytics</span>
          </button>
          <ExportAuditDropdown data={data} />
        </div>
      }
    >
      {error && (
        <div className="alert-notice alert-danger mb-4" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      {/* KPI Metrics */}
      <section className="overview-metrics-grid" aria-label="Analytics Totals">
        <MetricCard
          label="Active Subscriptions"
          value={data?.active_subscriptions ?? (loading ? "…" : 0)}
          subtext="Currently billed software services"
          icon={<TrendingUp size={20} />}
        />
        <MetricCard
          label="Cancelled Contracts"
          value={data?.cancelled_subscriptions ?? (loading ? "…" : 0)}
          subtext="Terminated vendor commitments"
          icon={<ShieldCheck size={20} />}
        />
        <MetricCard
          label="Upcoming Renewals"
          value={data?.upcoming_renewals ?? (loading ? "…" : 0)}
          subtext="Expiring in the next 30 days"
          icon={<CalendarClock size={20} />}
        />
        <MetricCard
          label="Reporting Currencies"
          value={data ? Object.keys(data.totals_by_currency).length : (loading ? "…" : 0)}
          subtext="Multicurrency accounting"
          icon={<BarChart3 size={20} />}
        />
      </section>

      {/* Provider Spend Breakdown */}
      <section className="dashboard-content-card mt-6">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Provider Spend Distribution</h2>
            <p className="card-subheading">
              Current normalized 30-day run rate segmented by each connected cloud or SaaS provider.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Calculating financial telemetry…</span>
          </div>
        ) : !data || Object.keys(data.by_provider).length === 0 ? (
          <EmptyState
            icon={<BarChart3 size={28} />}
            title="No provider spend aggregated"
            description="Add subscriptions or connect cloud providers to start generating automated financial reports."
          />
        ) : (
          <div className="provider-reports-grid">
            {Object.entries(data.by_provider).map(([provider, row]) => (
              <div key={provider} className="provider-report-card">
                <div className="report-card-top">
                  <span className="report-provider-name">{provider}</span>
                  <StatusBadge
                    variant={row.data_status === "LIVE" ? "success" : "neutral"}
                    size="sm"
                  >
                    {row.data_status}
                  </StatusBadge>
                </div>
                <div className="report-card-spend">
                  <strong>
                    {row.currency} {Number(row.monthly_spend).toLocaleString()}
                  </strong>
                  <small>Normalized monthly run rate</small>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Historical Aggregation Notice */}
        <div className="historical-note-box mt-6">
          <BarChart3 size={20} className="text-muted flex-none" />
          <div>
            <strong className="block text-primary text-sm">Longitudinal Snapshots</strong>
            <span className="text-muted text-xs">
              {data?.historical_note ||
                "Historical trendline snapshots are recorded each billing cycle as provider telemetry persists."}
            </span>
          </div>
        </div>
      </section>
    </DashboardFrame>
  );
}
