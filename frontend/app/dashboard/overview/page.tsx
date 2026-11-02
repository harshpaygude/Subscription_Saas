"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  CalendarClock,
  CircleDollarSign,
  Laptop,
  Plug,
  RefreshCw,
  Settings,
  Users,
  WalletCards,
  CheckCircle2,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { connectionStatus, providerRegistry } from "@/lib/integrations";
import {
  getAnalyticsSummary,
  getAzureConnection,
  listAnthropicConnections,
  listAWSConnections,
  listGeminiConnections,
  listOpenAIConnections,
  type AnalyticsSummary,
} from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";

export default function OverviewPage() {
  const [connected, setConnected] = useState<number | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    setLoading(true);
    try {
      const [connectionResults, summary] = await Promise.all([
        Promise.allSettled([
          listAWSConnections(),
          listOpenAIConnections(),
          listGeminiConnections(),
          getAzureConnection(),
          listAnthropicConnections(),
        ]),
        getAnalyticsSummary().catch(() => null),
      ]);

      let count = 0;
      connectionResults.forEach((result) => {
        if (result.status !== "fulfilled") return;
        const val = result.value;
        const items = Array.isArray(val) ? val : [val];
        count += items.filter(
          (item) => item && connectionStatus(item).toString() === "CONNECTED"
        ).length;
      });

      setConnected(count);
      setAnalytics(summary);
    } catch {
      // Keep existing state on error
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const currencies = analytics ? Object.entries(analytics.totals_by_currency) : [];
  const spendDisplay =
    currencies.length === 1
      ? `${currencies[0][0]} ${Number(currencies[0][1]).toLocaleString()}`
      : currencies.length > 1
      ? "Multiple Currencies"
      : "—";

  return (
    <DashboardFrame
      title="Overview"
      description="Holistic visibility into connected cloud providers, SaaS subscriptions, team usage, and IT assets."
      actions={
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadData}
          disabled={loading}
          title="Refresh workspace metrics"
        >
          <RefreshCw size={14} className={loading ? "spin-animation" : ""} />
          <span>Refresh</span>
        </button>
      }
    >
      {/* Portfolio Health Hero Banner */}
      <section className="overview-hero-card">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="hero-badge-dot" />
            <span>Portfolio Intelligence</span>
          </div>
          <h2 className="hero-title">Continuous Cloud & SaaS Cost Governance</h2>
          <p className="hero-desc">
            UniSora PRO actively correlates your connected infrastructure, vendor subscriptions, and employee licenses in one unified control pane.
          </p>
        </div>

        <div className="hero-health-panel">
          <div className="health-stat-header">
            <Plug size={18} className="health-icon" />
            <span>Integration Status</span>
          </div>
          <div className="health-stat-value">
            <strong>
              {connected !== null
                ? `${connected} Active Connection${connected === 1 ? "" : "s"}`
                : "Loading…"}
            </strong>
            <small>
              {connected === 0
                ? "No providers connected yet. Connect AWS, Azure, OpenAI or Gemini."
                : "Backend-verified and securely synchronized."}
            </small>
          </div>
          <Link href="/dashboard/integrations" className="hero-action-link">
            <span>Manage Integrations</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </section>

      {/* KPI Metric Cards Grid */}
      <section className="overview-metrics-grid" aria-label="Key Performance Indicators">
        <MetricCard
          label="Total Monthly Spend"
          value={spendDisplay}
          subtext={currencies.length === 1 ? "Active monthly run rate" : "From verified invoices & manual records"}
          icon={<CircleDollarSign size={20} />}
        />
        <MetricCard
          label="Active Subscriptions"
          value={analytics?.active_subscriptions ?? (loading ? "…" : 0)}
          subtext="Persisted SaaS vendor records"
          icon={<WalletCards size={20} />}
        />
        <MetricCard
          label="Connected Providers"
          value={connected ?? (loading ? "…" : 0)}
          subtext={`Out of ${providerRegistry.length} catalog integrations`}
          icon={<Plug size={20} />}
        />
        <MetricCard
          label="Upcoming Renewals"
          value={analytics?.upcoming_renewals ?? (loading ? "…" : 0)}
          subtext="Within the next 30 days"
          icon={<CalendarClock size={20} />}
        />
        <MetricCard
          label="Managed IT Assets"
          value={analytics?.assets?.total ?? (loading ? "…" : 0)}
          subtext={
            analytics?.assets
              ? `${analytics.assets.assigned} assigned · ${analytics.assets.available} available`
              : "Company hardware inventory"
          }
          icon={<Laptop size={20} />}
        />
        <MetricCard
          label="Active Departments"
          value={analytics?.departments ?? (loading ? "…" : 0)}
          subtext="Organization team divisions"
          icon={<Users size={20} />}
        />
      </section>

      {/* Quick Access Shortcuts Grid */}
      <section className="overview-shortcuts-section">
        <div className="section-title-row">
          <div>
            <h3 className="section-title">Essential Workflows</h3>
            <p className="section-subtitle">Direct shortcuts to configure and audit your workspace resources</p>
          </div>
        </div>

        <div className="shortcuts-grid">
          <ShortcutCard
            href="/dashboard/integrations"
            icon={<Plug size={20} />}
            title={`Explore ${providerRegistry.length} Integrations`}
            desc="Connect AWS, Azure, OpenAI, Anthropic, Gemini, and custom API webhooks."
          />
          <ShortcutCard
            href="/dashboard/subscriptions"
            icon={<WalletCards size={20} />}
            title="SaaS Subscriptions & Licenses"
            desc="Allocate software seats to employees and monitor contract renewal dates."
          />
          <ShortcutCard
            href="/dashboard/departments"
            icon={<Users size={20} />}
            title="Team & Department Management"
            desc="Configure organizational units and track department head membership."
          />
          <ShortcutCard
            href="/dashboard/employees"
            icon={<Users size={20} />}
            title="Employee Lifecycle & Access"
            desc="Onboard team members, assign hardware, and clear offboarding checklists."
          />
          <ShortcutCard
            href="/dashboard/assets"
            icon={<Laptop size={20} />}
            title="Physical IT Asset Tracking"
            desc="Register laptops, workstations, and manage custody handover logs."
          />
          <ShortcutCard
            href="/dashboard/usage"
            icon={<CircleDollarSign size={20} />}
            title="Cost Analysis & Invoices"
            desc="Review normalized monthly spend per provider and log custom cost entries."
          />
        </div>
      </section>
    </DashboardFrame>
  );
}

function ShortcutCard({
  href,
  icon,
  title,
  desc,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
}) {
  return (
    <Link href={href} className="shortcut-card">
      <div className="shortcut-icon-wrap">{icon}</div>
      <div className="shortcut-body">
        <h4 className="shortcut-title">{title}</h4>
        <p className="shortcut-desc">{desc}</p>
      </div>
      <div className="shortcut-arrow">
        <ArrowRight size={16} />
      </div>
    </Link>
  );
}
