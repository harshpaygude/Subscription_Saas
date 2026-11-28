"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  X,
  Laptop,
  Headphones,
  Monitor,
  Smartphone,
  Layers,
  Calendar,
  DollarSign,
  Tag,
  Shield,
  MapPin,
  Clock,
  User,
  RotateCcw,
  UserCheck,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";
import {
  listAssetAssignments,
  returnAsset,
  assignAsset,
  listEmployees,
  type AssetRecord,
  type AssetAssignmentRecord,
  type EmployeeRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  asset: AssetRecord | null;
  onAssetUpdated: () => void;
}

export function AssetDetailModal({ isOpen, onClose, asset, onAssetUpdated }: Props) {
  const [assignments, setAssignments] = useState<AssetAssignmentRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [assigningUser, setAssigningUser] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!isOpen || !asset) return;
    setError("");
    setNotice("");
    setAssigningUser("");

    async function fetchData() {
      setLoading(true);
      try {
        const [assignmentList, employeeList] = await Promise.all([
          listAssetAssignments(asset!.id),
          listEmployees(),
        ]);
        setAssignments(assignmentList);
        setEmployees(employeeList);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load custody details.");
      } finally {
        setLoading(false);
      }
    }

    void fetchData();
  }, [isOpen, asset]);

  if (!isOpen || !asset) return null;

  const activeAssignment = assignments.find((a) => a.status === "ACTIVE");
  const pastAssignments = assignments.filter((a) => a.status !== "ACTIVE");

  async function handleReturn(assignmentId: number) {
    if (!window.confirm(`Confirm return of ${asset?.name} (${asset?.asset_tag}) to inventory?`)) return;
    setActionLoading(true);
    setError("");
    try {
      await returnAsset(assignmentId, { handover_notes: "Returned to inventory custody." });
      setNotice("Hardware device returned to available inventory.");
      onAssetUpdated();
      setAssignments(await listAssetAssignments(asset!.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to return asset.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAssign() {
    if (!assigningUser) return;
    setActionLoading(true);
    setError("");
    try {
      await assignAsset(asset!.id, { user_id: Number(assigningUser) });
      setNotice("Device assigned to employee.");
      setAssigningUser("");
      onAssetUpdated();
      setAssignments(await listAssetAssignments(asset!.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign asset.");
    } finally {
      setActionLoading(false);
    }
  }

  function getDeviceIcon() {
    const t = (asset?.asset_type || "").toLowerCase();
    if (t.includes("headset") || t.includes("audio")) return <Headphones size={22} />;
    if (t.includes("monitor") || t.includes("display")) return <Monitor size={22} />;
    if (t.includes("phone") || t.includes("mobile")) return <Smartphone size={22} />;
    return <Laptop size={22} />;
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !actionLoading) onClose();
      }}
    >
      <div
        className="modal-dialog modal-dialog-lg"
        role="dialog"
        aria-modal="true"
        style={{ maxWidth: 740, maxHeight: "90vh", display: "flex", flexDirection: "column" }}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-title-row">
            <div
              className="modal-icon-badge"
              style={{
                width: 42,
                height: 42,
                borderRadius: 12,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--color-accent-subtle)",
                color: "var(--color-accent-ink)",
                border: "1px solid var(--color-accent-ring)",
              }}
            >
              {getDeviceIcon()}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    fontWeight: 700,
                    fontSize: 14,
                    color: "var(--color-accent-ink)",
                    letterSpacing: "0.03em",
                    fontFamily: "monospace",
                  }}
                >
                  {asset.asset_tag}
                </span>
                <StatusBadge variant={activeAssignment ? "info" : "success"} size="sm">
                  {activeAssignment ? "In Custody" : "Available in Storage"}
                </StatusBadge>
              </div>
              <h3 style={{ margin: "3px 0 0", fontSize: 18, color: "var(--text-primary)" }}>
                {asset.name}
              </h3>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={actionLoading}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="modal-body space-y-5" style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
          {notice && (
            <div className="alert-notice alert-success" role="status">
              <span>{notice}</span>
              <button type="button" onClick={() => setNotice("")}>×</button>
            </div>
          )}

          {error && (
            <div className="alert-notice alert-danger" role="alert">
              <AlertCircle size={16} className="flex-none" />
              <span>{error}</span>
              <button type="button" onClick={() => setError("")}>×</button>
            </div>
          )}

          {/* Full Specifications Grid */}
          <div
            style={{
              background: "var(--bg-subtle)",
              border: "1px solid var(--border-color)",
              borderRadius: "var(--radius-lg)",
              padding: 16,
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)", marginBottom: 12 }}>
              Hardware Specifications & Details
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Device Category</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{asset.asset_type}</strong>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Manufacturer / Brand</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{asset.manufacturer || "—"}</strong>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Model Name / No.</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{asset.model || "—"}</strong>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Serial Number (S/N)</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)", fontFamily: "monospace" }}>
                  {asset.serial_number || "—"}
                </strong>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Purchase Cost</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>
                  {asset.purchase_cost ? `${asset.currency} ${Number(asset.purchase_cost).toLocaleString()}` : "—"}
                </strong>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Storage / Location</span>
                <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{asset.location || "San Francisco HQ"}</strong>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Purchase Date</span>
                <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{asset.purchase_date || "—"}</span>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Warranty Expiry</span>
                <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{asset.warranty_expiry || "—"}</span>
              </div>

              <div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", display: "block" }}>Registered On</span>
                <span style={{ fontSize: 12, color: "var(--text-primary)" }}>
                  {new Date(asset.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Current Custody / Assignment Status */}
          <div
            style={{
              background: activeAssignment ? "var(--bg-surface)" : "var(--bg-subtle)",
              border: activeAssignment ? "1px solid var(--color-accent-ring)" : "1px solid var(--border-color)",
              borderRadius: "var(--radius-lg)",
              padding: 18,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <UserCheck size={16} style={{ color: activeAssignment ? "var(--color-accent-ink)" : "var(--text-muted)" }} />
                <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                  Current Custody Allocation
                </h4>
              </div>
              {activeAssignment && (
                <button
                  type="button"
                  className="btn btn-secondary btn-xs"
                  onClick={() => handleReturn(activeAssignment.id)}
                  disabled={actionLoading}
                  title="Return to inventory custody"
                >
                  <RotateCcw size={12} />
                  <span>Return Asset</span>
                </button>
              )}
            </div>

            {loading ? (
              <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 10 }}>Loading custody records…</div>
            ) : activeAssignment ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "var(--bg-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "12px 16px",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <strong style={{ fontSize: 14, color: "var(--text-primary)" }}>
                      {activeAssignment.user_name || activeAssignment.user_email || `User #${activeAssignment.user_id}`}
                    </strong>
                    {activeAssignment.user_employee_id && (
                      <span className="badge badge-subtle badge-xs">
                        ID: {activeAssignment.user_employee_id}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                    {activeAssignment.user_email}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                    Handed over on {new Date(activeAssignment.assigned_at).toLocaleDateString()}
                    {activeAssignment.handover_notes && ` · "${activeAssignment.handover_notes}"`}
                  </div>
                </div>

                {/* Redirect Link to Employee Profile */}
                <Link
                  href={`/dashboard/employees/${activeAssignment.user_id}`}
                  className="btn btn-primary btn-sm"
                  style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
                  title="Redirect to employee lifecycle and profile"
                >
                  <User size={13} />
                  <span>View Employee Profile</span>
                  <ExternalLink size={12} />
                </Link>
              </div>
            ) : (
              <div>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 10px" }}>
                  This device is currently unassigned in storage. You can allocate custody to an employee below:
                </p>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <select
                    className="form-select select-sm"
                    value={assigningUser}
                    onChange={(e) => setAssigningUser(e.target.value)}
                    style={{ maxWidth: 320 }}
                  >
                    <option value="">Choose employee to assign…</option>
                    {employees.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.display_name || e.email} {e.employee_id ? `(${e.employee_id})` : ""}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={handleAssign}
                    disabled={!assigningUser || actionLoading}
                  >
                    {actionLoading ? <Loader2 size={13} className="spin-animation" /> : <UserCheck size={13} />}
                    <span>Assign Device</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Historical Custodians (List of all users to whom it was provided) */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Clock size={16} style={{ color: "var(--text-muted)" }} />
              <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                Custody &amp; Handover History ({assignments.length} total)
              </h4>
            </div>

            {loading ? (
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Loading history…</div>
            ) : assignments.length === 0 ? (
              <div
                style={{
                  padding: "16px",
                  background: "var(--bg-subtle)",
                  borderRadius: "var(--radius-md)",
                  textAlign: "center",
                  fontSize: 12,
                  color: "var(--text-secondary)",
                }}
              >
                No previous custody assignments recorded for this hardware item.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {assignments.map((asgn) => {
                  const emp = employees.find((p) => p.id === asgn.user_id);
                  const isCurrent = asgn.status === "ACTIVE";

                  return (
                    <div
                      key={asgn.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12,
                        padding: "13px 16px",
                        background: "var(--bg-subtle)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "var(--radius-md)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: "50%",
                            background: isCurrent ? "var(--color-accent)" : "var(--bg-surface)",
                            color: isCurrent ? "var(--color-accent-text)" : "var(--text-secondary)",
                            border: isCurrent ? "none" : "1px solid var(--border-color)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 13,
                            fontWeight: 700,
                            flexShrink: 0,
                          }}
                        >
                          {(asgn.user_name || asgn.user_email || emp?.display_name || "U")[0].toUpperCase()}
                        </div>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>
                              {asgn.user_name || emp?.display_name || asgn.user_email || `User #${asgn.user_id}`}
                            </strong>
                            <StatusBadge variant={isCurrent ? "success" : "neutral"} size="sm">
                              {isCurrent ? "Active Custody" : "Returned"}
                            </StatusBadge>
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                            {asgn.user_email || emp?.email}
                            {asgn.user_employee_id || emp?.employee_id ? ` · ID: ${asgn.user_employee_id || emp?.employee_id}` : ""}
                          </div>
                          <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
                            Handed over: {new Date(asgn.assigned_at).toLocaleDateString()}
                            {asgn.returned_at && ` · Returned: ${new Date(asgn.returned_at).toLocaleDateString()}`}
                            {asgn.handover_notes && ` · Notes: ${asgn.handover_notes}`}
                          </div>
                        </div>
                      </div>

                      {/* Redirect Link to this User */}
                      <Link
                        href={`/dashboard/employees/${asgn.user_id}`}
                        className="btn btn-secondary btn-xs"
                        style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                        title={`Redirect to profile of ${asgn.user_name || asgn.user_email}`}
                      >
                        <User size={11} />
                        <span>View Employee</span>
                        <ArrowRight size={11} />
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer" style={{ padding: "12px 24px", display: "flex", justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
