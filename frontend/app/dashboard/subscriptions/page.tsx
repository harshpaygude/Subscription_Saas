"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  CalendarClock,
  Plus,
  X,
  UserPlus,
  UserMinus,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  WalletCards,
  Building,
  Upload,
  Download,
  Sparkles,
  Zap,
  Clock,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import { ImportSubscriptionsModal } from "@/components/dashboard/ImportSubscriptionsModal";
import {
  assignSubscription,
  cancelSubscription,
  createSubscription,
  createSubscriptionLicense,
  listEmployees,
  listSubscriptionAssignments,
  listSubscriptionLicenses,
  listSubscriptions,
  releaseSubscriptionAssignment,
  type EmployeeRecord,
  type SubscriptionAssignmentRecord,
  type SubscriptionLicenseRecord,
  type SubscriptionRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function SubscriptionsPage() {
  const [items, setItems] = useState<SubscriptionRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<SubscriptionRecord | null>(null);
  const [saving, setSaving] = useState(false);
  const [licenses, setLicenses] = useState<SubscriptionLicenseRecord[]>([]);
  const [assignments, setAssignments] = useState<SubscriptionAssignmentRecord[]>([]);
  const [seatSaving, setSeatSaving] = useState(false);
  const [assignmentSaving, setAssignmentSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [showImportModal, setShowImportModal] = useState(false);

  function getRenewalCountdown(renewalDateStr: string | null) {
    if (!renewalDateStr) return null;
    const renewal = new Date(renewalDateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    renewal.setHours(0, 0, 0, 0);
    const diffTime = renewal.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      return <span className="text-xs text-muted">Expired {Math.abs(diffDays)}d ago</span>;
    }
    if (diffDays === 0) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-600 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
          <Clock size={11} /> ⚠️ Renews today!
        </span>
      );
    }
    if (diffDays === 1) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
          <Clock size={11} /> ⚠️ 1-day alert (Tomorrow)
        </span>
      );
    }
    if (diffDays <= 30) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
          <Clock size={11} /> ⏱️ 1-mo alert ({diffDays}d left)
        </span>
      );
    }
    return <span className="text-xs text-muted">In {diffDays} days</span>;
  }

  function getRenewalTypeBadge(type: string | null | undefined) {
    const isAuto = !type || type.toUpperCase().includes("AUTO");
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
          isAuto
            ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
            : "bg-amber-500/10 text-amber-600 border border-amber-500/20"
        }`}
      >
        {isAuto ? "⚡ Auto-Pay" : "📝 Manual"}
      </span>
    );
  }

  async function load() {
    setLoading(true);
    try {
      const [subscriptionList, employeeList] = await Promise.all([
        listSubscriptions(),
        listEmployees(),
      ]);
      setItems(subscriptionList);
      setEmployees(employeeList);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load subscriptions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function openDetails(item: SubscriptionRecord) {
    setSelected(item);
    try {
      const [licenseList, assignmentList] = await Promise.all([
        listSubscriptionLicenses(item.id),
        listSubscriptionAssignments({ subscription_id: item.id }),
      ]);
      setLicenses(licenseList);
      setAssignments(assignmentList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load subscription assignments.");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      await createSubscription({
        provider: String(form.get("provider")),
        name: String(form.get("name")),
        plan: String(form.get("plan") || "") || null,
        amount: String(form.get("amount") || "") || null,
        currency: String(form.get("currency") || "USD"),
        billing_interval: String(form.get("billing_interval")),
        renewal_type: String(form.get("renewal_type") || "AUTOPAY"),
        start_date: String(form.get("start_date") || "") || null,
        next_renewal_date: String(form.get("next_renewal_date") || "") || null,
        note: String(form.get("note") || "") || null,
      });
      setShowForm(false);
      setNotice("Subscription recorded successfully.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save subscription.");
    } finally {
      setSaving(false);
    }
  }

  async function addSeats(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = new FormData(event.currentTarget);
    setSeatSaving(true);
    try {
      const license = await createSubscriptionLicense(selected.id, {
        reference: String(form.get("reference") || "") || undefined,
        capacity: Number(form.get("capacity")),
      });
      setLicenses((current) => [...current, license]);
      event.currentTarget.reset();
      setNotice("License capacity updated.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add subscription seats.");
    } finally {
      setSeatSaving(false);
    }
  }

  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = new FormData(event.currentTarget);
    setAssignmentSaving(true);
    try {
      const assignment = await assignSubscription({
        subscription_id: selected.id,
        license_id: Number(form.get("license_id")),
        user_id: Number(form.get("user_id")),
        notes: String(form.get("notes") || "") || undefined,
      });
      setAssignments((current) => [assignment, ...current]);
      event.currentTarget.reset();
      setNotice("Subscription seat assigned to employee.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not assign subscription.");
    } finally {
      setAssignmentSaving(false);
    }
  }

  async function release(id: number) {
    try {
      await releaseSubscriptionAssignment(id);
      setAssignments((current) =>
        current.map((item) => (item.id === id ? { ...item, status: "RELEASED" } : item))
      );
      setNotice("Seat released.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not release subscription assignment.");
    }
  }

  async function handleCancel(id: number) {
    if (!window.confirm("Cancel this subscription record?")) return;
    try {
      await cancelSubscription(id);
      setNotice("Subscription marked cancelled.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not cancel subscription.");
    }
  }

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      !search.trim() ||
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.provider.toLowerCase().includes(search.toLowerCase()) ||
      (item.plan && item.plan.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus =
      statusFilter === "ALL" || item.status.toUpperCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <DashboardFrame
      title="Subscriptions"
      description="Track recurring SaaS licenses, billing cycles, allocated employee seats, and renewal alerts."
      actions={
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowImportModal(true)}
          >
            <Upload size={14} />
            <span>Import CSV / Excel</span>
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setShowForm(true)}
          >
            <Plus size={15} />
            <span>Add Subscription</span>
          </button>
        </div>
      }
    >
      {/* Toast Notice */}
      {notice && (
        <div className="alert-notice alert-success" role="status">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>×</button>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div className="alert-notice alert-danger" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      {/* Main Table Card */}
      <section className="dashboard-content-card">
        <div className="card-header-bar flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="card-heading">Subscription Portfolio</h2>
            <p className="card-subheading">
              {items.length} recurring SaaS services tracked · Includes 1-month &amp; 1-day renewal alerts.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/UniSora_Complete_SaaS_Demo_Dataset.xlsx"
              download="UniSora_Complete_SaaS_Demo_Dataset.xlsx"
              className="btn btn-outline btn-xs flex items-center gap-1.5"
              title="Download complete demo dataset"
            >
              <Download size={12} />
              <span>Download Demo Dataset</span>
            </a>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="filter-toolbar">
          <div className="filter-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by service or provider…"
              aria-label="Search subscriptions"
            />
            {search && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setSearch("")}
              >
                ×
              </button>
            )}
          </div>

          <div className="filter-select-wrap">
            <Filter size={14} className="filter-icon" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by subscription status"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </div>

        {/* Table Content */}
        {loading ? (
          <div className="hub-data-empty">
            <div className="hub-spinner" />
            <span>Loading subscriptions…</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <EmptyState
            icon={<CalendarClock size={28} />}
            title="No subscriptions found"
            description={
              search || statusFilter !== "ALL"
                ? "Try adjusting your search query or filter selection."
                : "Add Microsoft 365, Google Workspace, Slack, Figma, or any recurring vendor service."
            }
            action={
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowForm(true)}
              >
                <Plus size={15} />
                <span>Add First Subscription</span>
              </button>
            }
          />
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service &amp; Provider</th>
                  <th>Plan Tier</th>
                  <th>Price</th>
                  <th>Billing Cycle</th>
                  <th>Renewal Type</th>
                  <th>Next Renewal &amp; Alert</th>
                  <th>Status</th>
                  <th className="align-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isActive = item.status === "ACTIVE";
                  return (
                    <tr key={item.id}>
                      <td>
                        <button
                          type="button"
                          className="table-link-btn"
                          onClick={() => void openDetails(item)}
                        >
                          <WalletCards size={16} className="table-row-icon" />
                          <div>
                            <span className="font-semibold block text-primary">{item.name}</span>
                            <span className="text-muted text-xs">{item.provider}</span>
                          </div>
                        </button>
                      </td>
                      <td>
                        <span className="text-secondary">{item.plan || "Standard"}</span>
                      </td>
                      <td>
                        <span className="font-medium text-primary">
                          {item.amount != null
                            ? `${item.currency} ${Number(item.amount).toLocaleString()}`
                            : "—"}
                        </span>
                      </td>
                      <td>
                        <span className="text-secondary capitalize">{item.billing_interval}</span>
                      </td>
                      <td>
                        {getRenewalTypeBadge(item.renewal_type)}
                      </td>
                      <td>
                        <div className="flex flex-col gap-0.5">
                          <span className="text-secondary font-medium text-xs">
                            {item.next_renewal_date || "—"}
                          </span>
                          {getRenewalCountdown(item.next_renewal_date)}
                        </div>
                      </td>
                      <td>
                        <StatusBadge
                          variant={isActive ? "success" : "neutral"}
                          size="sm"
                        >
                          {item.status}
                        </StatusBadge>
                      </td>
                      <td className="align-right">
                        <div className="table-actions-inline">
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => void openDetails(item)}
                          >
                            <span>Manage Seats</span>
                          </button>
                          {isActive && (
                            <button
                              type="button"
                              className="btn btn-outline btn-sm"
                              onClick={() => void handleCancel(item.id)}
                            >
                              <span>Cancel</span>
                            </button>
                          )}
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

      {/* Subscription Access / Seat Allocation Modal */}
      {selected && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelected(null);
          }}
        >
          <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <WalletCards size={20} className="text-accent" />
                <div>
                  <h3 className="font-semibold">{selected.name}</h3>
                  <span className="text-xs text-muted">
                    {selected.provider} · {selected.plan || "Standard Plan"}
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelected(null)}
              >
                <X size={17} />
              </button>
            </div>

            <div className="modal-body space-y-6">
              {/* License Capacity Section */}
              <div className="submodal-section">
                <h4 className="submodal-heading">
                  <Plus size={15} />
                  <span>Add License Capacity or Group</span>
                </h4>
                <form className="inline-add-bar mt-2" onSubmit={addSeats}>
                  <div className="flex-1">
                    <input
                      name="reference"
                      placeholder="Seat reference / License pool (e.g. Org Tenant E3)"
                      className="form-input"
                    />
                  </div>
                  <div style={{ width: "130px" }}>
                    <input
                      name="capacity"
                      type="number"
                      min="1"
                      defaultValue="1"
                      required
                      placeholder="Qty"
                      className="form-input"
                    />
                  </div>
                  <button
                    type="submit"
                    className="btn btn-secondary btn-sm"
                    disabled={seatSaving}
                  >
                    <span>{seatSaving ? "Adding…" : "Add Seats"}</span>
                  </button>
                </form>
              </div>

              {/* Assign to Employee Section */}
              <div className="submodal-section">
                <h4 className="submodal-heading">
                  <UserPlus size={15} />
                  <span>Assign License to Employee</span>
                </h4>
                {licenses.length === 0 ? (
                  <p className="text-muted text-xs mt-2">
                    Add at least one seat group above before assigning licenses to employees.
                  </p>
                ) : (
                  <form className="space-y-3 mt-2" onSubmit={assign}>
                    <div className="form-row-grid">
                      <div className="form-group">
                        <label className="form-label">Employee</label>
                        <select name="user_id" required className="form-select">
                          <option value="">Select team member…</option>
                          {employees.map((emp) => (
                            <option key={emp.id} value={emp.id}>
                              {emp.display_name || emp.email}
                              {emp.employee_id ? ` (${emp.employee_id})` : ""}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Available Seat Pool</label>
                        <select name="license_id" required className="form-select">
                          <option value="">Select seat group…</option>
                          {licenses
                            .filter((l) => l.status === "ACTIVE")
                            .map((l) => (
                              <option key={l.id} value={l.id}>
                                {l.reference || `Seat Pool #${l.id}`} (Capacity: {l.capacity})
                              </option>
                            ))}
                        </select>
                      </div>
                    </div>

                    <div className="flex-items-center gap-3">
                      <input
                        name="notes"
                        placeholder="Service Account ID, email, or license key note (optional)"
                        className="form-input flex-1"
                      />
                      <button
                        type="submit"
                        className="btn btn-primary btn-sm flex-none"
                        disabled={assignmentSaving}
                      >
                        <span>{assignmentSaving ? "Assigning…" : "Assign License"}</span>
                      </button>
                    </div>
                  </form>
                )}
              </div>

              {/* Assigned Members List */}
              <div className="submodal-section">
                <h4 className="submodal-heading">
                  <span>Current License Holders ({assignments.length})</span>
                </h4>
                {assignments.length === 0 ? (
                  <p className="text-muted text-xs mt-2">No employee seats assigned yet.</p>
                ) : (
                  <div className="assignment-rows-list mt-2">
                    {assignments.map((assignment) => {
                      const emp = employees.find((e) => e.id === assignment.user_id);
                      const isAssigned = assignment.status === "ACTIVE";
                      return (
                        <div key={assignment.id} className="assignment-row-item">
                          <div>
                            <strong className="block text-primary text-sm">
                              {emp?.display_name || emp?.email || `Employee #${assignment.user_id}`}
                            </strong>
                            <span className="text-muted text-xs">
                              {assignment.notes || "Standard user license"} · {assignment.status}
                            </span>
                          </div>
                          {isAssigned && (
                            <button
                              type="button"
                              className="btn btn-outline btn-sm text-danger"
                              onClick={() => void release(assignment.id)}
                            >
                              <UserMinus size={13} />
                              <span>Release Seat</span>
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setSelected(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Subscription Modal Dialog */}
      {showForm && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !saving) setShowForm(false);
          }}
        >
          <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <Plus size={20} className="text-accent" />
                <h3>Add New SaaS Subscription</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowForm(false)}
                disabled={saving}
              >
                <X size={17} />
              </button>
            </div>

            <form onSubmit={submit}>
              <div className="modal-body space-y-4">
                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Provider / Vendor <span className="text-danger">*</span></label>
                    <input
                      name="provider"
                      required
                      placeholder="e.g. Microsoft, Google, Atlassian, Figma"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Subscription Name <span className="text-danger">*</span></label>
                    <input
                      name="name"
                      required
                      placeholder="e.g. Microsoft 365 Business Premium"
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Plan Tier</label>
                    <input
                      name="plan"
                      placeholder="e.g. Enterprise, Business, Team"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Billing Cycle <span className="text-danger">*</span></label>
                    <select name="billing_interval" defaultValue="monthly" className="form-select">
                      <option value="monthly">Monthly</option>
                      <option value="annual">Annual</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Periodic Amount</label>
                    <input
                      name="amount"
                      type="number"
                      min="0"
                      step="0.000001"
                      placeholder="e.g. 1500.00"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Currency <span className="text-danger">*</span></label>
                    <input
                      name="currency"
                      defaultValue="USD"
                      maxLength={3}
                      required
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Contract Start Date</label>
                    <input name="start_date" type="date" className="form-input" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Next Renewal Date</label>
                    <input name="next_renewal_date" type="date" className="form-input" />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Renewal Method <span className="text-danger">*</span></label>
                    <select name="renewal_type" defaultValue="AUTOPAY" className="form-select">
                      <option value="AUTOPAY">⚡ Auto-Pay (Card / Direct Debit)</option>
                      <option value="MANUAL">📝 Manual Renewal (Invoice / PO)</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Payment &amp; Contract Notes</label>
                    <input
                      name="note"
                      placeholder="e.g. Card ending in 4092, PO required 30d prior"
                      className="form-input"
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowForm(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving}
                >
                  <Plus size={15} />
                  <span>{saving ? "Saving…" : "Save Subscription"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Subscriptions Modal */}
      <ImportSubscriptionsModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        onSuccess={() => void load()}
      />
    </DashboardFrame>
  );
}
