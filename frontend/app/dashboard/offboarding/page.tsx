"use client";

import { useEffect, useState } from "react";
import {
  UserMinus,
  AlertOctagon,
  CheckCircle2,
  Clock,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  Plus,
  X,
  Key,
} from "lucide-react";
import Link from "next/link";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  getOffboardingSummary,
  listOrphanAccounts,
  revokeAllOrphanAccess,
  listActiveOffboardings,
  listEmployees,
  startEmployeeOffboarding,
  type OffboardingSummary,
  type OrphanAccount,
  type LifecycleEmployeeRecord,
  type EmployeeRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function OffboardingHubPage() {
  const [summary, setSummary] = useState<OffboardingSummary | null>(null);
  const [orphans, setOrphans] = useState<OrphanAccount[]>([]);
  const [activeList, setActiveList] = useState<LifecycleEmployeeRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Start offboarding modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [lastWorkingDate, setLastWorkingDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [starting, setStarting] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const [sum, orph, act, emps] = await Promise.all([
        getOffboardingSummary(),
        listOrphanAccounts(),
        listActiveOffboardings(),
        listEmployees(),
      ]);
      setSummary(sum);
      setOrphans(orph);
      setActiveList(act);
      setEmployees(emps);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load offboarding data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleRevokeOrphan(userId: number, name: string) {
    if (!confirm(`Revoke all remaining SaaS licenses and mark hardware returned for ${name}?`)) return;
    try {
      const res = await revokeAllOrphanAccess(userId);
      setNotice(res.message);
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to revoke orphan access.");
    }
  }

  async function handleStartOffboarding(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedUserId) {
      setError("Please select an employee to offboard.");
      return;
    }
    setStarting(true);
    try {
      await startEmployeeOffboarding(Number(selectedUserId), lastWorkingDate);
      setNotice("Offboarding workflow initiated successfully.");
      setModalOpen(false);
      setSelectedUserId("");
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start offboarding.");
    } finally {
      setStarting(false);
    }
  }

  return (
    <DashboardFrame
      title="Employee Offboarding Automation"
      description="One-click SaaS license revocation, asset recovery, and orphan account security clearance."
      actions={
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setModalOpen(true)}
          >
            <Plus size={14} />
            <span>Initiate Offboarding</span>
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadData}
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

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Active Offboardings</span>
            <Clock size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "var(--foreground, #0f172a)" }}>
            {summary?.active_offboardings || 0}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            Pending clearances in progress
          </div>
        </div>

        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Orphan Accounts</span>
            <AlertOctagon size={18} color="#dc2626" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: (summary?.orphan_accounts_count || 0) > 0 ? "#dc2626" : "#16a34a" }}>
            {summary?.orphan_accounts_count || 0}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            Departed users with lingering licenses
          </div>
        </div>

        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Completed This Month</span>
            <CheckCircle2 size={18} color="#16a34a" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#16a34a" }}>
            {summary?.completed_this_month || 0}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            Fully cleared departures
          </div>
        </div>

        <div style={{ background: "var(--card-bg, #ffffff)", border: "1px solid var(--border-color, #e2e8f0)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>Total Licenses Revoked</span>
            <Key size={18} color="#2563eb" />
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#2563eb" }}>
            {summary?.revoked_licenses_total || 0}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            Seats reclaimed for reuse
          </div>
        </div>
      </div>

      {/* Orphan Accounts Warning Section */}
      {orphans.length > 0 && (
        <div
          style={{
            background: "#fff1f2",
            border: "1px solid #fecdd3",
            borderRadius: "10px",
            padding: "20px",
            marginBottom: "24px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <ShieldAlert size={22} color="#e11d48" />
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#9f1239" }}>
                Security Risk: {orphans.length} Orphan Account{orphans.length > 1 ? "s" : ""} Retaining Company Access
              </h3>
              <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "#be123c" }}>
                These employees have completed departure workflows but still have active SaaS seats or hardware assigned.
              </p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {orphans.map((orph) => (
              <div
                key={orph.user_id}
                style={{
                  background: "#ffffff",
                  border: "1px solid #fecdd3",
                  borderRadius: "8px",
                  padding: "12px 16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: "#0f172a" }}>{orph.name} ({orph.email})</div>
                  <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
                    Offboarded {orph.days_since_offboarding} days ago ({orph.completed_at})
                  </div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "6px" }}>
                    {orph.active_subscriptions.map((s) => (
                      <span
                        key={s.assignment_id}
                        style={{
                          background: "#fee2e2",
                          color: "#991b1b",
                          fontSize: "11px",
                          fontWeight: 500,
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        {s.name} ({s.plan})
                      </span>
                    ))}
                    {orph.active_assets.map((a) => (
                      <span
                        key={a.assignment_id}
                        style={{
                          background: "#fef3c7",
                          color: "#92400e",
                          fontSize: "11px",
                          fontWeight: 500,
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        Asset: {a.name}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={() => handleRevokeOrphan(orph.user_id, orph.name)}
                  style={{ backgroundColor: "#e11d48", borderColor: "#e11d48", fontSize: "12px" }}
                >
                  Revoke All Licenses & Assets
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Offboardings Table */}
      <section className="dashboard-content-card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Active Offboarding Clearances</h2>
            <p className="card-subheading">
              Track multi-department clearance checklists, license un-assignment, and asset recovery in real time.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Loading offboarding statuses…</span>
          </div>
        ) : activeList.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 size={36} color="#16a34a" />}
            title="No active offboarding workflows in progress."
            description="When an employee departure is scheduled, click 'Initiate Offboarding' to automatically generate their access clearance checklist."
          />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--border-color, #e2e8f0)", textAlign: "left", color: "#64748b" }}>
                  <th style={{ padding: "12px 16px" }}>Employee</th>
                  <th style={{ padding: "12px 16px" }}>Department</th>
                  <th style={{ padding: "12px 16px" }}>Last Working Date</th>
                  <th style={{ padding: "12px 16px" }}>Clearance Progress</th>
                  <th style={{ padding: "12px 16px" }}>Status</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {activeList.map((emp) => {
                  const totalTasks = emp.tasks?.length || 0;
                  const completedTasks = emp.tasks?.filter((t) => t.status === "COMPLETED").length || 0;
                  const percent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

                  return (
                    <tr key={emp.id} style={{ borderBottom: "1px solid var(--border-color, #e2e8f0)" }}>
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ fontWeight: 600, color: "var(--foreground, #0f172a)" }}>
                          {emp.display_name || emp.email}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748b" }}>{emp.email}</div>
                      </td>

                      <td style={{ padding: "14px 16px", color: "#64748b" }}>
                        {emp.department_names?.[0] || "General"}
                      </td>

                      <td style={{ padding: "14px 16px", color: "#64748b" }}>
                        {emp.last_working_date || "Not set"}
                      </td>

                      <td style={{ padding: "14px 16px", minWidth: "160px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
                          <span>{completedTasks} / {totalTasks} tasks</span>
                          <span style={{ fontWeight: 600 }}>{percent}%</span>
                        </div>
                        <div style={{ width: "100%", height: "6px", backgroundColor: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                          <div
                            style={{
                              width: `${percent}%`,
                              height: "100%",
                              backgroundColor: percent === 100 ? "#16a34a" : "#f59e0b",
                              transition: "width 0.3s ease",
                            }}
                          />
                        </div>
                      </td>

                      <td style={{ padding: "14px 16px" }}>
                        <StatusBadge variant="warning" size="sm">
                          {emp.status}
                        </StatusBadge>
                      </td>

                      <td style={{ padding: "14px 16px", textAlign: "right" }}>
                        <Link
                          href={`/dashboard/offboarding/${emp.id}`}
                          className="btn btn-sm btn-secondary"
                          style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}
                        >
                          <span>Manage Clearance</span>
                          <ArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Start Offboarding Modal */}
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
              maxWidth: "480px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
              color: "var(--foreground, #0f172a)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <UserMinus size={20} color="#dc2626" />
                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 600 }}>Initiate Employee Offboarding</h3>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "18px" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleStartOffboarding}>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: 0, marginBottom: "20px" }}>
                Initiates security checklist, pulls assigned SaaS software seats, and schedules asset returns.
              </p>

              <div style={{ marginBottom: "16px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Select Employee
                </label>
                <select
                  required
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    backgroundColor: "transparent",
                  }}
                >
                  <option value="">-- Choose employee to offboard --</option>
                  {employees.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.display_name || emp.email} ({emp.email})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: "24px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Last Working Date
                </label>
                <input
                  type="date"
                  required
                  value={lastWorkingDate}
                  onChange={(e) => setLastWorkingDate(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    backgroundColor: "transparent",
                  }}
                />
              </div>

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
                  disabled={starting}
                  style={{ backgroundColor: "#dc2626", borderColor: "#dc2626" }}
                >
                  {starting ? "Starting…" : "Start Offboarding"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardFrame>
  );
}
