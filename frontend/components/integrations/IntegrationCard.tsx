"use client";

import { ArrowUpRight, CheckCircle2, Clock3, MoreHorizontal, Plug, Unplug, RefreshCw } from "lucide-react";
import type { IntegrationConnection, ProviderDefinition } from "@/lib/integrations";
import { categoryLabels, connectionStatus } from "@/lib/integrations";
import { ProviderLogo } from "./ProviderLogo";
import { StatusBadge } from "@/components/ui/StatusBadge";

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
}: IntegrationCardProps) {
  const status = connectionStatus(connections[0]);
  const isConnected = status === "CONNECTED";
  const isAttention = status === "ERROR" || status === "EXPIRED";
  const isAvailable = provider.availability === "available";
  const isManual = provider.availability === "manual";

  return (
    <article className={`service-card ${isConnected ? "is-connected" : ""}`}>
      {/* Top Header: Logo + Status Badge */}
      <div className="service-card-header">
        <div className={`service-logo-wrap provider-${provider.icon}`}>
          <ProviderLogo icon={provider.icon} />
        </div>

        <div className="service-status-slot">
          {isConnected ? (
            <StatusBadge variant="success" size="sm">
              Connected
            </StatusBadge>
          ) : isAttention ? (
            <StatusBadge variant="warning" size="sm">
              {status === "EXPIRED" ? "Expired" : "Attention"}
            </StatusBadge>
          ) : isAvailable ? (
            <StatusBadge variant="neutral" size="sm" dot={false}>
              Ready to connect
            </StatusBadge>
          ) : (
            <StatusBadge variant="neutral" size="sm" dot={false}>
              Manual tracking
            </StatusBadge>
          )}
        </div>
      </div>

      {/* Body: Category, Name, Description */}
      <div className="service-card-body">
        <span className="service-category-tag">{categoryLabels[provider.category] || provider.category}</span>
        <h3 className="service-name">{provider.name}</h3>
        <p className="service-description">{provider.description}</p>
      </div>

      {/* Capabilities Badges */}
      <div className="service-capabilities">
        {provider.capabilities.slice(0, 3).map((cap) => (
          <span key={cap} className="capability-pill">
            {cap}
          </span>
        ))}
        {provider.capabilities.length > 3 && (
          <span className="capability-pill-more">+{provider.capabilities.length - 3}</span>
        )}
      </div>

      {/* Card Footer Actions */}
      <div className="service-card-footer">
        {isConnected || isAttention ? (
          <div className="footer-connected-actions">
            {isAvailable && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onView(provider, connections[0])}
              >
                <span>Details</span>
                <ArrowUpRight size={13} />
              </button>
            )}

            {(provider.id === "openai" || provider.id === "azure" || provider.id === "anthropic") && onTest && (
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => onTest(connections[0])}
                title="Test API Key Connection"
              >
                <RefreshCw size={13} />
                <span>Test</span>
              </button>
            )}

            <button
              type="button"
              className="btn btn-danger-icon btn-sm"
              onClick={() => onDisconnect(connections[0])}
              aria-label={`Disconnect ${provider.name}`}
              title={`Disconnect ${provider.name}`}
            >
              <Unplug size={15} />
            </button>
          </div>
        ) : isAvailable || isManual ? (
          <button
            type="button"
            className="btn btn-primary btn-sm btn-full"
            onClick={() => onConnect(provider)}
          >
            <Plug size={15} />
            <span>{isManual ? "Track Manually" : "Connect Provider"}</span>
          </button>
        ) : (
          <span className="service-unsupported-note">
            <MoreHorizontal size={14} />
            <span>Managed Service</span>
          </span>
        )}
      </div>
    </article>
  );
}
