"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  CreditCard,
  Search,
  Settings2,
  Sparkles,
  Plug,
  WalletCards,
} from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { ProviderIcon } from "@/components/integrations/ProviderIcon";
import { connectionStatus, providerRegistry, type IntegrationConnection } from "@/lib/integrations";
import {
  getAzureConnection,
  listAnthropicConnections,
  listAWSConnections,
  listGeminiConnections,
  listOpenAIConnections,
} from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function BillingPage() {
  const [search, setSearch] = useState("");
  const [connections, setConnections] = useState<Record<string, IntegrationConnection[]>>({});

  useEffect(() => {
    void Promise.allSettled([
      listAWSConnections(),
      listOpenAIConnections(),
      listGeminiConnections(),
      getAzureConnection(),
      listAnthropicConnections(),
    ]).then(([aws, openai, gemini, azure, anthropic]) => {
      const next: Record<string, IntegrationConnection[]> = {};
      if (aws.status === "fulfilled") next.aws = aws.value;
      if (openai.status === "fulfilled") next.openai = openai.value;
      if (gemini.status === "fulfilled") next.gemini = gemini.value;
      if (azure.status === "fulfilled" && azure.value.id) next.azure = [azure.value];
      if (anthropic.status === "fulfilled") next.anthropic = anthropic.value;
      setConnections(next);
    });
  }, []);

  const services = useMemo(() => {
    const query = search.trim().toLowerCase();
    return providerRegistry.filter(
      (provider) =>
        !query ||
        provider.name.toLowerCase().includes(query) ||
        provider.description.toLowerCase().includes(query)
    );
  }, [search]);

  const connectedCount = providerRegistry.filter(
    (provider) => connectionStatus((connections[provider.id] || [])[0]) === "CONNECTED"
  ).length;

  return (
    <DashboardFrame
      title="Billing & Invoices"
      description="Centralized invoice synchronization, API usage credit tracking, and cloud provider spend governance."
    >
      {/* Metric Cards Row */}
      <section aria-label="Billing Summary">
        <div className="section-title-row">
          <div>
            <span className="section-eyebrow">BILLING OVERVIEW</span>
            <h2 className="section-title">Synchronized Billing Status</h2>
          </div>
        </div>
        <div className="overview-metrics-grid">
          <MetricCard
            label="Catalog Providers"
            value={providerRegistry.length}
            subtext="Supported cloud & SaaS vendors"
            icon={<CreditCard size={20} />}
          />
          <MetricCard
            label="Live Connected Billing"
            value={connectedCount}
            subtext="Telemetry synchronized"
            icon={<Plug size={20} />}
          />
          <MetricCard
            label="Contract Records"
            value="Manage"
            subtext="Seats, prices, and renewal terms"
            icon={<WalletCards size={20} />}
          />
        </div>
      </section>

      {/* Provider Billing Grid Section */}
      <section className="dashboard-content-card mt-6">
        <div className="card-header-bar">
          <div>
            <span className="section-eyebrow">PORTALS</span>
            <h2 className="card-heading">Service Billing Portals</h2>
            <p className="card-subheading">
              Select a connected service to inspect invoices or configure live cloud billing data.
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="filter-toolbar">
          <div className="filter-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search billing services…"
              aria-label="Search billing services"
            />
            {search && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setSearch("")}
              >
                ×
              </button>
            )}
          </div>
        </div>

        {services.length === 0 ? (
          <EmptyState
            icon={<Search size={28} />}
            title="No billing services matched"
            description="Try modifying your search term."
          />
        ) : (
          <div className="services-3col-grid">
            {services.map((provider) => {
              const items = connections[provider.id] || [];
              const isConnected = connectionStatus(items[0]) === "CONNECTED";

              return (
                <article key={provider.id} className="service-card">
                  <div className="service-card-header">
                    <div className={`service-logo-wrap provider-${provider.icon}`}>
                      <ProviderIcon icon={provider.icon} size={20} />
                    </div>
                    <StatusBadge
                      variant={
                        isConnected
                          ? "success"
                          : provider.availability === "available"
                          ? "neutral"
                          : "neutral"
                      }
                      size="sm"
                    >
                      {isConnected
                        ? "Connected"
                        : provider.availability === "available"
                        ? "Not Connected"
                        : "Manual Record"}
                    </StatusBadge>
                  </div>

                  <div className="service-card-body">
                    <span className="service-category-tag">
                      {provider.category.replace("-", " ")}
                    </span>
                    <h3 className="service-name">{provider.name}</h3>
                    <p className="service-description">{provider.description}</p>
                  </div>

                  <div className="service-capabilities">
                    <span className="capability-pill">{provider.authType}</span>
                    <span className="capability-pill">
                      {provider.availability === "available" ? "Live Telemetry" : "Manual Record"}
                    </span>
                  </div>

                  <div className="service-card-footer">
                    {provider.id === "aws" ? (
                      <Link
                        href="/dashboard/billing/aws"
                        className="btn btn-primary btn-sm btn-full"
                      >
                        <span>Open AWS Billing</span>
                        <ArrowRight size={14} />
                      </Link>
                    ) : provider.availability === "available" ? (
                      <Link
                        href="/dashboard/integrations"
                        className="btn btn-secondary btn-sm btn-full"
                      >
                        <Settings2 size={14} />
                        <span>Manage Connection</span>
                      </Link>
                    ) : (
                      <Link
                        href="/dashboard/subscriptions"
                        className="btn btn-outline btn-sm btn-full"
                      >
                        <Sparkles size={14} />
                        <span>Manage Records</span>
                      </Link>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </DashboardFrame>
  );
}
