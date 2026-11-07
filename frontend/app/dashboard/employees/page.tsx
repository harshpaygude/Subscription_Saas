"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  CheckCircle2,
  ClipboardCheck,
  Plus,
  UserRoundCheck,
  Search,
  Filter,
  UserPlus,
  ArrowRight,
  X,
  Mail,
  Phone,
  Building,
  Laptop,
  WalletCards,
  UserCheck,
  Upload,
  Edit3,
} from "lucide-react";
import { DashboardFrame } from "@/components/dashboard/DashboardFrame";
import {
  completeLifecycleTask,
  createEmployee,
  getLifecycleDashboard,
  listAssets,
  listDepartments,
  listEmployees,
  startEmployeeOnboarding,
  type AssetRecord,
  type DepartmentRecord,
  type EmployeeRecord,
  type LifecycleDashboardRecord,
  type LifecycleEmployeeRecord,
  type LifecycleTaskRecord,
} from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ImportEmployeesModal } from "@/components/dashboard/ImportEmployeesModal";
import { EditEmployeeModal } from "@/components/dashboard/EditEmployeeModal";

export default function EmployeeLifecyclePage() {
  const [data, setData] = useState<LifecycleDashboardRecord | null>(null);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [creating, setCreating] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showStartModal, setShowStartModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<LifecycleEmployeeRecord | null>(null);
  const [employeeId, setEmployeeId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [joinedAt, setJoinedAt] = useState(new Date().toISOString().slice(0, 10));
  const [onboarding, setOnboarding] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [deptFilter, setDeptFilter] = useState<string>("ALL");

  async function load() {
    try {
      const [dashboard, employeeList, departmentList, assetList] = await Promise.all([
        getLifecycleDashboard(),
        listEmployees(),
        listDepartments(),
        listAssets({ status: "AVAILABLE" }),
      ]);
      setData(dashboard);
      setEmployees(employeeList);
      setDepartments(departmentList.filter((item) => item.is_active));
      setAssets(assetList);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load employee lifecycle data.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onboard(event: FormEvent) {
    event.preventDefault();
    if (!employeeId || !departmentId) return;
    setOnboarding(true);
    try {
      await startEmployeeOnboarding(Number(employeeId), {
        department_id: Number(departmentId),
        joined_at: joinedAt,
      });
      setEmployeeId("");
      setDepartmentId("");
      setShowStartModal(false);
      setNotice("Onboarding lifecycle initialized for existing user.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start onboarding.");
    } finally {
      setOnboarding(false);
    }
  }

  async function addEmployee(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setCreating(true);
    try {
      await createEmployee({
        employee_id: String(form.get("employee_id")),
        name: String(form.get("name")),
        email: String(form.get("email")),
        phone_number: String(form.get("phone_number") || "") || undefined,
        department_id: Number(form.get("department_id")),
        joined_at: String(form.get("joined_at")),
        asset_ids: form.getAll("asset_ids").map(Number),
      });
      setShowAddModal(false);
      setNotice("Employee added and resources provisioned.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add employee.");
    } finally {
      setCreating(false);
    }
  }

  async function complete(task: LifecycleTaskRecord) {
    const note =
      task.task_type === "MANUAL_ACCESS"
        ? window.prompt("Enter the verification note for this access task:") || undefined
        : undefined;
    try {
      await completeLifecycleTask(task.id, note);
      setNotice("Lifecycle action verified and completed.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The linked resource action must be completed first.");
    }
  }

  // Combine all employee cases for unified directory view
  const allEmployees: (LifecycleEmployeeRecord & { listCategory: string })[] = [];
  if (data) {
    data.working.forEach((e) => allEmployees.push({ ...e, listCategory: "WORKING" }));
    data.new_joiners.forEach((e) => allEmployees.push({ ...e, listCategory: "NEW_JOINER" }));
    data.offboarding.forEach((e) => allEmployees.push({ ...e, listCategory: "OFFBOARDING" }));
    data.completed.forEach((e) => allEmployees.push({ ...e, listCategory: "COMPLETED" }));
  }

  // Deduplicate by user_id
  const uniqueEmployeeMap = new Map<number, LifecycleEmployeeRecord & { listCategory: string }>();
  allEmployees.forEach((emp) => {
    if (!uniqueEmployeeMap.has(emp.user_id)) {
      uniqueEmployeeMap.set(emp.user_id, emp);
    }
  });
  const unifiedList = Array.from(uniqueEmployeeMap.values());

  const filteredEmployees = unifiedList.filter((emp) => {
    const matchesSearch =
      !search.trim() ||
      (emp.display_name && emp.display_name.toLowerCase().includes(search.toLowerCase())) ||
      emp.email.toLowerCase().includes(search.toLowerCase()) ||
      (emp.employee_id && emp.employee_id.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus =
      statusFilter === "ALL" ||
      emp.status === statusFilter ||
      emp.listCategory === statusFilter;

    const matchesDept =
      deptFilter === "ALL" ||
      emp.department_names.some((d) => d.toLowerCase() === deptFilter.toLowerCase());

    return matchesSearch && matchesStatus && matchesDept;
  });

  return (
    <DashboardFrame
      title="Employee Lifecycle"
      description="Holistic directory of team members, role assignments, IT assets in custody, and offboarding clearance."
      actions={
        <div className="flex-items-center gap-2">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowImportModal(true)}
            title="Import multi-service roster (CSV or Excel)"
          >
            <Upload size={14} />
            <span>Import CSV</span>
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowStartModal(true)}
          >
            <UserCheck size={14} />
            <span>Start Existing User</span>
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={15} />
            <span>Add Employee</span>
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

      {/* Metrics Row */}
      <section className="overview-metrics-grid" aria-label="People KPIs">
        <MetricCard
          label="Active Employees"
          value={data?.working.length ?? 0}
          subtext="Currently employed and active"
          icon={<UserRoundCheck size={20} />}
        />
        <MetricCard
          label="New Joiners"
          value={data?.new_joiners.length ?? 0}
          subtext="Onboarding in progress"
          icon={<UserPlus size={20} />}
        />
        <MetricCard
          label="In Offboarding"
          value={data?.offboarding.length ?? 0}
          subtext="Asset & license clearance"
          icon={<ClipboardCheck size={20} />}
        />
        <MetricCard
          label="Pending Tasks"
          value={data?.pending_tasks.length ?? 0}
          subtext="Admin verification actions"
          icon={<CheckCircle2 size={20} />}
        />
      </section>

      {/* Employee Directory Section */}
      <section className="dashboard-content-card mt-6">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">People Directory</h2>
            <p className="card-subheading">
              Manage accounts, assigned hardware, and access provisions.
            </p>
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
              placeholder="Search by name, email, or employee ID…"
              aria-label="Search employees"
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
              aria-label="Filter by lifecycle status"
            >
              <option value="ALL">All Statuses</option>
              <option value="WORKING">Active Working</option>
              <option value="NEW_JOINER">New Joiners</option>
              <option value="OFFBOARDING">Offboarding</option>
              <option value="COMPLETED">Offboarded</option>
            </select>
          </div>

          <div className="filter-select-wrap">
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              aria-label="Filter by department"
            >
              <option value="ALL">All Departments</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.name}>
                  {dept.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Directory Table */}
        {filteredEmployees.length === 0 ? (
          <EmptyState
            icon={<UserRoundCheck size={30} />}
            title="No employees found"
            description={
              search || statusFilter !== "ALL" || deptFilter !== "ALL"
                ? "Try adjusting your search queries or filter selections."
                : "Add your first employee to initiate lifecycle tracking and asset management."
            }
            action={
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowAddModal(true)}
              >
                <Plus size={15} />
                <span>Add Employee</span>
              </button>
            }
          />
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Role / ID</th>
                  <th>Resources</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th className="align-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => {
                  const initial = (emp.display_name || emp.email || "E")
                    .slice(0, 1)
                    .toUpperCase();
                  const isOffboarded = emp.status === "COMPLETED";
                  const isOffboarding = emp.status === "OFFBOARDING";

                  return (
                    <tr key={emp.id}>
                      <td>
                        <Link
                          href={`/dashboard/employees/${emp.user_id}`}
                          className="table-user-cell"
                        >
                          <div className="user-avatar-circle size-sm">{initial}</div>
                          <div>
                            <span className="font-semibold block text-primary">
                              {emp.display_name || emp.email}
                            </span>
                            <span className="text-secondary text-xs">{emp.email}</span>
                          </div>
                        </Link>
                      </td>
                      <td>
                        <span className="text-secondary">
                          {emp.department_names.length
                            ? emp.department_names.join(", ")
                            : "—"}
                        </span>
                      </td>
                      <td>
                        <div>
                          <span className="text-primary font-medium text-xs block">
                            {emp.role}
                          </span>
                          <span className="text-muted text-xs">
                            {emp.employee_id || "No ID"}
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="flex-items-center gap-3 text-secondary text-xs">
                          <span title={`${emp.subscription_assignments.length} Subscriptions`}>
                            <WalletCards size={13} className="inline mr-1 text-muted" />
                            {emp.subscription_assignments.length}
                          </span>
                          <span title={`${emp.asset_assignments.length} IT Assets`}>
                            <Laptop size={13} className="inline mr-1 text-muted" />
                            {emp.asset_assignments.length}
                          </span>
                        </div>
                      </td>
                      <td>
                        <StatusBadge
                          variant={
                            isOffboarded
                              ? "neutral"
                              : isOffboarding
                              ? "warning"
                              : "success"
                          }
                          size="sm"
                        >
                          {emp.status}
                        </StatusBadge>
                      </td>
                      <td>
                        <span className="text-muted text-xs">{emp.joined_at}</span>
                      </td>
                      <td className="align-right">
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end", alignItems: "center" }}>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => setEditingEmployee(emp)}
                            title="Edit employee info, subscriptions, and IT assets"
                          >
                            <Edit3 size={13} />
                            <span>Edit</span>
                          </button>
                          <Link
                            href={`/dashboard/employees/${emp.user_id}`}
                            className="btn btn-secondary btn-sm"
                          >
                            <span>Manage</span>
                            <ArrowRight size={13} />
                          </Link>
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

      {/* Pending Tasks Section */}
      <section className="dashboard-content-card mt-6">
        <div className="card-header-bar">
          <div>
            <h2 className="card-heading">Required Lifecycle Tasks</h2>
            <p className="card-subheading">
              Open clearance actions and access verification tasks needing administrator attention.
            </p>
          </div>
        </div>

        {(data?.pending_tasks.length ?? 0) === 0 ? (
          <div className="empty-subpanel">
            <CheckCircle2 size={24} className="text-success" />
            <div>
              <strong className="block text-primary">All lifecycle tasks are clear</strong>
              <span className="text-secondary text-xs">
                No active onboarding or offboarding checklists waiting for verification.
              </span>
            </div>
          </div>
        ) : (
          <div className="tasks-list-grid">
            {data?.pending_tasks.map((task) => (
              <div className="task-item-card" key={task.id}>
                <div className="task-icon-col">
                  <ClipboardCheck size={20} className="text-accent" />
                </div>
                <div className="task-content-col">
                  <h4 className="task-title">{task.title}</h4>
                  <p className="task-meta">
                    Type: <span className="font-medium">{task.task_type.replaceAll("_", " ")}</span>
                    <span className="bullet-sep">·</span>
                    Action: <span className="font-medium">{task.action_status}</span>
                  </p>
                </div>
                <div className="task-action-col">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => void complete(task)}
                  >
                    <CheckCircle2 size={13} />
                    <span>Complete Task</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Add Employee Modal */}
      {showAddModal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !creating) setShowAddModal(false);
          }}
        >
          <div className="modal-dialog modal-dialog-lg" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <UserPlus size={20} className="text-accent" />
                <h3>Add New Employee & Provision Resources</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowAddModal(false)}
                disabled={creating}
              >
                <X size={17} />
              </button>
            </div>

            <form onSubmit={addEmployee}>
              <div className="modal-body space-y-4">
                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Employee ID <span className="text-danger">*</span></label>
                    <input
                      name="employee_id"
                      required
                      placeholder="e.g. EMP-042"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Full Name <span className="text-danger">*</span></label>
                    <input
                      name="name"
                      required
                      placeholder="e.g. Alex Morgan"
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Work Email <span className="text-danger">*</span></label>
                    <input
                      name="email"
                      type="email"
                      required
                      placeholder="alex@company.com"
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Phone Number</label>
                    <input
                      name="phone_number"
                      type="tel"
                      placeholder="+1 (555) 019-2834"
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-row-grid">
                  <div className="form-group">
                    <label className="form-label">Department <span className="text-danger">*</span></label>
                    <select name="department_id" required className="form-select">
                      <option value="">Select department…</option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Joining Date <span className="text-danger">*</span></label>
                    <input
                      name="joined_at"
                      type="date"
                      defaultValue={joinedAt}
                      required
                      className="form-input"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Initial IT Assets Provided
                    <small className="form-label-help">Hold Ctrl/Cmd to select multiple available assets</small>
                  </label>
                  <select
                    name="asset_ids"
                    multiple
                    size={Math.min(Math.max(assets.length, 2), 5)}
                    className="form-select form-multiselect"
                  >
                    {assets.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.asset_tag} — {item.name} ({item.asset_type})
                      </option>
                    ))}
                  </select>
                  {assets.length === 0 && (
                    <small className="text-muted mt-1 block">
                      No available assets currently in inventory. Assets can be assigned later.
                    </small>
                  )}
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddModal(false)}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={creating || !departments.length}
                >
                  <Plus size={15} />
                  <span>{creating ? "Adding Employee…" : "Create & Provision"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Start Lifecycle for Existing User Modal */}
      {showStartModal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !onboarding) setShowStartModal(false);
          }}
        >
          <div className="modal-dialog" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div className="modal-header-title-row">
                <UserCheck size={20} className="text-accent" />
                <h3>Initialize Lifecycle for Existing Account</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowStartModal(false)}
                disabled={onboarding}
              >
                <X size={17} />
              </button>
            </div>

            <form onSubmit={onboard}>
              <div className="modal-body space-y-4">
                <div className="form-group">
                  <label className="form-label">Select Registered User <span className="text-danger">*</span></label>
                  <select
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    required
                    className="form-select"
                  >
                    <option value="">Choose employee…</option>
                    {employees.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.display_name || item.email}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Target Department <span className="text-danger">*</span></label>
                  <select
                    value={departmentId}
                    onChange={(e) => setDepartmentId(e.target.value)}
                    required
                    className="form-select"
                  >
                    <option value="">Choose department…</option>
                    {departments.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Effective Joining Date <span className="text-danger">*</span></label>
                  <input
                    type="date"
                    value={joinedAt}
                    onChange={(e) => setJoinedAt(e.target.value)}
                    required
                    className="form-input"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowStartModal(false)}
                  disabled={onboarding}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={onboarding || !employeeId || !departmentId}
                >
                  <UserPlus size={15} />
                  <span>{onboarding ? "Starting…" : "Start Lifecycle"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Multi-Service Bulk CSV / Excel Import Modal */}
      <ImportEmployeesModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        onSuccess={() => {
          void load();
          setNotice("Multi-service CSV import processed successfully! Employees, assets, and subscriptions have been synchronized.");
        }}
      />

      {/* Edit Employee & Resource Allocation Modal */}
      <EditEmployeeModal
        isOpen={Boolean(editingEmployee)}
        onClose={() => setEditingEmployee(null)}
        onSuccess={() => {
          void load();
          setNotice("Employee info, subscriptions, and IT assets updated successfully!");
        }}
        employee={editingEmployee}
      />
    </DashboardFrame>
  );
}
