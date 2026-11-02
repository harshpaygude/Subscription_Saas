"use client";

import { useEffect, useState } from "react";
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Check,
  RefreshCw,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { listAlerts, markAlertRead, resolveAlert, type AlertRecord } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AlertsPage() {
  const [items, setItems] = useState<AlertRecord[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const alerts = await listAlerts({ resolved: false });
      setItems(alerts);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load alerts.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleMarkRead(id: number) {
    try {
      await markAlertRead(id);
      setNotice("Alert marked as read.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update alert status.");
    }
  }

  async function handleResolve(id: number) {
    try {
      await resolveAlert(id);
      setNotice("Alert resolved.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not resolve alert.");
    }
  }

  return (
    <DashboardFrame
      title="Alerts & Notifications"
      description="System warnings, upcoming subscription renewals, license thresholds, and provider sync alerts."
      actions={
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={load}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? "spin-animation" : ""} />
          <span>Refresh</span>
        </button>
      }
    >
      {notice && (
        <div className="alert-notice alert-success mb-4" role="status">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>×</button>
        </div>
      )}

      {error && (
        <div className="alert-notice alert-danger mb-4" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      <section className="dashboard-content-card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Active Workspace Notifications</h2>
            <p className="card-subheading">
              Generated automatically from verified contract renewals and backend event telemetry.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Scanning notifications…</span>
          </div>
        ) : !items || items.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 size={32} className="text-success" />}
            title="All clear! No active alerts."
            description="Your organization has no pending contract expirations or integration warnings."
          />
        ) : (
          <div className="alerts-list-stack">
            {items.map((item) => {
              const severity = (item.severity || "").toLowerCase();
              const isWarning = severity === "warning" || severity === "high";
              const isError = severity === "error" || severity === "critical";

              return (
                <article
                  key={item.id}
                  className={`alert-card-item ${item.is_read ? "is-read" : "is-unread"}`}
                >
                  <div className="alert-card-icon-col">
                    {isError ? (
                      <AlertTriangle size={20} className="text-danger" />
                    ) : isWarning ? (
                      <AlertTriangle size={20} className="text-warning" />
                    ) : (
                      <Info size={20} className="text-info" />
                    )}
                  </div>

                  <div className="alert-card-body">
                    <div className="alert-meta-top">
                      <StatusBadge
                        variant={isError ? "error" : isWarning ? "warning" : "info"}
                        size="sm"
                      >
                        {item.severity}
                      </StatusBadge>
                      <span className="badge-tag">{item.category}</span>
                      <span className="alert-time">
                        <Clock size={12} className="inline mr-1" />
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>

                    <h3 className="alert-title">{item.title}</h3>
                    <p className="alert-desc">{item.description}</p>
                  </div>

                  <div className="alert-card-actions">
                    {!item.is_read && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => void handleMarkRead(item.id)}
                      >
                        <Check size={13} />
                        <span>Mark Read</span>
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => void handleResolve(item.id)}
                    >
                      <CheckCircle2 size={13} />
                      <span>Resolve</span>
                    </button>
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
