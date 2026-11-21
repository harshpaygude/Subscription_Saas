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
  Mail,
  MessageSquare,
  Settings,
  Send,
  X,
  ShieldAlert,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  listAlerts,
  markAlertRead,
  resolveAlert,
  getNotificationPreferences,
  updateNotificationPreferences,
  sendTestNotification,
  dispatchDueAlerts,
  type AlertRecord,
  type NotificationPreference,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AlertsPage() {
  const [items, setItems] = useState<AlertRecord[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<string>("ALL");

  // Notification Preferences Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [prefs, setPrefs] = useState<NotificationPreference | null>(null);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [waEnabled, setWaEnabled] = useState(false);
  const [waNumber, setWaNumber] = useState("");
  const [notifyMilestones, setNotifyMilestones] = useState<string[]>(["30", "7", "1"]);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [testStatus, setTestStatus] = useState<string | null>(null);

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

  async function openPreferences() {
    try {
      const p = await getNotificationPreferences();
      setPrefs(p);
      setEmailEnabled(p.email_enabled);
      setWaEnabled(p.whatsapp_enabled);
      setWaNumber(p.whatsapp_number || "");
      setNotifyMilestones(p.notify_days_before ? p.notify_days_before.split(",") : ["30", "7", "1"]);
      setTestStatus(null);
      setModalOpen(true);
    } catch (e) {
      setError("Failed to load notification settings.");
    }
  }

  async function handleSavePreferences(e: React.FormEvent) {
    e.preventDefault();
    setSavingPrefs(true);
    try {
      await updateNotificationPreferences({
        email_enabled: emailEnabled,
        whatsapp_enabled: waEnabled,
        whatsapp_number: waNumber.trim() || null,
        notify_days_before: notifyMilestones.join(","),
      });
      setNotice("Notification settings saved successfully.");
      setModalOpen(false);
    } catch (e) {
      setError("Could not save settings.");
    } finally {
      setSavingPrefs(false);
    }
  }

  async function handleSendTest(channel: "email" | "whatsapp") {
    setTestStatus("Sending test notification…");
    try {
      const res = await sendTestNotification({ channel });
      const detail = res.results[channel];
      setTestStatus(detail ? detail.message : "Test notification sent.");
    } catch (e) {
      setTestStatus(e instanceof Error ? e.message : "Failed to send test.");
    }
  }

  async function handleDispatchDue() {
    try {
      const res = await dispatchDueAlerts();
      setNotice(`Dispatched ${res.dispatched_count} alerts via active channels.`);
    } catch (e) {
      setError("Failed to dispatch notifications.");
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

  const filteredItems = items?.filter((item) => {
    if (activeCategory === "ALL") return true;
    return (item.category || "").toUpperCase() === activeCategory;
  });

  const renewalCount = items?.filter((i) => (i.category || "").toLowerCase() === "renewal").length || 0;

  return (
    <DashboardFrame
      title="Alerts & Smart Notifications"
      description="Automated renewal notices (30d, 7d, 1d), security warnings, and multi-channel dispatch."
      actions={
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={openPreferences}
          >
            <Settings size={14} />
            <span>Channels (Email/WhatsApp)</span>
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={load}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin-animation" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      }
    >
      {notice && (
        <div className="alert-notice alert-success mb-4" role="status" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")} style={{ background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {error && (
        <div className="alert-notice alert-danger mb-4" role="alert" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{error}</span>
          <button type="button" onClick={() => setError("")} style={{ background: "none", border: "none", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", borderBottom: "1px solid var(--border-color, #e2e8f0)", paddingBottom: "8px" }}>
        {["ALL", "RENEWAL", "SECURITY", "BUDGET"].map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            className={`btn btn-sm ${activeCategory === cat ? "btn-primary" : "btn-secondary"}`}
            style={{ textTransform: "capitalize" }}
          >
            {cat === "ALL" ? "All Alerts" : cat.toLowerCase()}
            {cat === "RENEWAL" && renewalCount > 0 && (
              <span style={{ marginLeft: "6px", background: "#ef4444", color: "#fff", padding: "1px 6px", borderRadius: "10px", fontSize: "11px" }}>
                {renewalCount}
              </span>
            )}
          </button>
        ))}
      </div>

      <section className="dashboard-content-card">
        <div className="card-header-bar" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 className="card-heading">Active Workspace Notifications</h2>
            <p className="card-subheading">
              Configured with smart 30-day, 7-day, and 1-day advance warning triggers.
            </p>
          </div>
          {renewalCount > 0 && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={handleDispatchDue}
              title="Dispatches notifications to your enabled Email & WhatsApp channels"
            >
              <Send size={13} style={{ marginRight: "4px" }} />
              Dispatch Due Notices
            </button>
          )}
        </div>

        {loading ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Scanning notifications…</span>
          </div>
        ) : !filteredItems || filteredItems.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 size={32} className="text-success" />}
            title="All clear! No pending alerts in this category."
            description="Your organization has no contract expirations or active warnings."
          />
        ) : (
          <div className="alerts-list-stack">
            {filteredItems.map((item) => {
              const severity = (item.severity || "").toLowerCase();
              const isWarning = severity === "warning" || severity === "high";
              const isError = severity === "error" || severity === "critical";

              return (
                <article
                  key={item.id}
                  className={`alert-card-item ${item.is_read ? "is-read" : "is-unread"}`}
                  style={{
                    display: "flex",
                    gap: "16px",
                    padding: "16px",
                    borderBottom: "1px solid var(--border-color, #e2e8f0)",
                    alignItems: "flex-start",
                  }}
                >
                  <div className="alert-card-icon-col" style={{ marginTop: "4px" }}>
                    {isError ? (
                      <AlertTriangle size={22} color="#dc2626" />
                    ) : isWarning ? (
                      <Clock size={22} color="#f59e0b" />
                    ) : (
                      <Info size={22} color="#3b82f6" />
                    )}
                  </div>

                  <div className="alert-card-body" style={{ flex: 1 }}>
                    <div className="alert-meta-top" style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <StatusBadge
                        variant={isError ? "error" : isWarning ? "warning" : "info"}
                        size="sm"
                      >
                        {item.severity}
                      </StatusBadge>
                      <span style={{ fontSize: "12px", textTransform: "uppercase", color: "#64748b", fontWeight: 600 }}>
                        {item.category}
                      </span>
                      {item.provider && (
                        <span style={{ fontSize: "12px", background: "rgba(0,0,0,0.05)", padding: "1px 6px", borderRadius: "4px" }}>
                          {item.provider}
                        </span>
                      )}
                    </div>

                    <h3 style={{ fontSize: "15px", fontWeight: 600, margin: "2px 0 6px 0", color: "var(--foreground, #0f172a)" }}>
                      {item.title}
                    </h3>

                    <p style={{ fontSize: "13px", color: "var(--muted-foreground, #64748b)", margin: 0, lineHeight: 1.5 }}>
                      {item.description}
                    </p>
                  </div>

                  <div className="alert-card-actions" style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    {!item.is_read && (
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        onClick={() => handleMarkRead(item.id)}
                        title="Mark as read"
                      >
                        Read
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleResolve(item.id)}
                      title="Mark as resolved"
                    >
                      <Check size={14} style={{ marginRight: "4px" }} />
                      Resolve
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Notification Preferences Modal */}
      {modalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px",
          }}
        >
          <div
            style={{
              backgroundColor: "var(--card-bg, #ffffff)",
              borderRadius: "12px",
              padding: "28px",
              width: "100%",
              maxWidth: "520px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
              color: "var(--foreground, #0f172a)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Bell size={20} color="#2563eb" />
                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 600 }}>Smart Notification Channels</h3>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "18px" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSavePreferences}>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: 0, marginBottom: "20px" }}>
                Configure real-time alerts before software subscriptions auto-renew or contracts expire.
              </p>

              {/* Email channel */}
              <div style={{ padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color, #e2e8f0)", marginBottom: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Mail size={16} color="#2563eb" />
                    <strong>Email Notifications</strong>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailEnabled}
                    onChange={(e) => setEmailEnabled(e.target.checked)}
                    style={{ width: "18px", height: "18px", cursor: "pointer" }}
                  />
                </div>
                <p style={{ fontSize: "12px", color: "#64748b", margin: "6px 0 10px 0" }}>
                  Sends HTML renewal summaries to your registered account email.
                </p>
                {emailEnabled && (
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleSendTest("email")}
                    style={{ fontSize: "11px", padding: "4px 8px" }}
                  >
                    Send Test Email
                  </button>
                )}
              </div>

              {/* WhatsApp channel */}
              <div style={{ padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color, #e2e8f0)", marginBottom: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <MessageSquare size={16} color="#16a34a" />
                    <strong>WhatsApp Alerts</strong>
                  </div>
                  <input
                    type="checkbox"
                    checked={waEnabled}
                    onChange={(e) => setWaEnabled(e.target.checked)}
                    style={{ width: "18px", height: "18px", cursor: "pointer" }}
                  />
                </div>
                <p style={{ fontSize: "12px", color: "#64748b", margin: "6px 0 10px 0" }}>
                  Instant WhatsApp text when renewals enter urgent milestone stages.
                </p>
                {waEnabled && (
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 500, display: "block", marginBottom: "4px" }}>
                      Phone Number (with Country Code)
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      value={waNumber}
                      onChange={(e) => setWaNumber(e.target.value)}
                      placeholder="+91 98765 43210"
                      style={{ width: "100%", padding: "6px 10px", fontSize: "13px", marginBottom: "8px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                    />
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleSendTest("whatsapp")}
                      disabled={!waNumber.trim()}
                      style={{ fontSize: "11px", padding: "4px 8px" }}
                    >
                      Send Test WhatsApp
                    </button>
                  </div>
                )}
              </div>

              {/* Milestones */}
              <div style={{ marginBottom: "20px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Alert Milestones:
                </label>
                <div style={{ display: "flex", gap: "16px", fontSize: "13px" }}>
                  {[
                    { label: "30 Days Prior", val: "30" },
                    { label: "7 Days Prior", val: "7" },
                    { label: "1 Day Prior", val: "1" },
                  ].map((m) => (
                    <label key={m.val} style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={notifyMilestones.includes(m.val)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setNotifyMilestones([...notifyMilestones, m.val]);
                          } else {
                            setNotifyMilestones(notifyMilestones.filter((x) => x !== m.val));
                          }
                        }}
                      />
                      <span>{m.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {testStatus && (
                <div style={{ padding: "8px 12px", background: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", borderRadius: "6px", fontSize: "12px", marginBottom: "16px" }}>
                  {testStatus}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={savingPrefs}
                >
                  {savingPrefs ? "Saving…" : "Save Preferences"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}
