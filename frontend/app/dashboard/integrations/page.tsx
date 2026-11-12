"use client";

import { useEffect, useMemo, useState } from "react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { AddIntegrationWizard } from "@/components/integrations/AddIntegrationWizard";
import { AnthropicIntegrationDetails } from "@/components/integrations/AnthropicIntegrationDetails";
import { AzureIntegrationDetails } from "@/components/integrations/AzureIntegrationDetails";
import { GeminiUsageDetails } from "@/components/integrations/GeminiUsageDetails";
import { IntegrationCard } from "@/components/integrations/IntegrationCard";
import { IntegrationDetails } from "@/components/integrations/IntegrationDetails";
import { IntegrationFilters, type IntegrationFilterCategory, type IntegrationFilterStatus } from "@/components/integrations/IntegrationFilters";
import { OpenAIUsageDetails } from "@/components/integrations/OpenAIUsageDetails";
import { GenericProviderDetails } from "@/components/integrations/GenericProviderDetails";
import { providerRegistry, sortProviders, connectionStatus, getProvider, type AWSConnectionCredentials, type IntegrationConnection, type ProviderDefinition } from "@/lib/integrations";
import {
  connectAWS,
  connectAnthropic,
  connectAzureServicePrincipal,
  connectGemini,
  connectOpenAI,
  connectProvider,
  createSubscription,
  disconnectAnthropic,
  disconnectAWS,
  disconnectAzure,
  disconnectGemini,
  disconnectOpenAI,
  disconnectProviderConnection,
  getAWSAccountPlan,
  getAWSCosts,
  getAzureConnection,
  listAllActiveConnections,
  listAnthropicConnections,
  listAWSConnections,
  listGeminiConnections,
  listOpenAIConnections,
  testAnthropicConnection,
  testAzureConnection,
  testGeminiConnection,
  testOpenAIConnection,
  testProviderConnection,
  type AWSAccountPlanResponse,
  type AWSConnection,
  type AWSCostResponse,
  type AnthropicConnection,
  type AzureConnection,
  type GeminiConnection,
  type GenericProviderConnection,
  type OpenAIConnection,
} from "@/lib/api";

