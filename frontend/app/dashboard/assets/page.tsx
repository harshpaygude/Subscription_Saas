"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  Laptop,
  Plus,
  RotateCcw,
  UserPlus,
  Search,
  Filter,
  X,
  CheckCircle2,
  HardDrive,
  Upload,
  Info,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  assignAsset,
  createAsset,
  listAssetAssignments,
  listAssets,
  listEmployees,
  returnAsset,
  type AssetAssignmentRecord,
  type AssetRecord,
  type EmployeeRecord,
} from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { ImportAssetsModal } from "@/components/dashboard/ImportAssetsModal";
import { AssetDetailModal } from "@/components/dashboard/AssetDetailModal";

export default function AssetsPage() {
  const [items, setItems] = useState<AssetRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [assignments, setAssignments] = useState<Record<number, AssetAssignmentRecord>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [assigning, setAssigning] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");

  async function load() {
    try {
      const [assetList, employeeList] = await Promise.all([
        listAssets(),
        listEmployees(),
      ]);
      const assignmentEntries = await Promise.all(
        assetList.map(
          async (asset) =>
            [
              asset.id,
              (await listAssetAssignments(asset.id)).find(
                (item) => item.status === "ACTIVE"
              ),
            ] as const
        )
      );
      setItems(assetList);
      setEmployees(employeeList);
      setAssignments(
        Object.fromEntries(
          assignmentEntries.filter(([, assignment]) => assignment)
        ) as Record<number, AssetAssignmentRecord>
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load assets.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    try {
      await createAsset({
        asset_tag: String(form.get("asset_tag")),
        asset_type: String(form.get("asset_type")),
        name: String(form.get("name")),
        manufacturer: String(form.get("manufacturer") || "") || undefined,
        model: String(form.get("model") || "") || undefined,
        serial_number: String(form.get("serial_number") || "") || undefined,
        purchase_cost: String(form.get("purchase_cost") || "") || undefined,
        currency: String(form.get("currency") || "USD"),
      });
      setShowAddModal(false);
      setError("");
      setNotice("IT Asset registered to inventory.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create asset.");
    } finally {
      setSaving(false);
    }
  }

  async function assign(assetId: number, userId: string) {
    if (!userId) return;
    setAssigning(assetId);
    try {
      await assignAsset(assetId, { user_id: Number(userId) });
      setError("");
      setNotice("Asset assigned to employee.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not assign asset.");
    } finally {
      setAssigning(null);
    }
  }

  async function remove(assignmentId: number) {
    if (!window.confirm("Confirm return of this hardware asset?")) return;
    setAssigning(assignmentId);
    try {
      await returnAsset(assignmentId, {
        handover_notes: "Returned to inventory custody.",
      });
      setError("");
      setNotice("Asset returned to available inventory.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove asset assignment.");
    } finally {
      setAssigning(null);
    }
  }

  const assignedCount = Object.keys(assignments).length;
  const availableCount = items.length - assignedCount;

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      !search.trim() ||
      item.asset_tag.toLowerCase().includes(search.toLowerCase()) ||
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      (item.serial_number && item.serial_number.toLowerCase().includes(search.toLowerCase())) ||
      (item.model && item.model.toLowerCase().includes(search.toLowerCase()));

    const matchesType = typeFilter === "ALL" || item.asset_type === typeFilter;
    const isAssigned = Boolean(assignments[item.id]);
    const matchesStatus =
      statusFilter === "ALL" ||
      (statusFilter === "ASSIGNED" && isAssigned) ||
      (statusFilter === "AVAILABLE" && !isAssigned);

    return matchesSearch && matchesType && matchesStatus;
  });

  const uniqueTypes = Array.from(new Set(items.map((i) => i.asset_type)));

  return (
    <DashboardFrame
      title="IT Assets"
      description="Physical device tracking, serial numbers, custody assignments, and handover logs."
      actions={
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowImportModal(true)}
            title="Import IT assets roster (CSV or Excel)"
          >
            <Upload size={14} />
            <span>Import CSV / Excel</span>
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={15} />
            <span>Add Asset</span>
          </button>
        </div>
      }
    >
      {notice && (
        <div className="alert-notice alert-success" role="status">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")}>×</button>
        </div>
      )}

      {error && (
        <div className="alert-notice alert-danger" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>×</button>
        </div>
      )}

      {/* KPI Metrics */}
      <section className="overview-metrics-grid" aria-label="Inventory KPIs">
        <MetricCard
          label="Total Inventory"
          value={items.length}
          subtext="Catalogued equipment"
          icon={<Laptop size={20} />}
        />
        <MetricCard
          label="In Custody"
          value={assignedCount}
          subtext="Allocated to working team members"
          icon={<HardDrive size={20} />}
        />
        <MetricCard
          label="Available in Storage"
          value={availableCount}
          subtext="Ready for new joiners"
          icon={<CheckCircle2 size={20} />}
        />
      </section>

      {/* Assets Table Section */}
      <section className="dashboard-content-card mt-6">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Hardware Inventory</h2>
            <p className="card-subheading">
              Track laptops, monitors, mobile phones, and network equipment.
            </p>
          </div>
        </div>

        {/* Filters Bar */}
        <div className="filter-toolbar">
          <div className="filter-search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by tag, model, or serial number…"
              aria-label="Search IT assets"
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
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              aria-label="Filter by asset type"
            >
              <option value="ALL">All Types</option>
              {uniqueTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-select-wrap">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by custody status"
            >
              <option value="ALL">All Custody Statuses</option>
              <option value="ASSIGNED">In Custody</option>
              <option value="AVAILABLE">Available</option>
            </select>
          </div>
        </div>

        {/* Table */}
        {items.length === 0 ? (
          <EmptyState
            icon={<Laptop size={28} />}
            title="No IT assets registered"
            description="Add company laptops, monitors, phones, and peripherals to track custody."
            action={
              <div style={{ display: "flex", gap: "8px", justifyContent: "center", flexWrap: "wrap" }}>
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
                  onClick={() => setShowAddModal(true)}
                >
                  <Plus size={15} />
                  <span>Add First IT Asset</span>
                </button>
              </div>
            }
          />
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Asset Tag & Name</th>
                  <th>Type</th>
                  <th>Model / Serial</th>
                  <th>Current Custody</th>
                  <th>Status</th>
                  <th className="align-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const assignment = assignments[item.id];
                  const emp =
                    assignment &&
                    employees.find((person) => person.id === assignment.user_id);
                  const isAssigned = Boolean(assignment);

                  return (
                    <tr key={item.id}>
                      <td>
                        <div
                          className="flex-items-center gap-2 cursor-pointer"
                          onClick={() => setSelectedAsset(item)}
                          title="Click to view full hardware details & employee custody history"
                          style={{ cursor: "pointer" }}
                        >
                          <Laptop size={16} className="table-row-icon" />
                          <div>
                            <span
                              className="font-semibold block text-primary"
                              style={{ textDecoration: "underline", textUnderlineOffset: 3 }}
                            >
                              {item.asset_tag}
                            </span>
                            <span className="text-secondary text-xs">{item.name}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="text-secondary">{item.asset_type}</span>
                      </td>
                      <td>
                        <span className="text-muted text-xs block">
                          {item.model || "—"}
                          {item.serial_number ? ` (S/N: ${item.serial_number})` : ""}
                        </span>
                      </td>
                      <td>
                        {emp ? (
                          <div>
                            <Link
                              href={`/dashboard/employees/${emp.id}`}
                              className="font-medium text-primary text-xs block"
                              title="Redirect to employee profile"
                              style={{ textDecoration: "underline", textUnderlineOffset: 2 }}
                            >
                              {emp.display_name || emp.email}
                            </Link>
                            <span className="text-muted text-xs">
                              {emp.employee_id ? `ID: ${emp.employee_id}` : emp.email}
                            </span>
                          </div>
                        ) : (
                          <div className="inline-select-table-wrap">
                            <select
                              aria-label={`Assign employee to ${item.asset_tag}`}
                              defaultValue=""
                              disabled={assigning === item.id}
                              onChange={(e) => void assign(item.id, e.target.value)}
                              className="form-select select-xs"
                            >
                              <option value="">+ Assign Employee</option>
                              {employees.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.display_name || p.email}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}
                      </td>
                      <td>
                        <StatusBadge
                          variant={isAssigned ? "info" : "success"}
                          size="sm"
                        >
                          {isAssigned ? "Assigned" : "Available"}
                        </StatusBadge>
                      </td>
                      <td className="align-right">
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end", alignItems: "center" }}>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => setSelectedAsset(item)}
                            title="View full asset info & custody history"
                          >
                            <Info size={13} />
                            <span>View Info</span>
                          </button>
                          {assignment ? (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              disabled={assigning === assignment.id}
                              onClick={() => void remove(assignment.id)}
                              title="Return device to storage"
                            >
                              <RotateCcw size={13} />
                              <span>
                                {assigning === assignment.id ? "Returning…" : "Return"}
                              </span>
                            </button>
                          ) : null}
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

      {/* Add IT Asset Modal */}
      {showAddModal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !saving) setShowAddModal(false);
          }}
        >
          <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <Plus size={20} className="text-accent" />
                <h3>Register Physical IT Asset</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowAddModal(false)}
                disabled={saving}
              >
                <X size={17} />
              </button>
            </div>

            <form onSubmit={submit}>
              <div className="modal-body space-y-4">
                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Asset Tag <span className="text-danger">*</span></label>
                    <input
                      name="asset_tag"
                      required
                      placeholder="e.g. LT-1092"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Asset Type <span className="text-danger">*</span></label>
                    <input
                      name="asset_type"
                      required
                      placeholder="e.g. Laptop, Monitor, Phone"
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Device Display Name <span className="text-danger">*</span></label>
                    <input
                      name="name"
                      required
                      placeholder="e.g. MacBook Pro 16 M3 Max"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Manufacturer</label>
                    <input
                      name="manufacturer"
                      placeholder="e.g. Apple, Dell, Lenovo"
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Model Name / Number</label>
                    <input
                      name="model"
                      placeholder="e.g. A2991"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Serial Number (S/N)</label>
                    <input
                      name="serial_number"
                      placeholder="e.g. C02G90..."
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Purchase Cost</label>
                    <input
                      name="purchase_cost"
                      type="number"
                      min="0"
                      step="0.000001"
                      placeholder="e.g. 2499.00"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Currency</label>
                    <input
                      name="currency"
                      defaultValue="USD"
                      maxLength={3}
                      className="form-input"
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddModal(false)}
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
                  <span>{saving ? "Registering…" : "Register IT Asset"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* IT Asset Bulk CSV / Excel Import Modal */}
      <ImportAssetsModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        onSuccess={() => {
          void load();
          setNotice("IT hardware assets and employee custody assignments synchronized successfully!");
        }}
      />

      {/* Asset Full Information & Custody History Drawer */}
      <AssetDetailModal
        isOpen={Boolean(selectedAsset)}
        onClose={() => setSelectedAsset(null)}
        asset={selectedAsset}
        onAssetUpdated={() => void load()}
      />
    </DashboardFrame>
  );
}
