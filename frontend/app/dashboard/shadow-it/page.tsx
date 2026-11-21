"use client";

import { useEffect, useState, useRef } from "react";
import {
  ShieldAlert,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  Ban,
  Check,
  Trash2,
  RefreshCw,
  Sparkles,
  FileText,
  DollarSign,
  Layers,
  Info,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  getShadowItStats,
  listShadowItEntries,
  uploadBankStatementCsv,
  runDemoShadowItScan,
  approveShadowItEntry,
  blockShadowItEntry,
  deleteShadowItEntry,
  type ShadowItEntry,
  type ShadowItStats,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function ShadowItPage() {
  const [stats, setStats] = useState<ShadowItStats | null>(null);
  const [entries, setEntries] = useState<ShadowItEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [activeTab, setActiveTab] = useState<string>("ALL");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadData() {
    setLoading(true);
    try {
      const [s, list] = await Promise.all([getShadowItStats(), listShadowItEntries()]);
      setStats(s);
      setEntries(list);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Shadow IT telemetry.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleFileUpload(file: File) {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const result = await uploadBankStatementCsv(file);
      setNotice(
        `Discovered ${result.matched_vendors_count} SaaS tools across ${result.processed_transactions} transactions (${result.currency} ${result.total_monthly_spend_discovered.toLocaleString()}/mo spend).`
      );
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload and analysis failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDemoScan() {
    setUploading(true);
    setError("");
    try {
      const result = await runDemoShadowItScan();
      setNotice(
        `Demo Scan Complete: Found ${result.matched_vendors_count} SaaS tools (${result.currency} ${result.total_monthly_spend_discovered.toLocaleString()}/mo spend) including unapproved AI & cloud subscriptions!`
      );
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Demo scan failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleApprove(id: number) {
    try {
      await approveShadowItEntry(id);
      setNotice("Tool marked as Approved.");
      await loadData();
    } catch (e) {
      setError("Could not approve tool.");
    }
  }

  async function handleBlock(id: number) {
    try {
      await blockShadowItEntry(id);
      setNotice("Tool flagged as BLOCKED / Unauthorized.");
      await loadData();
    } catch (e) {
      setError("Could not block tool.");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to remove this discovered tool record?")) return;
    try {
      await deleteShadowItEntry(id);
      setNotice("Record removed.");
      await loadData();
    } catch (e) {
      setError("Could not delete record.");
    }
  }

  const filteredEntries = entries?.filter((entry) => {
    if (activeTab === "ALL") return true;
    if (activeTab === "HIGH_RISK") return entry.risk_level === "HIGH";
    return entry.status === activeTab;
  });

  return (
    <DashboardFrame
      title="Shadow IT Discovery"
      description="Scan company bank statements and credit card exports to identify unauthorized SaaS purchases."
      actions={
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleDemoScan}
            disabled={uploading}
            title="Scan realistic corporate credit card export"
          >
            <Sparkles size={14} color="#f59e0b" />
            <span>{uploading ? "Analyzing…" : "Scan Demo Statement"}</span>
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <UploadCloud size={14} />
            <span>Upload Bank CSV</span>
          </button>
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files?.[0]) void handleFileUpload(e.target.files[0]);
            }}
          />
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

      {/* KPI Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Unmanaged Spend</span>
            <DollarSign size={18} color="#ef4444" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "var(--foreground, #0f172a)" }}>
            ₹{stats?.total_monthly_spend?.toLocaleString() || "0"}
            <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 400 }}> / month</span>
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            ₹{((stats?.total_monthly_spend || 0) * 12).toLocaleString()} annualized leak
          </div>
        </div>

        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Discovered Vendors</span>
            <Layers size={18} color="#3b82f6" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "var(--foreground, #0f172a)" }}>
            {stats?.vendor_count || 0}
            <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 400 }}> detected</span>
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            {stats?.discovered_count || 0} pending review
          </div>
        </div>

        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>High Risk Tools</span>
            <ShieldAlert size={18} color="#dc2626" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#dc2626" }}>
            {stats?.high_risk_count || 0}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            Cloud, API & Payment gateways
          </div>
        </div>

        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Approved / Governed</span>
            <CheckCircle2 size={18} color="#16a34a" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#16a34a" }}>
            {stats?.approved_count || 0}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            {stats?.blocked_count || 0} blocked / restricted
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", borderBottom: "1px solid var(--border-color, #e2e8f0)", paddingBottom: "8px" }}>
        {[
          { key: "ALL", label: "All Detected" },
          { key: "DISCOVERED", label: "Pending Review" },
          { key: "HIGH_RISK", label: "High Risk" },
          { key: "APPROVED", label: "Approved" },
          { key: "BLOCKED", label: "Blocked" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`btn btn-sm ${activeTab === tab.key ? "btn-primary" : "btn-secondary"}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Table Card */}
      <section className="dashboard-content-card">
        <div className="card-header-bar" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 className="card-heading">Detected Unmanaged Subscriptions</h2>
            <p className="card-subheading">
              SaaS tools matched from credit card statements against our 40+ vendor intelligence database.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Analyzing transactions…</span>
          </div>
        ) : !filteredEntries || filteredEntries.length === 0 ? (
          <EmptyState
            icon={<ShieldAlert size={36} color="#3b82f6" />}
            title="No Shadow IT records found."
            description="Upload a corporate bank statement CSV or click 'Scan Demo Statement' above to uncover unauthorized software spending."
          />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--border-color, #e2e8f0)", textAlign: "left", color: "#64748b" }}>
                  <th style={{ padding: "12px 16px" }}>Vendor & Tool</th>
                  <th style={{ padding: "12px 16px" }}>Category</th>
                  <th style={{ padding: "12px 16px" }}>Monthly Spend</th>
                  <th style={{ padding: "12px 16px" }}>Risk Level</th>
                  <th style={{ padding: "12px 16px" }}>Status</th>
                  <th style={{ padding: "12px 16px" }}>Activity</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry) => {
                  const isHigh = entry.risk_level === "HIGH";
                  const isMed = entry.risk_level === "MEDIUM";
                  const isApproved = entry.status === "APPROVED";
                  const isBlocked = entry.status === "BLOCKED";

                  return (
                    <tr
                      key={entry.id}
                      style={{
                        borderBottom: "1px solid var(--border-color, #e2e8f0)",
                        backgroundColor: isBlocked ? "rgba(239, 68, 68, 0.03)" : "transparent",
                      }}
                    >
                      <td style={{ padding: "14px 16px", fontWeight: 600, color: "var(--foreground, #0f172a)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <FileText size={16} color="#64748b" />
                          <span>{entry.vendor_name}</span>
                        </div>
                      </td>

                      <td style={{ padding: "14px 16px", color: "#64748b" }}>
                        {entry.category}
                      </td>

                      <td style={{ padding: "14px 16px", fontWeight: 600 }}>
                        ₹{Number(entry.monthly_amount).toLocaleString()}
                        <div style={{ fontSize: "11px", fontWeight: 400, color: "#64748b" }}>
                          ₹{(Number(entry.monthly_amount) * 12).toLocaleString()} / yr
                        </div>
                      </td>

                      <td style={{ padding: "14px 16px" }}>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "11px",
                            fontWeight: 600,
                            backgroundColor: isHigh ? "#fee2e2" : isMed ? "#fef3c7" : "#dcfce7",
                            color: isHigh ? "#b91c1c" : isMed ? "#b45309" : "#15803d",
                          }}
                        >
                          {entry.risk_level} RISK
                        </span>
                      </td>

                      <td style={{ padding: "14px 16px" }}>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "11px",
                            fontWeight: 600,
                            backgroundColor: isApproved ? "#dcfce7" : isBlocked ? "#fee2e2" : "#f1f5f9",
                            color: isApproved ? "#15803d" : isBlocked ? "#b91c1c" : "#475569",
                          }}
                        >
                          {entry.status}
                        </span>
                      </td>

                      <td style={{ padding: "14px 16px", fontSize: "12px", color: "#64748b" }}>
                        {entry.transaction_count} txn{entry.transaction_count > 1 ? "s" : ""}
                        {entry.last_seen && <div>Last: {entry.last_seen}</div>}
                      </td>

                      <td style={{ padding: "14px 16px", textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                          {!isApproved && (
                            <button
                              type="button"
                              className="btn btn-sm btn-secondary"
                              onClick={() => handleApprove(entry.id)}
                              title="Approve as official company software"
                              style={{ padding: "4px 8px", fontSize: "11px" }}
                            >
                              <Check size={12} color="#16a34a" style={{ marginRight: "3px" }} />
                              Approve
                            </button>
                          )}
                          {!isBlocked && (
                            <button
                              type="button"
                              className="btn btn-sm btn-secondary"
                              onClick={() => handleBlock(entry.id)}
                              title="Block and restrict software usage"
                              style={{ padding: "4px 8px", fontSize: "11px" }}
                            >
                              <Ban size={12} color="#dc2626" style={{ marginRight: "3px" }} />
                              Block
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btn-sm btn-secondary"
                            onClick={() => handleDelete(entry.id)}
                            title="Delete entry"
                            style={{ padding: "4px 6px" }}
                          >
                            <Trash2 size={12} color="#64748b" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </DashboardFrame>
  );
}
