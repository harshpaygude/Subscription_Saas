import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Check, Copy, ExternalLink, Eye, EyeOff, Search, X } from "lucide-react";
import type { AWSConnection } from "@/lib/api";
import type { AWSConnectionCredentials, AzureServicePrincipalCredentials, IntegrationCategory, ProviderDefinition } from "@/lib/integrations";
import { categoryLabels, providerRegistry } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

type WizardStep = "select" | "requirements" | "configure" | "verify";

interface AddIntegrationWizardProps {
  open: boolean;
  initialProvider?: ProviderDefinition | null;
  connections: AWSConnection[];
  connectedProviderIds?: string[];
  busy: boolean;
  error: string;
  onClose: () => void;
  onSubmitAWS: (credentials: AWSConnectionCredentials) => Promise<void>;
  onSubmitOpenAI: (apiKey: string) => Promise<void>;
  onSubmitGemini: (apiKey: string) => Promise<void>;
  onSubmitAzure: (credentials: AzureServicePrincipalCredentials) => Promise<void>;
  onSubmitAnthropic: (apiKey: string, model: string, connectionName?: string) => Promise<void>;
}

const stepLabels: Record<WizardStep, string> = {
  select: "Select service",
  requirements: "Requirements",
  configure: "Configure",
  verify: "Verify",
};

