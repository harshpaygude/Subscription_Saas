"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { ProviderIcon } from "@/components/integrations/ProviderIcon";
import { connectionStatus, providerRegistry, type IntegrationConnection } from "@/lib/integrations";
import { getAzureConnection, listAnthropicConnections, listAWSConnections, listGeminiConnections, listOpenAIConnections } from "@/lib/api";

export default function BillingPage() {
  const [search, setSearch] = useState("");
  const [connections, setConnections] = useState<Record<string, IntegrationConnection[]>>({});

  useEffect(() => {
    void Promise.allSettled([listAWSConnections(), listOpenAIConnections(), listGeminiConnections(), getAzureConnection(), listAnthropicConnections()]).then(([aws, openai, gemini, azure, anthropic]) => {
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
    return providerRegistry.filter((provider) => !query || provider.name.toLowerCase().includes(query) || provider.description.toLowerCase().includes(query));
  }, [search]);

  return <DashboardFrame title="Billing" description="Choose a connected service to review provider billing and spend information.">
    <section className="hub-section">
      <div className="hub-section-heading"><div><p className="hub-eyebrow">Service billing</p><h2>All services</h2><p>Search your service catalog and open the provider billing view where supported.</p></div></div>
      <label className="hub-search hub-billing-search"><Search size={16} /><span className="sr-only">Search services</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search services…" /></label>
      {services.length === 0 ? <div className="hub-empty-state"><h3>No services found</h3><p>Try a different search term.</p></div> : <div className="hub-billing-service-grid">{services.map((provider) => {
        const items = connections[provider.id] || [];
        const connected = connectionStatus(items[0]) === "CONNECTED";
        return <article className="hub-billing-service-card" key={provider.id}>
          <div className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} size={20} /></div>
          <div className="hub-billing-service-copy"><p className="hub-eyebrow">{provider.category.replace("-", " ")}</p><h3>{provider.name}</h3><p>{provider.description}</p></div>
          <div className="hub-billing-service-footer"><span className={`hub-availability ${connected ? "connected" : provider.availability === "available" ? "ready" : "soon"}`}>{connected ? "Connected" : provider.availability === "available" ? "Not connected" : "Coming soon"}</span>{provider.id === "aws" ? <Link className="hub-primary-button small" href="/dashboard/billing/aws">Open AWS billing <ArrowRight size={14} /></Link> : <span className="hub-billing-unavailable">Provider billing view unavailable</span>}</div>
        </article>;
      })}</div>}
    </section>
  </DashboardFrame>;
}