export default function IntegrationsPage() {
  const [aws, setAws] = useState<AWSConnection[]>([]);
  const [openai, setOpenai] = useState<OpenAIConnection[]>([]);
  const [gemini, setGemini] = useState<GeminiConnection[]>([]);
  const [azure, setAzure] = useState<AzureConnection[]>([]);
  const [anthropic, setAnthropic] = useState<AnthropicConnection[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<IntegrationFilterCategory>("all");
  const [status, setStatus] = useState<IntegrationFilterStatus>("all");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardProvider, setWizardProvider] = useState<ProviderDefinition | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [awsDetails, setAwsDetails] = useState<AWSConnection | null>(null);
  const [openaiDetails, setOpenaiDetails] = useState<OpenAIConnection | null>(null);
  const [geminiDetails, setGeminiDetails] = useState<GeminiConnection | null>(null);
  const [azureDetails, setAzureDetails] = useState<AzureConnection | null>(null);
  const [anthropicDetails, setAnthropicDetails] = useState<AnthropicConnection | null>(null);
  const [genericConnections, setGenericConnections] = useState<Record<string, GenericProviderConnection[]>>({});
  const [genericDetails, setGenericDetails] = useState<GenericProviderConnection | null>(null);
  const [genericProviderDef, setGenericProviderDef] = useState<ProviderDefinition | null>(null);
  const [awsPlan, setAwsPlan] = useState<AWSAccountPlanResponse | undefined>();
  const [awsCost, setAwsCost] = useState<AWSCostResponse | undefined>();
  const [awsPlanError, setAwsPlanError] = useState("");

  const byProvider: Record<string, IntegrationConnection[]> = { aws, openai, gemini, azure, anthropic, ...genericConnections };

  useEffect(() => {
    void Promise.allSettled([
      listAWSConnections(),
      listOpenAIConnections(),
      listGeminiConnections(),
      getAzureConnection(),
      listAnthropicConnections(),
      listAllActiveConnections(),
    ]).then(([a, o, g, z, c, act]) => {
      if (a.status === "fulfilled") setAws(a.value);
      if (o.status === "fulfilled") setOpenai(o.value);
      if (g.status === "fulfilled") setGemini(g.value);
      if (z.status === "fulfilled") setAzure(z.value.id ? [z.value] : []);
      if (c.status === "fulfilled") setAnthropic(c.value);
      if (act.status === "fulfilled") {
        const grouped: Record<string, GenericProviderConnection[]> = {};
        for (const conn of act.value) {
          const key = conn.provider.toLowerCase().replace(/_/g, "-");
          if (!grouped[key]) grouped[key] = [];
          grouped[key].push(conn);
        }
        setGenericConnections(grouped);
      }
    });
  }, []);

  const providers = useMemo(() => {
    const query = search.trim().toLowerCase();
    return sortProviders(providerRegistry.filter((provider) => {
      const connection = byProvider[provider.id]?.[0];
      return (!query || [provider.name, provider.description].some((value) => value.toLowerCase().includes(query))) && (category === "all" || provider.category === category) && (status === "all" || (status === "connected" ? connectionStatus(connection) === "CONNECTED" : connectionStatus(connection) !== "CONNECTED"));
    }), byProvider);
  }, [search, category, status, aws, openai, gemini, azure, anthropic, genericConnections]);

  function closeWizard() {
    if (!busy) { setWizardOpen(false); setWizardProvider(null); setError(""); }
  }

  function closeDetails() {
    setAwsDetails(null); setOpenaiDetails(null); setGeminiDetails(null); setAzureDetails(null); setAnthropicDetails(null);
    setGenericDetails(null); setGenericProviderDef(null);
    setAwsPlan(undefined); setAwsCost(undefined); setAwsPlanError("");
  }

  async function loadAwsPlan(connectionId: number) {
    setAwsPlanError("");
    try { setAwsPlan(await getAWSAccountPlan(connectionId)); }
    catch (requestError) { setAwsPlan(undefined); setAwsPlanError(requestError instanceof Error ? requestError.message : "AWS credit information is unavailable."); }
  }

  async function loadAwsCost() {
    if (!awsDetails) return;
    setBusy(true);
    try { setAwsCost(await getAWSCosts(awsDetails.id)); }
    catch (requestError) { setNotice(requestError instanceof Error ? requestError.message : "AWS cost data is unavailable."); }
    finally { setBusy(false); }
  }

  function viewDetails(provider: ProviderDefinition, connection?: IntegrationConnection) {
    if (!connection) return;
    closeDetails();
    if (provider.id === "aws") { const value = connection as AWSConnection; setAwsDetails(value); void loadAwsPlan(value.id); }
    else if (provider.id === "openai") setOpenaiDetails(connection as OpenAIConnection);
    else if (provider.id === "gemini") setGeminiDetails(connection as GeminiConnection);
    else if (provider.id === "azure") setAzureDetails(connection as AzureConnection);
    else if (provider.id === "anthropic") setAnthropicDetails(connection as AnthropicConnection);
    else {
      setGenericDetails(connection as GenericProviderConnection);
      setGenericProviderDef(provider);
    }
  }

  async function submit<T>(action: () => Promise<T>, success: string) {
    setBusy(true); setError("");
    try { await action(); setNotice(success); closeWizard(); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "The provider request failed."); throw requestError; }
    finally { setBusy(false); }
  }

  async function disconnect(connection: IntegrationConnection) {
    if (!window.confirm("Disconnect this integration?")) return;
    setBusy(true);
    try {
      const provUpper = connection.provider.toUpperCase();
      if (provUpper === "AWS") { await disconnectAWS(connection.id); setAws((items) => items.filter((item) => item.id !== connection.id)); }
      else if (provUpper === "OPENAI") { await disconnectOpenAI(connection.id); setOpenai((items) => items.filter((item) => item.id !== connection.id)); }
      else if (provUpper === "GEMINI") { await disconnectGemini(connection.id); setGemini((items) => items.filter((item) => item.id !== connection.id)); }
      else if (provUpper === "AZURE") { await disconnectAzure(); setAzure([]); }
      else if (provUpper === "ANTHROPIC") { await disconnectAnthropic(connection.id); setAnthropic((items) => items.filter((item) => item.id !== connection.id)); }
      else {
        const provKey = connection.provider.toLowerCase().replace(/_/g, "-");
        await disconnectProviderConnection(provKey, connection.id);
        setGenericConnections((curr) => ({
          ...curr,
          [provKey]: (curr[provKey] || []).filter((item) => item.id !== connection.id),
        }));
      }
      closeDetails(); setNotice("Integration disconnected.");
    } catch (requestError) { setNotice(requestError instanceof Error ? requestError.message : "Could not disconnect the integration."); }
    finally { setBusy(false); }
  }

  async function test(connection: IntegrationConnection) {
    setBusy(true);
    try {
      const provUpper = connection.provider.toUpperCase();
      if (provUpper === "OPENAI") { const result = await testOpenAIConnection(connection.id); setOpenai((items) => items.map((item) => item.id === connection.id ? { ...item, status: result.status, last_verified_at: result.last_verified_at } : item)); }
      else if (provUpper === "GEMINI") { const result = await testGeminiConnection(connection.id); setGemini((items) => items.map((item) => item.id === connection.id ? { ...item, status: result.status, last_verified_at: result.last_verified_at } : item)); }
      else if (provUpper === "ANTHROPIC") { const result = await testAnthropicConnection(connection.id); setAnthropic((items) => items.map((item) => item.id === connection.id ? { ...item, status: result.status, last_verified_at: result.last_verified_at } : item)); }
      else if (provUpper === "AZURE") { const result = await testAzureConnection(); setAzure((items) => items.map((item) => ({ ...item, status: result.status, last_successful_refresh: result.last_successful_refresh }))); }
      else {
        const provKey = connection.provider.toLowerCase().replace(/_/g, "-");
        const result = await testProviderConnection(provKey, connection.id);
        setGenericConnections((curr) => ({
          ...curr,
          [provKey]: (curr[provKey] || []).map((item) => item.id === connection.id ? { ...item, status: result.status, last_verified_at: result.last_verified_at, profile_data: result.profile_data || item.profile_data } : item),
        }));
        if (genericDetails && genericDetails.id === connection.id) {
          setGenericDetails((curr) => curr ? { ...curr, status: result.status, last_verified_at: result.last_verified_at, profile_data: result.profile_data || curr.profile_data } : null);
        }
      }
      setNotice("Connection test completed.");
    } catch (requestError) { setNotice(requestError instanceof Error ? requestError.message : "Connection test failed."); }
    finally { setBusy(false); }
  }

  return (
    <DashboardFrame
      title="All services"
      description="Connect, verify, and manage the services in your workspace."
      onAddIntegration={() => setWizardOpen(true)}
    >
      {notice && (
        <div className="hub-notice" role="status">
          {notice}
        </div>
      )}

      <section className="hub-section">
        <div className="hub-section-heading">
          <div>
            <p className="hub-eyebrow">PROVIDER CATALOG</p>
            <h2>Integrations</h2>
            <p>
              {providerRegistry.length} providers are catalogued. Only backend-confirmed
              connections show as connected.
            </p>
          </div>
          <button
            type="button"
            className="hub-primary-button"
            onClick={() => setWizardOpen(true)}
          >
            Add integration
          </button>
        </div>

        <IntegrationFilters
          search={search}
          category={category}
          status={status}
          onSearchChange={setSearch}
          onCategoryChange={setCategory}
          onStatusChange={setStatus}
        />

        <div className="hub-integration-grid">
          {providers.map((provider) => (
            <IntegrationCard
              key={provider.id}
              provider={provider}
              connections={byProvider[provider.id]}
              onConnect={(selected) => {
                setWizardProvider(selected);
                setWizardOpen(true);
              }}
              onDisconnect={disconnect}
              onTest={provider.availability === "available" && provider.id !== "aws" ? test : undefined}
              onView={viewDetails}
            />
          ))}
        </div>
      </section>

      <AddIntegrationWizard
        open={wizardOpen}
        initialProvider={wizardProvider}
        connections={aws}
        connectedProviderIds={Object.entries(byProvider)
          .filter(([, items]) => items.length > 0)
          .map(([id]) => id)}
        busy={busy}
        error={error}
        onClose={closeWizard}
        onSubmitAWS={(credentials: AWSConnectionCredentials) =>
          submit(async () => {
            const result = await connectAWS(credentials);
            setAws((items) => [
              result.connection,
              ...items.filter((item) => item.id !== result.connection.id),
            ]);
          }, "AWS connected successfully.")
        }
        onSubmitOpenAI={(key) =>
          submit(async () => {
            const result = await connectOpenAI(key);
            setOpenai((items) => [
              result.connection,
              ...items.filter((item) => item.id !== result.connection.id),
            ]);
          }, "OpenAI connected successfully.")
        }
        onSubmitGemini={(key) =>
          submit(async () => {
            const result = await connectGemini(key);
            setGemini((items) => [
              result.connection,
              ...items.filter((item) => item.id !== result.connection.id),
            ]);
          }, "Gemini connected successfully.")
        }
        onSubmitAzure={(credentials) =>
          submit(async () => {
            const result = await connectAzureServicePrincipal(credentials);
            setAzure([result]);
          }, "Azure connected successfully.")
        }
        onSubmitAnthropic={(key, model, name, tier) =>
          submit(async () => {
            const result = await connectAnthropic(key, model, name, tier);
            setAnthropic((items) => [
              result.connection,
              ...items.filter((item) => item.id !== result.connection.id),
            ]);
          }, "Anthropic Claude connected successfully.")
        }
        onSubmitGenericProvider={(providerId, credentials) =>
          submit(async () => {
            const result = await connectProvider(providerId, credentials);
            const provKey = providerId.toLowerCase().replace(/_/g, "-");
            setGenericConnections((curr) => ({
              ...curr,
              [provKey]: [result.connection, ...(curr[provKey] || []).filter((item) => item.id !== result.connection.id)],
            }));
          }, `${wizardProvider?.name || "Provider"} connected successfully.`)
        }
        onSubmitManual={(provider, payload) =>
          submit(async () => {
            await createSubscription({
              provider: provider.name,
              name: payload.name,
              plan: payload.plan || null,
              amount: payload.amount || null,
              currency: payload.currency,
              billing_interval: payload.billing_interval,
              start_date: new Date().toISOString().slice(0, 10),
              next_renewal_date: payload.next_renewal_date || null,
              note: `Manual service record created from the ${provider.name} catalog.`,
            });
          }, `${wizardProvider?.name || "Service"} tracked successfully.`)
        }
      />

      {awsDetails && (
        <IntegrationDetails
          provider={getProvider("aws")!}
          connection={awsDetails}
          cost={awsCost}
          plan={awsPlan}
          planError={awsPlanError}
          busy={busy}
          onClose={closeDetails}
          onLoadCosts={() => void loadAwsCost()}
          onRefreshPlan={() => void loadAwsPlan(awsDetails.id)}
        />
      )}

      {openaiDetails && (
        <OpenAIUsageDetails
          provider={getProvider("openai")!}
          connection={openaiDetails}
          onClose={closeDetails}
        />
      )}

      {geminiDetails && (
        <GeminiUsageDetails
          provider={getProvider("gemini")!}
          connection={geminiDetails}
          onClose={closeDetails}
        />
      )}

      {azureDetails && (
        <AzureIntegrationDetails
          provider={getProvider("azure")!}
          connection={azureDetails}
          onClose={closeDetails}
        />
      )}

      {anthropicDetails && (
        <AnthropicIntegrationDetails
          provider={getProvider("anthropic")!}
          connection={anthropicDetails}
          onClose={closeDetails}
          onConnectionChange={(updated) => {
            setAnthropic((items) =>
              items.map((item) => (item.id === updated.id ? updated : item))
            );
            setAnthropicDetails(updated);
          }}
        />
      )}

      {genericDetails && genericProviderDef && (
        <GenericProviderDetails
          provider={genericProviderDef}
          connection={genericDetails}
          onClose={closeDetails}
          onDisconnect={() => void disconnect(genericDetails)}
        />
      )}
    </DashboardFrame>
  );
}