export function AddIntegrationWizard({ open, initialProvider = null, connections, connectedProviderIds = [], busy, error, onClose, onSubmitAWS, onSubmitOpenAI, onSubmitGemini, onSubmitAzure, onSubmitAnthropic }: AddIntegrationWizardProps) {
  const [provider, setProvider] = useState<ProviderDefinition | null>(initialProvider);
  const [step, setStep] = useState<WizardStep>(initialProvider ? "requirements" : "select");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<"all" | IntegrationCategory>("all");
  const [accessKeyId, setAccessKeyId] = useState("");
  const [secretAccessKey, setSecretAccessKey] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [region, setRegion] = useState("us-east-1");
  const [showSecret, setShowSecret] = useState(false);
  const [copied, setCopied] = useState(false);
  const [openaiApiKey, setOpenaiApiKey] = useState("");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [anthropicApiKey, setAnthropicApiKey] = useState("");
  const [anthropicModel, setAnthropicModel] = useState("claude-sonnet-4-6");
  const [anthropicConnectionName, setAnthropicConnectionName] = useState("");
  const [azureTenantId, setAzureTenantId] = useState("");
  const [azureClientId, setAzureClientId] = useState("");
  const [azureClientSecret, setAzureClientSecret] = useState("");
  const [azureSubscriptionId, setAzureSubscriptionId] = useState("");

  useEffect(() => {
    if (open) {
      setProvider(initialProvider || null);
      setStep(initialProvider ? "requirements" : "select");
      setSearch("");
      setCategory("all");
      setCopied(false);
    }
  }, [initialProvider, open]);

  function clearSensitiveState() {
    setAccessKeyId("");
    setSecretAccessKey("");
    setSessionToken("");
    setRegion("us-east-1");
    setShowSecret(false);
    setOpenaiApiKey("");
    setGeminiApiKey("");
    setAnthropicApiKey("");
    setAnthropicModel("claude-sonnet-4-6");
    setAnthropicConnectionName("");
    setAzureTenantId("");
    setAzureClientId("");
    setAzureClientSecret("");
    setAzureSubscriptionId("");
  }

  function close() {
    if (busy) return;
    clearSensitiveState();
    setProvider(null);
    setStep("select");
    onClose();
  }

  const filteredProviders = useMemo(() => {
    const query = search.trim().toLowerCase();
    return providerRegistry.filter((item) => {
      const matchesQuery = !query || [item.name, item.description, item.authType].some((value) => value.toLowerCase().includes(query));
      return matchesQuery && (category === "all" || item.category === category);
    });
  }, [category, search]);

  if (!open) return null;

  function chooseProvider(selected: ProviderDefinition) {
    setProvider(selected);
    setStep("requirements");
  }

  function back() {
    if (step === "requirements") setStep("select");
    if (step === "configure") setStep("requirements");
  }

  async function submitAWS(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStep("verify");
    try {
      await onSubmitAWS({
        access_key_id: accessKeyId.trim(),
        secret_access_key: secretAccessKey,
        ...(sessionToken.trim() ? { session_token: sessionToken.trim() } : {}),
        region: region.trim(),
      });
      clearSensitiveState();
    } catch {
      setStep("configure");
    }
  }

  async function copyAWSRequirements() {
    const policy = `Required AWS permissions for UniSora\n\n- sts:GetCallerIdentity\n- ce:GetCostAndUsage\n- freetier:GetAccountPlanState (optional plan details)`;
    await navigator.clipboard.writeText(policy);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  async function submitOpenAI(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!openaiApiKey.trim()) return;
    setStep("verify");
    try {
      await onSubmitOpenAI(openaiApiKey.trim());
      clearSensitiveState();
    } catch {
      setStep("configure");
    }
  }

  async function submitGemini(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!geminiApiKey.trim()) return;
    setStep("verify");
    try { await onSubmitGemini(geminiApiKey.trim()); clearSensitiveState(); } catch { setStep("configure"); }
  }

  async function submitAnthropic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!anthropicApiKey.trim() || !anthropicModel.trim()) return;
    setStep("verify");
    try { await onSubmitAnthropic(anthropicApiKey.trim(), anthropicModel.trim(), anthropicConnectionName); clearSensitiveState(); }
    catch { setStep("configure"); }
  }

  const isAWS = provider?.id === "aws";
  const isOpenAI = provider?.id === "openai";
  const isGemini = provider?.id === "gemini";
  const isAzure = provider?.id === "azure";
  const isAnthropic = provider?.id === "anthropic";
  const isConnectable = provider?.availability === "available";
  const isComingSoon = provider?.availability === "coming-soon";
  const steps: WizardStep[] = provider
    ? ["requirements", ...(isConnectable ? (["configure", "verify"] as WizardStep[]) : [])]
    : ["select"];

  return (
    <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && close()}>
      <section className="hub-dialog hub-wizard-dialog" role="dialog" aria-modal="true" aria-labelledby="add-integration-title">
        <div className="hub-dialog-header">
          <div><p className="hub-eyebrow">{provider ? "Add integration" : "Integration catalog"}</p><h2 id="add-integration-title">{provider ? provider.name : "Add an integration"}</h2></div>
          <button className="hub-icon-action" onClick={close} aria-label="Close integration wizard"><X size={18} /></button>
        </div>
        {provider && <div className="hub-wizard-progress" aria-label="Connection progress">{steps.map((item, index) => <div className={`hub-wizard-step ${item === step ? "active" : ["requirements", "configure", "verify"].indexOf(item) < ["requirements", "configure", "verify"].indexOf(step) ? "complete" : ""}`} key={item}><span>{item === step || ["requirements", "configure", "verify"].indexOf(item) <= ["requirements", "configure", "verify"].indexOf(step) ? <Check size={12} /> : index + 1}</span>{stepLabels[item]}</div>)}</div>}
        {!provider ? (
          <>
            <p className="hub-dialog-intro">Choose a provider to see its authentication method, required permissions and connection status.</p>
            <div className="hub-wizard-toolbar"><label className="hub-wizard-search"><Search size={16} /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search integrations" /></label><select value={category} onChange={(event) => setCategory(event.target.value as "all" | IntegrationCategory)} aria-label="Filter providers by category"><option value="all">All categories</option>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
            <div className="hub-provider-picker">{filteredProviders.map((item) => { const connected = connectedProviderIds.includes(item.id) || (item.id === "aws" && connections.length > 0); return <button className="hub-provider-option" key={item.id} onClick={() => chooseProvider(item)}><span className={`hub-provider-icon hub-provider-${item.icon}`}><ProviderIcon icon={item.icon} size={19} /></span><span className="hub-provider-option-copy"><strong>{item.name}</strong><small>{item.description}</small><em>{item.authType}</em></span><span className={`hub-picker-status ${connected ? "connected" : item.availability === "available" ? "available" : "soon"}`}>{connected ? "Connected" : item.availability === "available" ? "Available" : "Coming soon"}<ArrowRight size={15} /></span></button>; })}</div>
            {!filteredProviders.length && <div className="hub-empty-state"><Search size={20} /><h3>No integrations found</h3><p>Try a different provider or category.</p></div>}
            <div className="hub-dialog-actions"><button className="hub-secondary-button" onClick={close}>Cancel</button></div>
          </>
        ) : step === "requirements" ? (
          <>
            <div className="hub-wizard-provider"><span className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} size={22} /></span><div><strong>{provider.name}</strong><span>{categoryLabels[provider.category]} · {provider.authType}</span></div><span className={`hub-picker-status ${isComingSoon ? "soon" : "available"}`}>{isComingSoon ? "Coming soon" : "Available"}</span></div>
            <div className="hub-requirements"><h3>What you’ll need</h3><ul>{provider.requiredFields.map((field) => <li key={field}><Check size={14} />{field}</li>)}</ul>{provider.optionalFields?.length ? <p><strong>Optional:</strong> {provider.optionalFields.join(", ")}</p> : null}</div>
            <div className="hub-instruction-list"><h3>Connection details</h3>{provider.instructions.map((instruction) => <p key={instruction}>{instruction}</p>)}</div>
            {isAWS && <div className="hub-permission-callout"><div><strong>Least-privilege scope</strong><span>STS identity verification is required. Cost Explorer and Free Tier data require their respective read-only permissions.</span></div><button className="hub-secondary-button" onClick={() => void copyAWSRequirements()}><Copy size={14} />{copied ? "Copied" : "Copy permissions"}</button></div>}
            {provider.id === "openai" && <a className="hub-external-link" href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer">Open OpenAI API key management <ExternalLink size={13} /></a>}
            {provider.id === "gemini" && <a className="hub-external-link" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">Open Google AI Studio API keys <ExternalLink size={13} /></a>}
            {provider.id === "anthropic" && <a className="hub-external-link" href="https://platform.claude.com/settings/keys" target="_blank" rel="noreferrer">Open Anthropic Console API keys <ExternalLink size={13} /></a>}
            <div className="hub-dialog-actions"><button className="hub-secondary-button" onClick={back}><ArrowLeft size={14} /> Back</button>{isComingSoon ? <button className="hub-secondary-button" onClick={close}>Close</button> : <button className="hub-primary-button" onClick={() => setStep("configure")} disabled={busy}>Continue <ArrowRight size={14} /></button>}</div>
          </>
        ) : isAWS && step === "configure" ? (
          <form onSubmit={submitAWS}><p className="hub-dialog-intro">Enter the AWS credentials for the account you want to connect. They are sent only to the authenticated backend for verification and are cleared when this wizard closes.</p><div className="hub-form-grid"><label>Access key ID<input required value={accessKeyId} onChange={(event) => setAccessKeyId(event.target.value)} autoComplete="off" /></label><label>Secret access key<div className="hub-password-field"><input required value={secretAccessKey} onChange={(event) => setSecretAccessKey(event.target.value)} type={showSecret ? "text" : "password"} autoComplete="new-password" /><button type="button" onClick={() => setShowSecret((value) => !value)} aria-label={showSecret ? "Hide secret access key" : "Show secret access key"}>{showSecret ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label><label>Session token <span className="hub-label-note">optional</span><input value={sessionToken} onChange={(event) => setSessionToken(event.target.value)} type="password" autoComplete="off" /></label><label>AWS region<input required value={region} onChange={(event) => setRegion(event.target.value)} placeholder="us-east-1" /></label></div>{error && <p className="hub-form-error" role="alert">{error}</p>}<div className="hub-dialog-actions"><button type="button" className="hub-secondary-button" onClick={back}><ArrowLeft size={14} /> Back</button><button type="submit" className="hub-primary-button" disabled={busy}>Verify connection <ArrowRight size={14} /></button></div></form>
        ) : isOpenAI && step === "configure" ? (
          <form onSubmit={submitOpenAI}><p className="hub-dialog-intro">Enter an OpenAI API key. This is separate from a ChatGPT subscription or password. The key is sent to the authenticated backend for verification and is never saved in browser storage.</p><label>OpenAI API key<span className="hub-label-note"> required</span><div className="hub-password-field"><input required value={openaiApiKey} onChange={(event) => setOpenaiApiKey(event.target.value)} type={showSecret ? "text" : "password"} autoComplete="new-password" placeholder="sk-…" /><button type="button" onClick={() => setShowSecret((value) => !value)} aria-label={showSecret ? "Hide OpenAI API key" : "Show OpenAI API key"}>{showSecret ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>{error && <p className="hub-form-error" role="alert">{error}</p>}<div className="hub-dialog-actions"><button type="button" className="hub-secondary-button" onClick={back}><ArrowLeft size={14} /> Back</button><button type="submit" className="hub-primary-button" disabled={busy || !openaiApiKey.trim()}>Verify and connect <ArrowRight size={14} /></button></div></form>
        ) : isGemini && step === "configure" ? (
          <form onSubmit={submitGemini}><p className="hub-dialog-intro">Enter a Gemini API key. It is sent only to the authenticated backend for verification and is never stored in browser storage.</p><label>Gemini API key<span className="hub-label-note"> required</span><div className="hub-password-field"><input required value={geminiApiKey} onChange={(event) => setGeminiApiKey(event.target.value)} type={showSecret ? "text" : "password"} autoComplete="new-password" placeholder="AIza…" /><button type="button" onClick={() => setShowSecret((value) => !value)} aria-label={showSecret ? "Hide Gemini API key" : "Show Gemini API key"}>{showSecret ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>{error && <p className="hub-form-error" role="alert">{error}</p>}<div className="hub-dialog-actions"><button type="button" className="hub-secondary-button" onClick={back}><ArrowLeft size={14} /> Back</button><button type="submit" className="hub-primary-button" disabled={busy || !geminiApiKey.trim()}>Verify and connect <ArrowRight size={14} /></button></div></form>
        ) : isAnthropic && step === "configure" ? (
          <form onSubmit={submitAnthropic}><p className="hub-dialog-intro">Enter an Anthropic API key from the Anthropic Console. UniSora sends it only to the authenticated backend, which makes a minimal real Messages API request and stores the key encrypted. The complete key is never returned or stored in your browser.</p><label>Anthropic API key<span className="hub-label-note"> required</span><div className="hub-password-field"><input required value={anthropicApiKey} onChange={(event) => setAnthropicApiKey(event.target.value)} type={showSecret ? "text" : "password"} autoComplete="new-password" placeholder="sk-ant-…" /><button type="button" onClick={() => setShowSecret((value) => !value)} aria-label={showSecret ? "Hide Anthropic API key" : "Show Anthropic API key"}>{showSecret ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label><label>Claude model<select required value={anthropicModel} onChange={(event) => setAnthropicModel(event.target.value)}><option value="claude-sonnet-4-6">Claude Sonnet 4.6</option><option value="claude-opus-4-6">Claude Opus 4.6</option><option value="claude-haiku-4-5-20251001">Claude Haiku 4.5</option></select></label><label>Connection name <span className="hub-label-note">optional</span><input value={anthropicConnectionName} onChange={(event) => setAnthropicConnectionName(event.target.value)} maxLength={255} placeholder="Production Claude" /></label>{error && <p className="hub-form-error" role="alert">{error}</p>}<div className="hub-dialog-actions"><button type="button" className="hub-secondary-button" onClick={back}><ArrowLeft size={14} /> Back</button><button type="submit" className="hub-primary-button" disabled={busy || !anthropicApiKey.trim() || !anthropicModel.trim()}>Verify and connect <ArrowRight size={14} /></button></div></form>
        ) : isAzure && step === "configure" ? (
          <form onSubmit={(event) => { event.preventDefault(); if (!azureTenantId.trim() || !azureClientId.trim() || !azureClientSecret) return; setStep("verify"); void onSubmitAzure({ tenant_id: azureTenantId.trim(), client_id: azureClientId.trim(), client_secret: azureClientSecret, ...(azureSubscriptionId.trim() ? { subscription_id: azureSubscriptionId.trim() } : {}) }).then(clearSensitiveState).catch(() => setStep("configure")); }}><p className="hub-dialog-intro">Enter your Microsoft Entra service-principal details. The client secret is sent only to the authenticated backend and is encrypted before storage.</p><label>Tenant ID<input required value={azureTenantId} onChange={(event) => setAzureTenantId(event.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label><label>Application (client) ID<input required value={azureClientId} onChange={(event) => setAzureClientId(event.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label><label>Client secret<div className="hub-password-field"><input required value={azureClientSecret} onChange={(event) => setAzureClientSecret(event.target.value)} type={showSecret ? "text" : "password"} autoComplete="new-password" /><button type="button" onClick={() => setShowSecret((value) => !value)} aria-label={showSecret ? "Hide client secret" : "Show client secret"}>{showSecret ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label><label>Subscription ID <span className="hub-label-note">optional</span><input value={azureSubscriptionId} onChange={(event) => setAzureSubscriptionId(event.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label>{error && <p className="hub-form-error" role="alert">{error}</p>}<div className="hub-dialog-actions"><button type="button" className="hub-secondary-button" onClick={back}>Back</button><button type="submit" className="hub-primary-button" disabled={busy}>Verify and connect <ArrowRight size={14} /></button></div></form>
        ) : isConnectable && step === "verify" ? (
          <div className="hub-verifying"><div className="hub-spinner" /><h3>Verifying with {provider.name}</h3><p>{isAWS ? "UniSora is checking the AWS identity and read-only Cost Explorer access." : "UniSora is checking the API credential with a read-only provider request."} No resources are being changed.</p></div>
        ) : <div className="hub-coming-soon-panel"><p>This provider is not configured for connection yet.</p><span>It will become connectable after a verified backend authorization and verification flow is available.</span><button className="hub-secondary-button" onClick={back}>Back to requirements</button></div>}
      </section>
    </div>
  );
}
