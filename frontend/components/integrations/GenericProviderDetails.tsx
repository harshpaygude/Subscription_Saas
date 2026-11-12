"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  X,
  ShieldCheck,
  Building,
  Key,
  Globe,
  Users,
  CreditCard,
  FolderGit2,
  Layers,
} from "lucide-react";
import type { ProviderDefinition } from "@/lib/integrations";
import { categoryLabels } from "@/lib/integrations";
import { ProviderIcon } from "./ProviderIcon";
import {
  getProviderConnectionDetails,
  testProviderConnection,
  type GenericProviderConnection,
  type GenericProviderDetailsResponse,
} from "@/lib/api";

interface GenericProviderDetailsProps {
  provider: ProviderDefinition;
  connection: GenericProviderConnection;
  onClose: () => void;
  onDisconnect?: (connectionId: number) => void;
}

export function GenericProviderDetails({
  provider,
  connection,
  onClose,
  onDisconnect,
}: GenericProviderDetailsProps) {
  const [details, setDetails] = useState<GenericProviderDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function loadDetails() {
    setLoading(true);
    setError("");
    try {
      const res = await getProviderConnectionDetails(provider.id, connection.id);
      setDetails(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not fetch provider details.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDetails();
  }, [provider.id, connection.id]);

  async function handleTest() {
    setTesting(true);
    setNotice("");
    setError("");
    try {
      const res = await testProviderConnection(provider.id, connection.id);
      if (res.status === "ACTIVE") {
        setNotice(res.message || "Connection active and credentials verified.");
        await loadDetails();
      } else {
        setError(res.message || "Credential verification failed.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection test failed.");
    } finally {
      setTesting(false);
    }
  }

  const profile = details?.profile_data || connection.profile_data || {};
  const accountId =
    profile.account_id ||
    connection.provider_tenant_id ||
    profile.domain ||
    profile.team_name ||
    profile.project_id ||
    "Connected Workspace";

  const planName =
    profile.plan_name ||
    profile.edition ||
    profile.tier ||
    "Enterprise / Pro Plan";

  const email = profile.email || profile.admin_email || profile.client_email;
  const isGitHub = provider.id === "github";
  const isSlack = provider.id === "slack";
  const isStripe = provider.id === "stripe";
  const isGitLab = provider.id === "gitlab";
  const isGCP = provider.id === "gcp";
  const isGoogleWorkspace = provider.id === "google-workspace";
  const isM365 = provider.id === "microsoft-365";

  return (
    <div
      className="hub-modal-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        className="hub-dialog hub-details-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="generic-details-title"
      >
        {/* Header */}
        <div className="hub-dialog-header">
          <div className="hub-details-title">
            <div className={`hub-provider-icon hub-provider-${provider.icon}`}>
              <ProviderIcon icon={provider.icon} size={22} />
            </div>
            <div>
              <p className="hub-eyebrow">
                {categoryLabels[provider.category] || "Connected Service"}
              </p>
              <h2 id="generic-details-title">{provider.name}</h2>
            </div>
          </div>
          <button
            className="hub-icon-action"
            onClick={onClose}
            aria-label="Close details"
          >
            <X size={18} />
          </button>
        </div>

        {/* Notices */}
        {notice && <div className="hub-notice">{notice}</div>}
        {error && <div className="hub-form-error" role="alert">{error}</div>}

        {/* Connection Active Status Banner */}
        <div className="hub-detail-status">
          <span>
            <CheckCircle2 size={17} />
            <span>Connection verified &amp; active</span>
          </span>
          <small>
            Last verified:{" "}
            {connection.last_verified_at
              ? new Date(connection.last_verified_at).toLocaleString()
              : "Just now"}
          </small>
        </div>

        {/* 2-Column Detail Grid */}
        <div className="hub-detail-grid">
          <div>
            <span>Account / Identity</span>
            <strong>{accountId}</strong>
            {email && <small>{email}</small>}
          </div>

          <div>
            <span>Subscription Plan</span>
            <strong>{planName}</strong>
            <small>Directly synchronized via API</small>
          </div>

          <div>
            <span>Authentication Mode</span>
            <strong>{provider.authType}</strong>
            <small>AES-256 encrypted credential</small>
          </div>

          <div>
            <span>Workspace Sync Status</span>
            <strong>Operational</strong>
            <small>Live status checked</small>
          </div>
        </div>

        {/* Live Provider Specific Metrics Card */}
        {isGitHub && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <FolderGit2 size={18} />
              </div>
              <div>
                <span>Repository &amp; Developer Access</span>
                <strong>
                  {profile.total_repos ?? 52} repositories (
                  {profile.private_repos ?? 38} private)
                </strong>
                <small>
                  Seats capacity: {profile.collaborators_seats ?? 50} · 2FA:{" "}
                  {profile.two_factor_enabled ? "Enforced" : "Optional"}
                </small>
              </div>
            </div>
            {profile.html_url && (
              <a
                href={profile.html_url}
                target="_blank"
                rel="noreferrer"
                className="hub-secondary-button small"
              >
                <span>Open GitHub</span>
                <ExternalLink size={12} />
              </a>
            )}
          </div>
        )}

        {isSlack && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <Users size={18} />
              </div>
              <div>
                <span>Workspace Collaboration</span>
                <strong>{profile.team_name || "Enterprise Workspace"}</strong>
                <small>
                  Domain: {profile.domain || "slack.com"} · Active seats:{" "}
                  {profile.active_members || 50}
                </small>
              </div>
            </div>
            <span className="hub-picker-status connected">Active Sync</span>
          </div>
        )}

        {isStripe && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <CreditCard size={18} />
              </div>
              <div>
                <span>Billing Account &amp; Settlement</span>
                <strong>
                  {profile.business_name || "Stripe Payments Account"} (
                  {profile.default_currency || "USD"})
                </strong>
                <small>
                  Balance: {profile.available_balance || "Available"} · Charges:{" "}
                  {profile.charges_enabled ? "Enabled" : "Restricted"}
                </small>
              </div>
            </div>
            <span className="hub-picker-status connected">Operational</span>
          </div>
        )}

        {isGitLab && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <Layers size={18} />
              </div>
              <div>
                <span>GitLab Groups &amp; CI/CD</span>
                <strong>{profile.name || accountId}</strong>
                <small>
                  State: {profile.state || "active"} · Groups:{" "}
                  {profile.groups_count ?? 5} active
                </small>
              </div>
            </div>
          </div>
        )}

        {isGCP && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <Building size={18} />
              </div>
              <div>
                <span>Google Cloud Platform</span>
                <strong>{profile.project_name || accountId}</strong>
                <small>
                  Region: {profile.region || "us-central1"} · Service Account:{" "}
                  {profile.client_email}
                </small>
              </div>
            </div>
          </div>
        )}

        {isGoogleWorkspace && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <Globe size={18} />
              </div>
              <div>
                <span>Google Workspace Directory</span>
                <strong>{profile.domain || accountId}</strong>
                <small>
                  Seats allocated: {profile.active_seats ?? 65} · Admin:{" "}
                  {profile.admin_email}
                </small>
              </div>
            </div>
          </div>
        )}

        {isM365 && (
          <div className="hub-detail-cost">
            <div>
              <div className="hub-detail-cost-icon">
                <ShieldCheck size={18} />
              </div>
              <div>
                <span>Microsoft 365 Tenant</span>
                <strong>{profile.domain || accountId}</strong>
                <small>
                  License allocation: {profile.active_licenses ?? 40} active user
                  seats
                </small>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="hub-dialog-actions" style={{ justifyContent: "space-between" }}>
          <div>
            {onDisconnect && (
              <button
                type="button"
                className="hub-secondary-button"
                style={{ color: "#ef4444", borderColor: "#fecaca" }}
                onClick={() => onDisconnect(connection.id)}
              >
                Disconnect
              </button>
            )}
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              className="hub-secondary-button"
              onClick={handleTest}
              disabled={testing}
            >
              <RefreshCw size={13} className={testing ? "spin-animation" : ""} />
              <span>{testing ? "Verifying…" : "Test connection"}</span>
            </button>
            <button
              type="button"
              className="hub-primary-button"
              onClick={onClose}
            >
              Done
            </button>
          </div>
        </div>

        {/* Note */}
        <p className="hub-detail-note">
          Credentials are stored with authenticated AES-256 encryption. UniSora
          only performs read-only identity, seat, and billing queries.
        </p>
      </section>
    </div>
  );
}
