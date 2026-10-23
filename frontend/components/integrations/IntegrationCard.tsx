import { ArrowUpRight, CheckCircle2, Clock3, MoreHorizontal, Plug, Unplug } from "lucide-react";
import type { IntegrationConnection, ProviderDefinition } from "@/lib/integrations";
import { categoryLabels, connectionStatus } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

interface IntegrationCardProps {
  provider: ProviderDefinition;
  connections?: IntegrationConnection[];
  onConnect: (provider: ProviderDefinition) => void;
  onDisconnect: (connection: IntegrationConnection) => void;
  onView: (provider: ProviderDefinition, connection?: IntegrationConnection) => void;
  onTest?: (connection: IntegrationConnection) => void;
  onOpenUsage?: (connection: IntegrationConnection) => void;
  onOpenGeminiUsage?: (connection: IntegrationConnection) => void;
  onOpenAzure?: (connection: IntegrationConnection) => void;
}

export function IntegrationCard({
  provider,
  connections = [],
  onConnect,
  onDisconnect,
  onView,
  onTest,
  onOpenUsage,
  onOpenGeminiUsage,
  onOpenAzure,
}: IntegrationCardProps) {
  const status = connectionStatus(connections[0]);
  const connected = status === "CONNECTED";
  const attention = status === "ERROR" || status === "EXPIRED";
  const available = provider.availability === "available";

  return (
    <article className={`hub-integration-card ${connected ? "is-connected" : ""}`}>
      <div className="hub-card-topline">
        <div className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} /></div>
        <span className={`hub-availability ${connected ? "connected" : attention ? "error" : available ? "ready" : "soon"}`}>
          {connected ? <><CheckCircle2 size={13} /> Connected</> : attention ? <><Clock3 size={13} /> {status === "EXPIRED" ? "Expired" : "Needs attention"}</> : available ? "Not connected" : <><Clock3 size={13} /> Coming soon</>}
        </span>
      </div>
      <div className="hub-card-copy">
        <p className="hub-card-category">{categoryLabels[provider.category]}</p>
        <h3>{provider.name}</h3>
        <p>{provider.description}</p>
      </div>
      <div className="hub-capability-list">
        {provider.capabilities.map((capability) => <span key={capability}>{capability}</span>)}
      </div>
      <div className="hub-card-footer">
        {connected || attention ? (
          <>
            <span className="hub-card-meta">{connections.length === 1 ? `Account ${connections[0].account_id || "Connected"}` : `${connections.length} accounts connected`}</span>
            {available && <button className="hub-text-button" onClick={() => onView(provider, connections[0])}>View details <ArrowUpRight size={14} /></button>}
            {(provider.id === "openai" || provider.id === "azure" || provider.id === "anthropic") && onTest && <button className="hub-text-button" onClick={() => onTest(connections[0])}>{attention ? "Retry connection" : "Test connection"}</button>}
            <button className="hub-icon-action danger" onClick={() => onDisconnect(connections[0])} aria-label={`Disconnect ${provider.name}`} title={`Disconnect ${provider.name}`}>
              <Unplug size={16} />
            </button>
          </>
        ) : available ? (
          <button className="hub-primary-button small" onClick={() => onConnect(provider)}><Plug size={15} /> Connect</button>
        ) : (
          <span className="hub-card-meta"><MoreHorizontal size={15} /> Provider roadmap</span>
        )}
      </div>
    </article>
  );
}
