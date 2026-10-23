"use client";

import { CheckCircle2, X } from "lucide-react";
import type { AnthropicConnection } from "@/lib/api";
import type { ProviderDefinition } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";

export function AnthropicIntegrationDetails({ provider, connection, onClose }: { provider: ProviderDefinition; connection: AnthropicConnection; onClose: () => void }) {
  return <div className="hub-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="hub-dialog hub-details-dialog" role="dialog" aria-modal="true" aria-labelledby="anthropic-details-title">
      <div className="hub-dialog-header"><div className="hub-details-title"><div className={`hub-provider-icon hub-provider-${provider.icon}`}><ProviderIcon icon={provider.icon} size={20} /></div><div><p className="hub-eyebrow">Connected integration</p><h2 id="anthropic-details-title">{provider.name}</h2></div></div><button className="hub-icon-action" onClick={onClose} aria-label="Close Anthropic details"><X size={18} /></button></div>
      <div className="hub-detail-status"><CheckCircle2 size={17} /><span>{connection.status === "ACTIVE" ? "Connection active" : connection.status}</span><small>Last updated {new Date(connection.updated_at).toLocaleString()}</small></div>
      <div className="hub-detail-grid"><div><span>Connection name</span><strong>{connection.connection_name || "Default connection"}</strong></div><div><span>Model</span><strong>{connection.model || "Not reported"}</strong></div><div><span>Last verified</span><strong>{connection.last_verified_at ? new Date(connection.last_verified_at).toLocaleString() : "Not available"}</strong></div><div><span>Billing balance</span><strong>Not available from provider</strong></div></div>
      <p className="hub-detail-note">The connected Anthropic API key is verified for Messages API access. Anthropic does not expose a remaining-credit balance or organization billing history through the currently configured API flow, so UniSora does not estimate or fabricate those values.</p>
    </section>
  </div>;
}
