"use client";

import { ArrowUpRight, CheckCircle2, Clock3, MoreHorizontal, Plug, Unplug, RefreshCw } from "lucide-react";
import type { IntegrationConnection, ProviderDefinition } from "@/lib/integrations";
import { categoryLabels, connectionStatus } from "@/lib/integrations";
import { ProviderLogo } from "./ProviderLogo";

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
  const firstConnection = connections[0];
  const status = connectionStatus(firstConnection);
  const isConnected = status === "CONNECTED";
  const isAttention = status === "ERROR" || status === "EXPIRED";
  const isAvailable = provider.availability === "available";
  const isManual = provider.availability === "manual";

  const accountId = (firstConnection as { account_id?: string } | undefined)?.account_id;
  const accountLabel = accountId ? `Account ${accountId}` : "Account Connected";

  return (
    <article className={`service-card ${isConnected ? "is-connected" : ""}`}>
      {/* Top Header: Logo + Status Badge */}
      <div className="service-card-header">
        <div className={`service-logo-wrap provider-${provider.icon}`}>
          <ProviderLogo icon={provider.icon} size={22} />
        </div>

        <div className="service-status-slot">
          {isConnected ? (
            <div className="service-status-pill is-connected">
              <CheckCircle2 size={13} />
              <span>Connected</span>
            </div>
          ) : isAttention ? (
            <div className="service-status-pill is-attention">
              <Clock3 size={13} />
              <span>{status === "EXPIRED" ? "Expired" : "Attention"}</span>
            </div>
          ) : isAvailable ? (
            <div className="service-status-pill is-not-connected">
              <span>Not connected</span>
            </div>
          ) : (
            <div className="service-status-pill is-manual">
              <span>Manual tracking</span>
            </div>
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
          <div className="service-footer-connected">
            <span className="service-account-info" title={accountLabel}>
              {accountLabel}
            </span>

            <div className="footer-connected-actions">
              {isAvailable && (
                <button
                  type="button"
                  className="service-text-link"
                  onClick={() => onView(provider, firstConnection)}
                >
                  <span>View details</span>
                  <ArrowUpRight size={13} className="service-arrow" />
                </button>
              )}

              {(provider.id === "openai" || provider.id === "azure" || provider.id === "anthropic") && onTest && (
                <button
                  type="button"
                  className="service-text-link"
                  onClick={() => onTest(firstConnection)}
                  title="Test connection"
                >
                  <span>Test connection</span>
                </button>
              )}

              <button
                type="button"
                className="service-btn-disconnect"
                onClick={() => onDisconnect(firstConnection)}
                aria-label={`Disconnect ${provider.name}`}
                title={`Disconnect ${provider.name}`}
              >
                <Unplug size={14} />
              </button>
            </div>
          </div>
        ) : isAvailable ? (
          <div className="service-footer-action">
            <button
              type="button"
              className="hub-btn-connect"
              onClick={() => onConnect(provider)}
            >
              <Plug size={14} />
              <span>Connect</span>
            </button>
          </div>
        ) : isManual ? (
          <div className="service-footer-action">
            <button
              type="button"
              className="hub-btn-connect"
              onClick={() => onConnect(provider)}
            >
              <Plug size={14} />
              <span>Track manually</span>
            </button>
          </div>
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
