"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  UserCheck,
  Building,
  Mail,
  Phone,
  WalletCards,
  Laptop,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Plus,
} from "lucide-react";
import {
  listDepartments,
  listSubscriptions,
  listAssets,
  updateEmployee,
  type DepartmentRecord,
  type SubscriptionRecord,
  type AssetRecord,
  type LifecycleEmployeeRecord,
  type EmployeeRecord,
} from "@/lib/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  employee: (LifecycleEmployeeRecord | EmployeeRecord) | null;
}

export function EditEmployeeModal({ isOpen, onClose, onSuccess, employee }: Props) {
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRecord[]>([]);
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [loadingData, setLoadingData] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [role, setRole] = useState("MEMBER");
  const [departmentId, setDepartmentId] = useState<number | undefined>(undefined);
  const [selectedSubscriptionIds, setSelectedSubscriptionIds] = useState<number[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<number[]>([]);

  useEffect(() => {
    if (!isOpen || !employee) return;

    setName(employee.display_name || "");
    setEmail(employee.email || "");
    setEmployeeId(employee.employee_id || "");
    setPhoneNumber(employee.phone_number || "");
    setRole(employee.role || "MEMBER");
    setDepartmentId(employee.department_ids?.[0] || undefined);
    setSelectedSubscriptionIds([]);
    setSelectedAssetIds([]);
    setError("");

    async function fetchData() {
      setLoadingData(true);
      try {
        const [deptList, subList, assetList] = await Promise.all([
          listDepartments(),
          listSubscriptions(),
          listAssets(),
        ]);
        setDepartments(deptList.filter((d) => d.is_active));
        setSubscriptions(subList);
        setAssets(assetList);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load auxiliary options.");
      } finally {
        setLoadingData(false);
      }
    }

    void fetchData();
  }, [isOpen, employee]);

  if (!isOpen || !employee) return null;

  const currentUserId = "user_id" in employee ? employee.user_id : employee.id;

  // Active subscriptions currently held
  const activeSubIds = new Set<number>();
  if ("subscription_assignments" in employee && Array.isArray(employee.subscription_assignments)) {
    employee.subscription_assignments
      .filter((s) => s.status === "ACTIVE")
      .forEach((s) => activeSubIds.add(s.resource_id));
  }

  // Active assets currently in custody
  const activeAssetIds = new Set<number>();
  if ("asset_assignments" in employee && Array.isArray(employee.asset_assignments)) {
    employee.asset_assignments
      .filter((a) => a.status === "ACTIVE")
      .forEach((a) => activeAssetIds.add(a.resource_id));
  }

  function toggleSubscription(subId: number) {
    setSelectedSubscriptionIds((prev) =>
      prev.includes(subId) ? prev.filter((id) => id !== subId) : [...prev, subId]
    );
  }

  function toggleAsset(assetId: number) {
    setSelectedAssetIds((prev) =>
      prev.includes(assetId) ? prev.filter((id) => id !== assetId) : [...prev, assetId]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateEmployee(currentUserId, {
        name,
        email,
        employee_id: employeeId || undefined,
        phone_number: phoneNumber || undefined,
        role,
        department_id: departmentId,
        subscription_ids: selectedSubscriptionIds.length ? selectedSubscriptionIds : undefined,
        asset_ids: selectedAssetIds.length ? selectedAssetIds : undefined,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update employee.");
    } finally {
      setSaving(false);
    }
  }

  // Assets available to be newly assigned to this user
  const assignableAssets = assets.filter(
    (a) => a.status === "AVAILABLE" || activeAssetIds.has(a.id)
  );

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
    >
      <div
        className="modal-dialog modal-dialog-lg"
        role="dialog"
        aria-modal="true"
        style={{ maxWidth: 680, maxHeight: "90vh", display: "flex", flexDirection: "column" }}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-title-row">
            <div
              className="modal-icon-badge"
              style={{ backgroundColor: "var(--color-accent-subtle)", color: "var(--color-accent)" }}
            >
              <UserCheck size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18 }}>Edit Employee Profile & Resources</h3>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
                Update employee identity, allocate subscriptions, and assign multiple hardware assets.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: "auto", flex: 1 }}>
          <div className="modal-body space-y-4" style={{ padding: "20px 24px" }}>
            {error && (
              <div className="alert-notice alert-danger" role="alert">
                <AlertCircle size={16} className="flex-none" />
                <span>{error}</span>
                <button type="button" onClick={() => setError("")}>×</button>
              </div>
            )}

            {/* Profile Fields */}
            <div className="form-row-grid">
              <div className="form-group">
                <label className="form-label">Full Name <span className="text-danger">*</span></label>
                <input
                  type="text"
                  required
                  className="form-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Rivera"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email Address <span className="text-danger">*</span></label>
                <input
                  type="email"
                  required
                  className="form-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. alex.rivera@acme.com"
                />
              </div>
            </div>

            <div className="form-row-grid">
              <div className="form-group">
                <label className="form-label">Employee ID</label>
                <input
                  type="text"
                  className="form-input"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  placeholder="e.g. EMP-101"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <input
                  type="text"
                  className="form-input"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="e.g. +1 555-0101"
                />
              </div>
            </div>

            <div className="form-row-grid">
              <div className="form-group">
                <label className="form-label">Department</label>
                <select
                  className="form-select"
                  value={departmentId || ""}
                  onChange={(e) => setDepartmentId(e.target.value ? Number(e.target.value) : undefined)}
                >
                  <option value="">Select Department…</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Role</label>
                <select
                  className="form-select"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                >
                  <option value="MEMBER">Member / Staff</option>
                  <option value="ADMIN">Administrator</option>
                  <option value="OWNER">Owner</option>
                </select>
              </div>
            </div>

            <hr style={{ border: "none", borderTop: "1px solid var(--border-color)", margin: "16px 0" }} />

            {/* Subscriptions Section */}
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <WalletCards size={16} style={{ color: "var(--color-warning)" }} />
                  <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>
                    Add Subscriptions from Subscriptions Page
                  </strong>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  {selectedSubscriptionIds.length} newly selected
                </span>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "0 0 10px" }}>
                Select available software licenses registered in your workspace to allocate to this employee.
              </p>

              {loadingData ? (
                <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 8 }}>Loading subscriptions…</div>
              ) : subscriptions.length === 0 ? (
                <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 8, background: "var(--bg-subtle)", borderRadius: "var(--radius-md)" }}>
                  No subscriptions found in workspace. Add them on the Subscriptions page first.
                </div>
              ) : (
                <div
                  style={{
                    maxHeight: 140,
                    overflowY: "auto",
                    border: "1px solid var(--border-color)",
                    borderRadius: "var(--radius-md)",
                    padding: 8,
                    background: "var(--bg-surface)",
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 6,
                  }}
                >
                  {subscriptions.map((sub) => {
                    const isAlreadyActive = activeSubIds.has(sub.id);
                    const isNewlySelected = selectedSubscriptionIds.includes(sub.id);
                    return (
                      <label
                        key={sub.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 10px",
                          borderRadius: "var(--radius-sm)",
                          background: isAlreadyActive
                            ? "var(--bg-subtle)"
                            : isNewlySelected
                            ? "var(--color-accent-subtle)"
                            : "transparent",
                          cursor: isAlreadyActive ? "default" : "pointer",
                          fontSize: 12,
                          border: isNewlySelected ? "1px solid var(--color-accent)" : "1px solid transparent",
                        }}
                      >
                        <input
                          type="checkbox"
                          disabled={isAlreadyActive}
                          checked={isAlreadyActive || isNewlySelected}
                          onChange={() => toggleSubscription(sub.id)}
                        />
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          <strong>{sub.provider || sub.name}</strong>
                          <span style={{ color: "var(--text-secondary)", fontSize: 11, marginLeft: 4 }}>
                            ({sub.plan})
                          </span>
                          {isAlreadyActive && (
                            <span style={{ color: "var(--color-success)", fontSize: 10, marginLeft: 6 }}>
                              [Active]
                            </span>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <hr style={{ border: "none", borderTop: "1px solid var(--border-color)", margin: "16px 0" }} />

            {/* IT Assets Section (1-to-Many Multi-Assign) */}
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Laptop size={16} style={{ color: "var(--color-accent)" }} />
                  <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>
                    Assign IT Assets (Laptops, Headsets, Monitors, etc.)
                  </strong>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  {selectedAssetIds.length} newly selected
                </span>
              </div>
              <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "0 0 10px" }}>
                Select one or more available hardware devices to issue to this employee simultaneously.
              </p>

              {loadingData ? (
                <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 8 }}>Loading assets…</div>
              ) : assignableAssets.length === 0 ? (
                <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 8, background: "var(--bg-subtle)", borderRadius: "var(--radius-md)" }}>
                  No available IT assets in storage. Register or return assets in the IT Assets page first.
                </div>
              ) : (
                <div
                  style={{
                    maxHeight: 160,
                    overflowY: "auto",
                    border: "1px solid var(--border-color)",
                    borderRadius: "var(--radius-md)",
                    padding: 8,
                    background: "var(--bg-surface)",
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 6,
                  }}
                >
                  {assignableAssets.map((asset) => {
                    const isAlreadyActive = activeAssetIds.has(asset.id);
                    const isNewlySelected = selectedAssetIds.includes(asset.id);
                    return (
                      <label
                        key={asset.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 10px",
                          borderRadius: "var(--radius-sm)",
                          background: isAlreadyActive
                            ? "var(--bg-subtle)"
                            : isNewlySelected
                            ? "var(--color-accent-subtle)"
                            : "transparent",
                          cursor: isAlreadyActive ? "default" : "pointer",
                          fontSize: 12,
                          border: isNewlySelected ? "1px solid var(--color-accent)" : "1px solid transparent",
                        }}
                      >
                        <input
                          type="checkbox"
                          disabled={isAlreadyActive}
                          checked={isAlreadyActive || isNewlySelected}
                          onChange={() => toggleAsset(asset.id)}
                        />
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          <span style={{ fontWeight: 600, color: "var(--color-accent)", marginRight: 4 }}>
                            [{asset.asset_tag}]
                          </span>
                          <span>{asset.name}</span>
                          <span style={{ color: "var(--text-secondary)", fontSize: 11, marginLeft: 4 }}>
                            · {asset.asset_type}
                          </span>
                          {isAlreadyActive && (
                            <span style={{ color: "var(--color-success)", fontSize: 10, marginLeft: 6 }}>
                              [In Custody]
                            </span>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="modal-footer" style={{ padding: "14px 24px", display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={saving}
            >
              {saving ? (
                <>
                  <Loader2 size={14} className="spin-animation" />
                  <span>Saving & Allocating Resources…</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={14} />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
